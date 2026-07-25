import assert from "node:assert/strict";
import test from "node:test";

import {
  isLoginPath,
  loginRedirectResponse,
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
