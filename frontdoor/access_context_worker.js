import {notifyOrganizationAdmins, notificationSummary} from "./access_notifications.js";
import {authenticateClerk, clerkConfiguration} from "./clerk_auth.js";
import {listUserMemberships, membershipAccessProfile} from "./clerk_roles.js";
const CONTEXT_HEADER = "x-rental-context";
const CONTEXT_SIGNATURE_HEADER = "x-rental-context-signature";
const RENTAL_HEADER_PREFIX = "x-rental-";
const TENANT_ROLES = new Set(["reader", "operator", "admin"]);
const ACCESS_PROFILES = new Set(["full", "basic"]);
const TENANT_ROUTE_PREFIX = "tid-";
const RESERVED_TENANT_IDS = new Set(["access-requests", "admin", "auth", "context", "health", "platform-admin"]);
const ERROR_CODES = Object.freeze({
  ACCESS_CONTEXT_ERROR: "ACCESS_CONTEXT_ERROR",
  ACCESS_PROFILE_DISABLED: "ACCESS_PROFILE_DISABLED",
  ACCESS_PROFILE_INVALID: "ACCESS_PROFILE_INVALID",
  ACCESS_PROFILE_NOT_FOUND: "ACCESS_PROFILE_NOT_FOUND",
  ACCESS_PROFILE_NO_TENANT: "ACCESS_PROFILE_NO_TENANT",
  ACCESS_REQUEST_INVALID: "ACCESS_REQUEST_INVALID",
  ACCESS_REQUEST_PENDING: "ACCESS_REQUEST_PENDING",
  ACCESS_TOKEN_INVALID: "ACCESS_TOKEN_INVALID",
  ACCESS_TOKEN_MISSING: "ACCESS_TOKEN_MISSING",
  TENANT_ACCESS_DENIED: "TENANT_ACCESS_DENIED",
  TENANT_ROUTE_INVALID: "TENANT_ROUTE_INVALID"
});
const PENDING_REQUEST_FALLBACK_LIMIT = 100;

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);
      if (url.pathname === "/api/auth/config" && request.method === "GET") {
        return jsonResponse(clerkConfiguration(env), 200);
      }
      if (url.pathname === "/api/health") {
        return forwardToBackend(request, env, null);
      }
      if (!url.pathname.startsWith("/api/")) {
        return forwardToBackend(request, env, null);
      }

      const claims = await authenticateClerk(request, env);
      if (url.pathname === "/api/access-requests" && request.method === "POST") {
        return await createAccessRequest(request, env, claims);
      }
      let assignment;
      try {
        assignment = await loadTenantAssignment(claims, env, url);
      } catch (error) {
        return jsonResponse(authenticatedErrorBody(error, claims), error.status || 403);
      }
      const notificationRoute = url.pathname.match(/^\/api\/admin\/access-requests\/(access_request:[a-f0-9]{24})\/notify$/);
      if (notificationRoute && request.method === "POST") {
        const item = await env.TENANT_ACCESS_KV.get(notificationRoute[1], {type: "json"});
        if (!item || item.status !== "pending" || assignment.role !== "admin" || item.tenant_id !== assignment.tenant_id) {
          return jsonResponse({error: "Access request not found"}, 404);
        }
        const association = await env.RENTAL_KV.get(`associations:${item.tenant_id}`, {type: "json"});
        if (!association?.clerk_organization_id) return jsonResponse({error: "Association is not mapped to Clerk"}, 409);
        item.notification = await notifyOrganizationAdmins(item, association, env, claims.clerkClient, url.origin);
        await env.TENANT_ACCESS_KV.put(item.id, JSON.stringify(item));
        return jsonResponse({notification_status: notificationSummary(item)}, 200);
      }
      const context = {
        access_profile: assignment.access_profile || "full",
        actor_id: assignment.actor_id || `clerk:${await shortDigest(claims.sub)}`,
        issued_at: Date.now() / 1000,
        member_id: assignment.member_id,
        role: assignment.role,
        tenant_count: assignment.tenant_count || 0,
        tenant_id: assignment.tenant_id,
        tenant_switchable: Boolean(assignment.tenant_switchable),
        user_email: assignment.email
      };
      const signedHeaders = await signedContextHeaders(context, env.RENTAL_CONTEXT_SECRET);
      return forwardToBackend(request, env, signedHeaders);
    } catch (error) {
      return jsonResponse(errorBody(error), error.status || 403);
    }
  }
};


