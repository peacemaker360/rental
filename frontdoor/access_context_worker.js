const ACCESS_JWT_HEADER = "cf-access-jwt-assertion";
const ACCESS_COOKIE_NAME = "CF_Authorization";
const CONTEXT_HEADER = "x-rental-context";
const CONTEXT_SIGNATURE_HEADER = "x-rental-context-signature";
const RENTAL_HEADER_PREFIX = "x-rental-";
const ALLOWED_ROLES = new Set(["viewer", "operator", "admin"]);
const GLOBAL_ROLES = new Set(["none", "reader", "operator", "admin", "platform_admin"]);
const TENANT_ROLES = new Set(["reader", "operator", "admin"]);
const ACCESS_PROFILES = new Set(["full", "basic"]);
const LOGIN_PATH = "/auth/login";

let cachedJwks = null;
let cachedJwksUntil = 0;

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);
      if (url.pathname === "/api/health") {
        return forwardToBackend(request, env, null);
      }
      if (url.pathname === "/api/access-requests" && request.method === "POST") {
        return createAccessRequest(request, env, null);
      }
      if (!url.pathname.startsWith("/api/") && url.pathname !== LOGIN_PATH) {
        return forwardToBackend(request, env, null);
      }

      const accessJwt = accessJwtFromRequest(request);
      if (!accessJwt) {
        return jsonResponse({error: "missing Cloudflare Access token"}, 401);
      }

      const claims = await verifyAccessJwt(accessJwt, env);
      if (url.pathname === LOGIN_PATH) {
        return forwardToBackend(rewriteRequestPath(request, "/"), env, null);
      }
      if (!url.pathname.startsWith("/api/")) {
        return forwardToBackend(request, env, null);
      }
      let assignment;
      try {
        assignment = await loadTenantAssignment(claims, env, url);
      } catch (error) {
        return jsonResponse(authenticatedErrorBody(error, claims), error.status || 403);
      }
      const context = {
        access_profile: assignment.access_profile || "full",
        actor_id: assignment.actor_id || `access:${await shortDigest(assignment.email || claims.sub || "unknown")}`,
        global_role: assignment.global_role || "none",
        has_global_role: Boolean(assignment.has_global_role),
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
      return jsonResponse({error: error.message || "frontdoor request failed"}, error.status || 403);
    }
  }
};

function authenticatedErrorBody(error, claims) {
  const body = {error: error.message || "frontdoor request failed"};
  const email = cleanEmail(claims?.email);
  if (validEmail(email)) body.user_email = email;
  return body;
}

async function createAccessRequest(request, env, claims) {
  if (!env.TENANT_ACCESS_KV) throw new Error("TENANT_ACCESS_KV binding is required");
  const payload = await request.json().catch(() => ({}));
  const email = cleanEmail(claims?.email || payload.email);
  if (!validEmail(email)) throw new Error("valid email is required");
  const tenantId = String(payload.tenant_id || "").trim().toLowerCase();
  if (!validTenantId(tenantId)) throw new Error("tenant id must use 2-63 lowercase letters, numbers, hyphens, or underscores");
  const now = new Date().toISOString();
  const id = `access_request:${await shortDigest(`${email}:${tenantId}`)}`;
  const item = {
    id,
    email,
    status: "pending",
    tenant_id: tenantId,
    requested_at: now,
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
  return jsonResponse({data: item}, 201);
}

function jsonResponse(body, status) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {"content-type": "application/json; charset=utf-8"}
  });
}

