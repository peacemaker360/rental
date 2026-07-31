import assert from "node:assert/strict";
import test from "node:test";

import {
  ERROR_CODES,
  errorCodeFor,
  isLoginPath,
  loginRedirectResponse,
  pendingAccessRequestForEmail,
  publicAccessRequest,
  routeTenant,
  validAssociationTenantId
} from "../frontdoor/access_context_worker.js";

test("login handoff accepts exact and trailing-slash paths", () => {
  assert.equal(isLoginPath("/api/auth/login"), true);
  assert.equal(isLoginPath("/api/auth/login/"), true);
  assert.equal(isLoginPath("/api/auth/login/extra"), false);
});

test("login handoff redirects to the current origin root", () => {
  const response = loginRedirectResponse(
    new Request("https://rental.kittythecat.ch/api/auth/login")
  );

  assert.equal(response.status, 303);
  assert.equal(response.headers.get("location"), "https://rental.kittythecat.ch/");
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(response.headers.get("x-rental-auth-handler"), "login-redirect");
});

test("auth routes are never interpreted as tenant ids", () => {
  assert.equal(routeTenant(new URL("https://rental.kittythecat.ch/api/auth/login")), null);
  assert.equal(routeTenant(new URL("https://rental.kittythecat.ch/api/context")), null);
  assert.equal(routeTenant(new URL("https://rental.kittythecat.ch/api/mgw/summary")), null);
  assert.equal(routeTenant(new URL("https://rental.kittythecat.ch/api/tid-mgw/summary")), "mgw");
  assert.throws(
    () => routeTenant(new URL("https://rental.kittythecat.ch/api/tid-auth/summary")),
    /invalid or reserved/
  );
  assert.equal(validAssociationTenantId("auth"), false);
  assert.equal(validAssociationTenantId("mgw"), true);
});

test("context errors expose stable machine-readable codes", () => {
  assert.equal(
    errorCodeFor(new Error("missing Cloudflare Access token")),
    ERROR_CODES.ACCESS_TOKEN_MISSING
  );
  assert.equal(
    errorCodeFor(new Error("no user access profile for authenticated email")),
    ERROR_CODES.ACCESS_PROFILE_NOT_FOUND
  );
  assert.equal(
    errorCodeFor(Object.assign(new Error("access request is pending"), {
      errorCode: ERROR_CODES.ACCESS_REQUEST_PENDING
    })),
    ERROR_CODES.ACCESS_REQUEST_PENDING
  );
});

test("pending request context omits the stored email", () => {
  const request = publicAccessRequest({
    id: "access_request:1234567890abcdef12345678",
    email: "member@example.test",
    status: "pending",
    tenant_id: "tenant-a",
    requested_at: "2026-07-25T10:00:00Z",
    updated_at: "2026-07-25T10:00:00Z"
  });

  assert.equal(request.email, undefined);
  assert.equal(request.status, "pending");
  assert.equal(request.tenant_id, "tenant-a");
});

test("pending request lookup backfills the opaque email index", async () => {
  const requestId = "access_request:1234567890abcdef12345678";
  const writes = [];
  const kv = {
    async get(key) {
      if (key === "access_requests:index") return [requestId];
      if (key === requestId) {
        return {
          id: requestId,
          email: "member@example.test",
          status: "pending",
          tenant_id: "tenant-a"
        };
      }
      return null;
    },
    async put(key, value) {
      writes.push([key, JSON.parse(value)]);
    }
  };

  const request = await pendingAccessRequestForEmail(
    "member@example.test",
    {TENANT_ACCESS_KV: kv}
  );

  assert.equal(request.id, requestId);
  assert.equal(request.email, undefined);
  assert.equal(writes.length, 1);
  assert.match(writes[0][0], /^access_requests:email:[a-f0-9]{24}$/);
  assert.deepEqual(writes[0][1], [requestId]);
});