function authenticatedErrorBody(error, claims) {
  const body = errorBody(error);
  const email = cleanEmail(claims?.email);
  if (validEmail(email)) body.user_email = email;
  return body;
}

function errorBody(error) {
  const body = {
    error: error?.message || "frontdoor request failed",
    errorCode: errorCodeFor(error)
  };
  if (error?.accessRequest) body.accessRequest = error.accessRequest;
  if (error?.authReason) body.authReason = error.authReason;
  return body;
}

function errorCodeFor(error) {
  if (error?.errorCode) return error.errorCode;
  const message = String(error?.message || "").toLowerCase();
  if (message.includes("missing sign-in token")) return ERROR_CODES.ACCESS_TOKEN_MISSING;
  if (message.includes("access token")) return ERROR_CODES.ACCESS_TOKEN_INVALID;
  if (message.includes("no user access profile")) return ERROR_CODES.ACCESS_PROFILE_NOT_FOUND;
  if (message.includes("access profile is disabled")) return ERROR_CODES.ACCESS_PROFILE_DISABLED;
  if (message.includes("has no tenant")) return ERROR_CODES.ACCESS_PROFILE_NO_TENANT;
  if (message.includes("not allowed for this tenant")) return ERROR_CODES.TENANT_ACCESS_DENIED;
  if (message.includes("tenant route")) return ERROR_CODES.TENANT_ROUTE_INVALID;
  if (message.includes("access profile") || message.includes("tenant assignment")) return ERROR_CODES.ACCESS_PROFILE_INVALID;
  if (message.includes("valid email") || message.includes("tenant id is invalid")) return ERROR_CODES.ACCESS_REQUEST_INVALID;
  return ERROR_CODES.ACCESS_CONTEXT_ERROR;
}

function accessError(message, errorCode, status = 403, accessRequest = null) {
  const error = new Error(message);
  error.errorCode = errorCode;
  error.status = status;
  if (accessRequest) error.accessRequest = accessRequest;
  return error;
}

export async function createAccessRequest(request, env, claims) {
  if (!env.TENANT_ACCESS_KV) throw new Error("TENANT_ACCESS_KV binding is required");
  const payload = await request.json().catch(() => ({}));
  const email = cleanEmail(claims?.email || payload.email);
  if (!validEmail(email)) throw new Error("valid email is required");
  const tenantId = String(payload.tenant_id || "").trim().toLowerCase();
  if (!validAssociationTenantId(tenantId)) throw new Error("tenant id is invalid or reserved");
  const association = await env.RENTAL_KV?.get(`associations:${tenantId}`, {type: "json"});
  if (!association?.clerk_organization_id || (association.status && association.status !== "active")) {
    throw accessError("Association is unavailable or has not been connected to Clerk", "ACCESS_REQUEST_INVALID", 404);
  }
  const now = new Date().toISOString();
  const id = `access_request:${await shortDigest(`${email}:${tenantId}`)}`;
  const existing = await env.TENANT_ACCESS_KV.get(id, {type: "json"});
  if (existing?.status === "pending") return jsonResponse({data: {...publicAccessRequest(existing), email}}, 200);
  const item = {
    id,
    email,
    status: "pending",
    tenant_id: tenantId,
    requested_at: existing?.requested_at || now,
    updated_at: now
  };
  const associationContact = await env.TENANT_ACCESS_KV.get(`association_contact:${tenantId}`, {type: "json"});
  if (associationContact) {
    item.association = {
      contact: associationContact.contact,
      display_name: associationContact.display_name,
      tenant_id: tenantId
    };
  }
  const indexKey = "access_requests:index";
  const ids = await env.TENANT_ACCESS_KV.get(indexKey, {type: "json"}) || [];
  if (!ids.includes(id)) {
    ids.push(id);
    ids.sort();
    await env.TENANT_ACCESS_KV.put(indexKey, JSON.stringify(ids));
  }
  await env.TENANT_ACCESS_KV.put(id, JSON.stringify(item));
  await addEmailRequestIndex(email, id, env);
  item.notification = await notifyOrganizationAdmins(item, association, env, claims.clerkClient, new URL(request.url).origin);
  await env.TENANT_ACCESS_KV.put(id, JSON.stringify(item));
  return jsonResponse({data: {...publicAccessRequest(item), email}}, 201);
}