function accessJwtFromRequest(request) {
  const header = request.headers.get(ACCESS_JWT_HEADER);
  if (header) return header;
  const cookie = request.headers.get("cookie") || "";
  return cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${ACCESS_COOKIE_NAME}=`))
    ?.slice(ACCESS_COOKIE_NAME.length + 1);
}

async function verifyAccessJwt(jwt, env) {
  const parts = jwt.split(".");
  if (parts.length !== 3) throw new Error("invalid Cloudflare Access token");

  const [encodedHeader, encodedPayload, encodedSignature] = parts;
  const header = JSON.parse(base64UrlDecodeText(encodedHeader));
  const claims = JSON.parse(base64UrlDecodeText(encodedPayload));
  if (header.alg !== "RS256") throw new Error("unsupported Cloudflare Access token algorithm");

  const jwks = await accessJwks(env);
  const jwk = jwks.keys.find((key) => key.kid === header.kid);
  if (!jwk) throw new Error("Cloudflare Access signing key not found");

  const key = await crypto.subtle.importKey(
    "jwk",
    jwk,
    {name: "RSASSA-PKCS1-v1_5", hash: "SHA-256"},
    false,
    ["verify"]
  );
  const valid = await crypto.subtle.verify(
    {name: "RSASSA-PKCS1-v1_5"},
    key,
    base64UrlDecodeBytes(encodedSignature),
    new TextEncoder().encode(`${encodedHeader}.${encodedPayload}`)
  );
  if (!valid) throw new Error("invalid Cloudflare Access token signature");

  const now = Math.floor(Date.now() / 1000);
  const issuer = `https://${env.CF_ACCESS_TEAM_DOMAIN}`;
  if (claims.iss !== issuer) throw new Error("invalid Cloudflare Access issuer");
  if (claims.exp && now >= claims.exp) throw new Error("expired Cloudflare Access token");
  if (claims.nbf && now < claims.nbf) throw new Error("Cloudflare Access token is not active");
  if (!audienceMatches(claims.aud, env.CF_ACCESS_AUD)) throw new Error("invalid Cloudflare Access audience");
  return claims;
}

async function accessJwks(env) {
  const now = Date.now();
  if (cachedJwks && now < cachedJwksUntil) return cachedJwks;

  const response = await fetch(`https://${env.CF_ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs`);
  if (!response.ok) throw new Error("could not load Cloudflare Access certificates");
  cachedJwks = await response.json();
  cachedJwksUntil = now + 10 * 60 * 1000;
  return cachedJwks;
}

function audienceMatches(actual, expected) {
  return Array.isArray(actual) ? actual.includes(expected) : actual === expected;
}

async function loadTenantAssignment(claims, env, url) {
  if (!env.TENANT_ACCESS_KV) throw new Error("TENANT_ACCESS_KV binding is required");
  const email = String(claims.email || "").trim().toLowerCase();
  if (!email) throw new Error("Cloudflare Access token is missing email");
  if (!validEmail(email)) throw new Error("Cloudflare Access token email is invalid");

  const user = await env.TENANT_ACCESS_KV.get(`user:${email}`, {type: "json"});
  if (user) return resolveUserAssignment(user, email, url);

  const principal = claims.sub || "";
  if (principal) {
    const assignment = await env.TENANT_ACCESS_KV.get(`principal:${principal}`, {type: "json"});
    if (assignment) return resolveLegacyAssignment(assignment, email);
  }

  throw new Error("no user access profile for authenticated email");
}

function resolveLegacyAssignment(assignment, email) {
  if (!validTenantId(assignment.tenant_id || "")) throw new Error("tenant assignment has invalid tenant id");
  if (!ALLOWED_ROLES.has(assignment.role)) {
    throw new Error("tenant assignment has invalid role");
  }
  return {...assignment, email};
}

function resolveUserAssignment(user, email, url) {
  validateUserProfile(user);
  if (user.status && user.status !== "active") throw new Error("user access profile is disabled");
  const requestedTenant = routeTenant(url);
  const defaultTenant = user.default_tenant || firstTenantRole(user)?.tenant_id || firstMemberLink(user)?.tenant_id;
  const adminRoute = url.pathname.startsWith("/api/admin");
  const platformAdminRoute = adminRoute && user.global_role === "platform_admin";
  const tenantId = platformAdminRoute
    ? "platform-admin"
    : requestedTenant || defaultTenant || (user.global_role === "platform_admin" ? "platform-admin" : "");
  if (!validTenantId(tenantId)) throw new Error("user access profile has no tenant for this route");

  const role = roleForTenant(user, tenantId, adminRoute);
  const memberLink = (user.member_links || []).find((item) => item.tenant_id === tenantId);
  const globalRole = user.global_role || "none";
  const tenantCount = tenantAccessCount(user);
  return {
    access_profile: user.access_profile || "full",
    email,
    global_role: globalRole,
    has_global_role: globalRole !== "none",
    member_id: memberLink?.member_id,
    role,
    tenant_count: tenantCount,
    tenant_id: tenantId,
    tenant_switchable: globalRole !== "none" || tenantCount > 1
  };
}

