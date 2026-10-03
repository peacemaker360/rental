import {createClerkClient, verifyToken} from "@clerk/backend";

const verificationReasons = new Set([
  "token-expired", "token-invalid", "token-invalid-algorithm",
  "token-invalid-authorized-parties", "token-invalid-signature",
  "token-not-active-yet", "token-iat-in-the-future", "token-verification-failed",
  "secret-key-invalid", "jwk-local-missing", "jwk-remote-failed-to-load",
  "jwk-remote-invalid", "jwk-remote-missing", "jwk-failed-to-resolve", "jwk-kid-mismatch"
]);

function authError(message, errorCode, status = 401) {
  return Object.assign(new Error(message), {errorCode, status});
}

export function clerkConfiguration(env) {
  const publishableKey = String(env.CLERK_PUBLISHABLE_KEY || env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "").trim();
  if (!/^pk_(test|live)_[A-Za-z0-9+/=]+$/.test(publishableKey)) {
    throw authError("Sign-in is not configured", "AUTH_CONFIGURATION_ERROR", 503);
  }
  let domain;
  try {
    domain = atob(publishableKey.split("_")[2]);
  } catch {
    throw authError("Invalid sign-in configuration", "AUTH_CONFIGURATION_ERROR", 503);
  }
  if (!/^[a-z0-9]+(?:[.-][a-z0-9]+)*\$$/.test(domain)) {
    throw authError("Invalid sign-in configuration", "AUTH_CONFIGURATION_ERROR", 503);
  }
  return {provider: "clerk", publishableKey, frontendApi: `https://${domain.slice(0, -1)}`};
}

export function verifiedPrimaryEmail(user) {
  const primary = user.emailAddresses?.find((item) => item.id === user.primaryEmailAddressId);
  if (!primary || primary.verification?.status !== "verified") {
    throw authError("Verify your email address before requesting access", "ACCESS_EMAIL_UNVERIFIED", 403);
  }
  return primary.emailAddress.trim().toLowerCase();
}

export async function authenticateClerk(request, env, dependencies = {verifyToken, createClerkClient}) {
  const token = request.headers.get("authorization")?.match(/^Bearer\s+(\S+)$/i)?.[1];
  if (!token) throw authError("Sign in to continue", "ACCESS_TOKEN_MISSING");
  const config = clerkConfiguration(env);
  if (!env.CLERK_SECRET_KEY) {
    throw authError("Sign-in is not configured", "AUTH_CONFIGURATION_ERROR", 503);
  }
  const origin = new URL(request.url).origin;
  let claims;
  try {
    claims = await dependencies.verifyToken(token, {
      secretKey: env.CLERK_SECRET_KEY,
      authorizedParties: [origin]
    });
  } catch (error) {
    // SDK messages can contain token/claim data; expose only known reason codes.
    const reason = verificationReasons.has(error?.reason) ? error.reason : "token-verification-failed";
    throw Object.assign(authError("Your sign-in has expired or could not be verified", "ACCESS_TOKEN_INVALID"), {authReason: reason});
  }
  const reason = claims.iss !== config.frontendApi ? "issuer-mismatch"
    : claims.azp !== origin ? "origin-mismatch"
    : !claims.sub || !claims.sid ? "session-claims-missing" : null;
  if (reason) {
    throw Object.assign(authError("Your sign-in has expired or could not be verified", "ACCESS_TOKEN_INVALID"), {authReason: reason});
  }
  if (claims.sts === "pending") {
    throw Object.assign(authError("Complete your account setup to continue", "ACCESS_SESSION_PENDING", 403), {authReason: "session-pending"});
  }
  const client = dependencies.createClerkClient({secretKey: env.CLERK_SECRET_KEY, publishableKey: config.publishableKey});
  let user;
  try {
    user = await client.users.getUser(claims.sub);
  } catch {
    throw authError("Unable to verify your account right now", "AUTH_PROVIDER_UNAVAILABLE", 503);
  }
  if (user.banned || user.locked) throw authError("Account is unavailable", "ACCESS_PROFILE_DISABLED", 403);
  return {sub: claims.sub, activeOrganizationId: claims.o?.id || claims.org_id || null, email: verifiedPrimaryEmail(user), clerkUser: user, clerkClient: client};
}