function jsonResponse(body, status) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "cache-control": "no-store",
      "content-type": "application/json; charset=utf-8"
    }
  });
}


async function loadTenantAssignment(claims, env, url) {
  if (!env.TENANT_ACCESS_KV) throw new Error("TENANT_ACCESS_KV binding is required");
  const email = String(claims.email || "").trim().toLowerCase();
  if (!validEmail(email)) throw new Error("Sign-in email is invalid");
  if (!env.RENTAL_KV) throw accessError("Association registry is unavailable", "AUTH_CONFIGURATION_ERROR", 503);
  const tenantIds = await env.RENTAL_KV.get("associations:index", {type: "json"}) || [];
  const associations = [];
  for (const tenantId of tenantIds) {
    const association = await env.RENTAL_KV.get(`associations:${tenantId}`, {type: "json"});
    if (association) associations.push(association);
  }
  let memberships;
  try {
    memberships = await listUserMemberships(claims.clerkClient, claims.sub);
  } catch {
    throw accessError("Unable to check association access right now", "AUTH_PROVIDER_UNAVAILABLE", 503);
  }
  const profile = membershipAccessProfile(claims.clerkUser, memberships, associations);
  const activeAssociation = associations.find(item => item.clerk_organization_id === claims.activeOrganizationId);
  if (activeAssociation && profile.tenant_roles.some(item => item.tenant_id === activeAssociation.tenant_id)) {
    profile.default_tenant = activeAssociation.tenant_id;
  }
  if (!routeTenant(url)) {
    if (claims.activeOrganizationId && !activeAssociation) {
      throw accessError("The selected Clerk organization has no association mapping in Rental Desk. Ask the app operator to connect its organization ID to the existing association.", "ACCESS_ORGANIZATION_UNMAPPED");
    }
    if (claims.activeOrganizationId && !profile.tenant_roles.some(item => item.tenant_id === activeAssociation?.tenant_id)) {
      const membership = memberships.find(item => item.organization.id === claims.activeOrganizationId);
      throw membership
        ? accessError("Your Clerk organization role is not supported by Rental Desk. Ask an organization admin to assign a rental role in Clerk.", "ACCESS_ORGANIZATION_ROLE_UNSUPPORTED")
        : accessError("You no longer have membership in the selected Clerk organization. Switch organizations or ask its admin for an invitation.", "ACCESS_ORGANIZATION_ACCESS_DENIED");
    }
    if (!claims.activeOrganizationId && profile.tenant_roles.length) {
      throw accessError("Select your organization in Clerk to continue", "ACCESS_ORGANIZATION_REQUIRED");
    }
  }
  if (profile.tenant_roles.length) return resolveUserAssignment(profile, email, url);

  const pendingRequest = await pendingAccessRequestForEmail(email, env);
  if (pendingRequest) {
    throw accessError(
      "access request is pending",
      ERROR_CODES.ACCESS_REQUEST_PENDING,
      403,
      pendingRequest
    );
  }
  throw accessError(
    "no user access profile for authenticated email",
    ERROR_CODES.ACCESS_PROFILE_NOT_FOUND
  );
}

async function addEmailRequestIndex(email, requestId, env) {
  const key = `access_requests:email:${await shortDigest(email)}`;
  const ids = await env.TENANT_ACCESS_KV.get(key, {type: "json"}) || [];
  if (!ids.includes(requestId)) {
    ids.push(requestId);
    await env.TENANT_ACCESS_KV.put(key, JSON.stringify(ids));
  }
}