function validateUserProfile(user) {
  if (user.status && !["active", "disabled"].includes(user.status)) {
    throw new Error("user access profile has invalid status");
  }
  const globalRole = user.global_role || "none";
  if (!GLOBAL_ROLES.has(globalRole)) throw new Error("user access profile has invalid global role");
  const accessProfile = user.access_profile || "full";
  if (!ACCESS_PROFILES.has(accessProfile)) throw new Error("user access profile has invalid access profile");
  if (user.default_tenant && !validTenantId(user.default_tenant)) {
    throw new Error("user access profile has invalid default tenant");
  }
  if (user.tenant_roles && !Array.isArray(user.tenant_roles)) {
    throw new Error("user access profile tenant roles must be a list");
  }
  if (user.member_links && !Array.isArray(user.member_links)) {
    throw new Error("user access profile member links must be a list");
  }
  for (const item of user.member_links || []) {
    if (!validTenantId(item.tenant_id)) throw new Error("user access profile has invalid member-link tenant");
    if (!opaqueMemberId(item.member_id)) throw new Error("user access profile has invalid member id");
  }
}

function roleForTenant(user, tenantId, adminRoute) {
  const globalRole = user.global_role || "none";
  if (globalRole === "platform_admin" && adminRoute) return "admin";
  if (globalRole === "platform_admin" && tenantId === "platform-admin") return "admin";
  if (globalRole === "admin") return "admin";
  if (globalRole === "operator") return "operator";
  if (globalRole === "reader") return "viewer";

  const tenantRole = (user.tenant_roles || []).find((item) => item.tenant_id === tenantId)?.role;
  if (!tenantRole && user.access_profile === "basic" && (user.member_links || []).some((item) => item.tenant_id === tenantId)) return "viewer";
  if (!tenantRole) throw new Error("user is not allowed for this tenant");
  if (!TENANT_ROLES.has(tenantRole)) throw new Error("user access profile has invalid tenant role");
  return tenantRole === "reader" ? "viewer" : tenantRole;
}

function firstTenantRole(user) {
  return (user.tenant_roles || []).find((item) => validTenantId(item.tenant_id));
}

function firstMemberLink(user) {
  return (user.member_links || []).find((item) => validTenantId(item.tenant_id));
}

function tenantAccessCount(user) {
  const tenantIds = new Set();
  for (const item of user.tenant_roles || []) {
    if (validTenantId(item.tenant_id)) tenantIds.add(item.tenant_id);
  }
  for (const item of user.member_links || []) {
    if (validTenantId(item.tenant_id)) tenantIds.add(item.tenant_id);
  }
  return tenantIds.size;
}

function routeTenant(url) {
  const parts = url.pathname.split("/").filter(Boolean);
  if (parts[0] !== "api") return null;
  if (!parts[1] || parts[1] === "context" || parts[1] === "health" || parts[1] === "admin") return null;
  return parts[1];
}

function validTenantId(value) {
  return /^[a-z0-9][a-z0-9_-]{1,62}$/.test(value || "");
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

function rewriteRequestPath(request, pathname) {
  const url = new URL(request.url);
  url.pathname = pathname;
  url.search = "";
  return new Request(url.toString(), request);
}

function stripUntrustedIdentityHeaders(headers) {
  headers.delete(ACCESS_JWT_HEADER);
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

function base64UrlDecodeText(value) {
  return new TextDecoder().decode(base64UrlDecodeBytes(value));
}

function base64UrlDecodeBytes(value) {
  const padded = value.replaceAll("-", "+").replaceAll("_", "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
  const binary = atob(padded);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}
