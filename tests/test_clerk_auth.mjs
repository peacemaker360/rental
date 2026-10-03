import assert from "node:assert/strict";
import {generateKeyPairSync, sign} from "node:crypto";
import test from "node:test";
import {verifyToken} from "@clerk/backend";
import {authenticateClerk, clerkConfiguration, verifiedPrimaryEmail} from "../frontdoor/clerk_auth.js";

const domain = "example.clerk.accounts.dev";
const env = {CLERK_PUBLISHABLE_KEY: `pk_test_${btoa(`${domain}$`)}`, CLERK_SECRET_KEY: "test-only"};
const origin = "https://rental.example.test";
const {privateKey, publicKey} = generateKeyPairSync("rsa", {modulusLength: 2048});
const jwtKey = publicKey.export({type: "spki", format: "pem"});
const user = {primaryEmailAddressId: "email_1", emailAddresses: [{id: "email_1", emailAddress: "Member@Example.Test", verification: {status: "verified"}}]};
const dependencies = {
  verifyToken: (token, options) => verifyToken(token, {...options, jwtKey}),
  createClerkClient: () => ({users: {getUser: async () => user}})
};

function request(overrides = {}, signatureKey = privateKey) {
  const now = Math.floor(Date.now() / 1000);
  const payload = {iss: `https://${domain}`, azp: origin, sub: "user_1", sid: "sess_1", iat: now, nbf: now - 5, exp: now + 60, ...overrides};
  const encode = (item) => Buffer.from(JSON.stringify(item)).toString("base64url");
  const body = `${encode({alg: "RS256", typ: "JWT", kid: "test"})}.${encode(payload)}`;
  const token = `${body}.${sign("RSA-SHA256", Buffer.from(body), signatureKey).toString("base64url")}`;
  return new Request(`${origin}/api/context`, {headers: {authorization: `Bearer ${token}`}});
}

test("authenticates a signed session and reads verified primary email", async () => {
  const identity = await authenticateClerk(request({email: "forged@example.test"}), env, dependencies);
  assert.equal(identity.sub, "user_1");
  assert.equal(identity.email, "member@example.test");
  assert.equal(identity.clerkUser, user);
});

test("local browser token requires the gateway's local origin, not its production route", async () => {
  const signed = request({azp: "http://localhost:8795"});
  const headers = signed.headers;
  await assert.rejects(authenticateClerk(
    new Request("http://rental.example.test/api/context", {headers}), env, dependencies
  ), {authReason: "token-invalid-authorized-parties"});
  const identity = await authenticateClerk(
    new Request("http://localhost:8795/api/context", {headers}), env, dependencies
  );
  assert.equal(identity.sub, "user_1");
});

test("rejects wrong issuer, origin, expired and non-session tokens", async () => {
  for (const claims of [{iss: "https://other.clerk.accounts.dev"}, {azp: "https://other.test"}, {exp: 1}, {sid: null}]) {
    await assert.rejects(authenticateClerk(request(claims), env, dependencies), {errorCode: "ACCESS_TOKEN_INVALID"});
  }
});

test("rejects forged signatures and Access headers", async () => {
  const other = generateKeyPairSync("rsa", {modulusLength: 2048});
  await assert.rejects(authenticateClerk(request({}, other.privateKey), env, dependencies), {errorCode: "ACCESS_TOKEN_INVALID"});
  await assert.rejects(authenticateClerk(new Request(`${origin}/api/context`, {headers: {"cf-access-jwt-assertion": "old-token"}}), env, dependencies), {errorCode: "ACCESS_TOKEN_MISSING"});
});

test("verification diagnostics identify failures without exposing SDK messages", async () => {
  for (const [claims, authReason] of [
    [{iss: "https://other.clerk.accounts.dev"}, "issuer-mismatch"],
    [{azp: "https://other.test"}, "token-invalid-authorized-parties"],
    [{exp: 1}, "token-expired"],
    [{sid: null}, "session-claims-missing"]
  ]) {
    await assert.rejects(authenticateClerk(request(claims), env, dependencies),
      {errorCode: "ACCESS_TOKEN_INVALID", authReason});
  }
  for (const reason of ["secret-key-invalid", "jwk-remote-failed-to-load", "private-token-value"]) {
    await assert.rejects(authenticateClerk(request(), env, {
      ...dependencies,
      verifyToken: async () => { throw Object.assign(new Error("private-token-value"), {reason}); }
    }), (error) => {
      assert.equal(error.authReason, reason === "private-token-value" ? "token-verification-failed" : reason);
      assert.equal(error.message.includes("private-token-value"), false);
      return true;
    });
  }
});

test("rejects unverified email and invalid configuration", () => {
  assert.throws(() => verifiedPrimaryEmail({...user, emailAddresses: []}), {errorCode: "ACCESS_EMAIL_UNVERIFIED"});
  assert.throws(() => clerkConfiguration({}), {errorCode: "AUTH_CONFIGURATION_ERROR"});
});

test("accepts the standard local publishable-key alias without exposing secrets", () => {
  const config = clerkConfiguration({NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: env.CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY: "private"});
  assert.equal(config.provider, "clerk");
  assert.equal(config.frontendApi, `https://${domain}`);
  assert.equal(config.CLERK_SECRET_KEY, undefined);
});


test("pending sessions get a recoverable setup response and never reach account lookup", async () => {
  await assert.rejects(authenticateClerk(request({sts: "pending"}), env, {
    ...dependencies,
    createClerkClient: () => { throw new Error("Pending session reached protected lookup"); }
  }), {errorCode: "ACCESS_SESSION_PENDING", status: 403, authReason: "session-pending"});
});

test("verified active organization is preserved for both token versions", async () => {
  for (const claims of [{v: 2, o: {id: "org_b"}}, {org_id: "org_b"}]) {
    const identity = await authenticateClerk(request(claims), env, dependencies);
    assert.equal(identity.activeOrganizationId, "org_b");
  }
});