async function pendingAccessRequestForEmail(email, env) {
  const emailIndexKey = `access_requests:email:${await shortDigest(email)}`;
  let ids = await env.TENANT_ACCESS_KV.get(emailIndexKey, {type: "json"}) || [];
  let usedFallback = false;
  if (!Array.isArray(ids) || !ids.length) {
    const allIds = await env.TENANT_ACCESS_KV.get("access_requests:index", {type: "json"}) || [];
    ids = Array.isArray(allIds) ? allIds.slice(-PENDING_REQUEST_FALLBACK_LIMIT) : [];
    usedFallback = true;
  }
  for (const requestId of [...ids].reverse()) {
    const item = await env.TENANT_ACCESS_KV.get(requestId, {type: "json"});
    if (cleanEmail(item?.email) !== email || item?.status !== "pending") continue;
    if (usedFallback) await addEmailRequestIndex(email, requestId, env);
    return publicAccessRequest(item);
  }
  return null;
}

function publicAccessRequest(item) {
  return {
    notification_status: notificationSummary(item),
    association: item.association,
    id: item.id,
    requested_at: item.requested_at,
    status: item.status,
    tenant_id: item.tenant_id,
    updated_at: item.updated_at
  };
}

function resolveUserAssignment(user, email, url) {
  validateUserProfile(user);
  if (user.status && user.status !== "active") throw new Error("user access profile is disabled");
  const requestedTenant = routeTenant(url);
  const defaultTenant = user.default_tenant || firstTenantRole(user)?.tenant_id;
  const tenantId = requestedTenant || defaultTenant;
  if (!validTenantId(tenantId)) throw new Error("user access profile has no tenant for this route");

  const role = roleForTenant(user, tenantId);
  const memberLink = (user.member_links || []).find((item) => item.tenant_id === tenantId);
  const tenantCount = tenantAccessCount(user);
  return {
    access_profile: user.tenant_profiles?.[tenantId] || user.access_profile || "full",
    email,
    member_id: memberLink?.member_id,
    role,
    tenant_count: tenantCount,
    tenant_id: tenantId,
    tenant_switchable: tenantCount > 1
  };
}

function validateUserProfile(user) {
  if (user.status && !["active", "disabled"].includes(user.status)) {
    throw new Error("user access profile has invalid status");
  }
  const accessProfile = user.access_profile || "full";
  if (!ACCESS_PROFILES.has(accessProfile)) throw new Error("user access profile has invalid access profile");
  if (user.default_tenant && !validAssociationTenantId(user.default_tenant)) {
    throw new Error("user access profile has invalid default tenant");
  }
  if (user.tenant_roles && !Array.isArray(user.tenant_roles)) {
    throw new Error("user access profile tenant roles must be a list");
  }
  if (user.member_links && !Array.isArray(user.member_links)) {
    throw new Error("user access profile member links must be a list");
  }
  for (const item of user.tenant_roles || []) {
    if (!validAssociationTenantId(item.tenant_id)) throw new Error("user access profile has invalid tenant-role tenant");
    if (!TENANT_ROLES.has(item.role)) throw new Error("user access profile has invalid tenant role");
  }
  for (const item of user.member_links || []) {
    if (!validAssociationTenantId(item.tenant_id)) throw new Error("user access profile has invalid member-link tenant");
    if (!opaqueMemberId(item.member_id)) throw new Error("user access profile has invalid member id");
  }
}

function roleForTenant(user, tenantId) {
  const tenantRole = (user.tenant_roles || []).find((item) => item.tenant_id === tenantId)?.role;
  if (!tenantRole) throw new Error("user is not allowed for this tenant");
  if (!TENANT_ROLES.has(tenantRole)) throw new Error("user access profile has invalid tenant role");
  return tenantRole === "reader" ? "viewer" : tenantRole;
}

function firstTenantRole(user) {
  return (user.tenant_roles || []).find((item) => validAssociationTenantId(item.tenant_id));
}

