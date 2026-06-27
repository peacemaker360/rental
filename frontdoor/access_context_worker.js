const ACCESS_JWT_HEADER = "cf-access-jwt-assertion";
const ACCESS_COOKIE_NAME = "CF_Authorization";
const CONTEXT_HEADER = "x-rental-context";
const CONTEXT_SIGNATURE_HEADER = "x-rental-context-signature";
const RENTAL_HEADER_PREFIX = "x-rental-";
const ALLOWED_ROLES = new Set(["viewer", "operator", "admin"]);

let cachedJwks = null;
let cachedJwksUntil = 0;

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);
      if (url.pathname === "/api/health") {
        return forwardToBackend(request, env, null);
      }

      const accessJwt = accessJwtFromRequest(request);
      if (!accessJwt) {
        return jsonResponse({error: "missing Cloudflare Access token"}, 401);
      }

      const claims = await verifyAccessJwt(accessJwt, env);
      const assignment = await loadTenantAssignment(claims, env);
      const context = {
        actor_id: assignment.actor_id || `access:${await shortDigest(claims.sub || claims.email || "unknown")}`,
        issued_at: Date.now() / 1000,
        role: assignment.role,
        tenant_id: assignment.tenant_id
      };
      const signedHeaders = await signedContextHeaders(context, env.RENTAL_CONTEXT_SECRET);
      return forwardToBackend(request, env, signedHeaders);
    } catch (error) {
      return jsonResponse({error: error.message || "frontdoor request failed"}, error.status || 403);
    }
  }
};

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

async function loadTenantAssignment(claims, env) {
  if (!env.TENANT_ACCESS_KV) throw new Error("TENANT_ACCESS_KV binding is required");
  const principal = claims.sub || "";
  if (!principal) throw new Error("Cloudflare Access token is missing subject");

  const assignment = await env.TENANT_ACCESS_KV.get(`principal:${principal}`, {type: "json"});
  if (!assignment) throw new Error("no tenant assignment for authenticated principal");
  if (!/^[a-z0-9][a-z0-9_-]{1,62}$/.test(assignment.tenant_id || "")) {
    throw new Error("tenant assignment has invalid tenant id");
  }
  if (!ALLOWED_ROLES.has(assignment.role)) {
    throw new Error("tenant assignment has invalid role");
  }
  return assignment;
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