function tenantAccessCount(user) {
  const tenantIds = new Set();
  for (const item of user.tenant_roles || []) {
    if (validAssociationTenantId(item.tenant_id)) tenantIds.add(item.tenant_id);
  }
  for (const item of user.member_links || []) {
    if (validAssociationTenantId(item.tenant_id)) tenantIds.add(item.tenant_id);
  }
  return tenantIds.size;
}

function routeTenant(url) {
  const parts = url.pathname.split("/").filter(Boolean);
  if (parts[0] !== "api") return null;
  const routeSegment = parts[1] || "";
  if (!routeSegment.startsWith(TENANT_ROUTE_PREFIX)) return null;
  const tenantId = routeSegment.slice(TENANT_ROUTE_PREFIX.length);
  if (!validAssociationTenantId(tenantId)) throw new Error("tenant route has invalid or reserved tenant id");
  return tenantId;
}

function validTenantId(value) {
  return /^[a-z0-9][a-z0-9_-]{1,62}$/.test(value || "");
}

function validAssociationTenantId(value) {
  return validTenantId(value) && !RESERVED_TENANT_IDS.has(value);
}

function validEmail(value) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value || "");
}

function cleanEmail(value) {
  return String(value || "").trim().toLowerCase();
}

function opaqueMemberId(value) {
  return Boolean(value) && !validEmail(value) && !/(?=(?:\D*\d){7,})\+?[\d][\d\s()./-]{6,}\d/.test(value);
}

async function signedContextHeaders(context, secret) {
  if (!secret) throw new Error("RENTAL_CONTEXT_SECRET is required");
  const encoded = base64UrlEncodeText(JSON.stringify(context));
  return {
    [CONTEXT_HEADER]: encoded,
    [CONTEXT_SIGNATURE_HEADER]: await hmacSha256Hex(secret, encoded)
  };
}

async function hmacSha256Hex(secret, value) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    {name: "HMAC", hash: "SHA-256"},
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(value));
  return Array.from(new Uint8Array(signature), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function shortDigest(value) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(value)));
  return Array.from(new Uint8Array(digest).slice(0, 12), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function forwardToBackend(request, env, signedHeaders) {
  const headers = new Headers(request.headers);
  stripUntrustedIdentityHeaders(headers);
  if (signedHeaders) {
    headers.set(CONTEXT_HEADER, signedHeaders[CONTEXT_HEADER]);
    headers.set(CONTEXT_SIGNATURE_HEADER, signedHeaders[CONTEXT_SIGNATURE_HEADER]);
  }

  const forwarded = new Request(request, {headers});
  if (env.RENTAL_BACKEND && typeof env.RENTAL_BACKEND.fetch === "function") {
    return env.RENTAL_BACKEND.fetch(forwarded);
  }
  if (env.RENTAL_BACKEND_URL) {
    const original = new URL(request.url);
    const target = new URL(`${original.pathname}${original.search}`, env.RENTAL_BACKEND_URL);
    return fetch(new Request(target.toString(), {
      body: ["GET", "HEAD"].includes(forwarded.method) ? undefined : forwarded.body,
      headers: forwarded.headers,
      method: forwarded.method,
      redirect: "manual"
    }));
  }
  throw new Error("RENTAL_BACKEND service binding or RENTAL_BACKEND_URL is required");
}

function stripUntrustedIdentityHeaders(headers) {
  headers.delete("cf-access-jwt-assertion");
  headers.delete("cf-access-authenticated-user-email");
  headers.delete("cookie");
  headers.delete("authorization");
  for (const name of Array.from(headers.keys())) {
    if (name.toLowerCase().startsWith(RENTAL_HEADER_PREFIX)) {
      headers.delete(name);
    }
  }
}

function base64UrlEncodeText(value) {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}


export {
  loadTenantAssignment,
  resolveUserAssignment,
  ERROR_CODES,
  errorCodeFor,
  pendingAccessRequestForEmail,
  publicAccessRequest,
  routeTenant,
  validAssociationTenantId
};
