import assert from "node:assert/strict";
import test from "node:test";
import {membershipAccessProfile, listUserMemberships} from "../frontdoor/clerk_roles.js";
import {loadTenantAssignment} from "../frontdoor/access_context_worker.js";

const associations = [{tenant_id: "band-a", clerk_organization_id: "org_a"}, {tenant_id: "band-b", clerk_organization_id: "org_b"}];
test("ambiguous organization mappings fail closed", () => {
  for (const duplicate of [
    {tenant_id: "other", clerk_organization_id: "org_a"},
    {tenant_id: "band-a", clerk_organization_id: "org_other"}
  ]) {
    assert.throws(() => membershipAccessProfile({}, [], [...associations, duplicate]), /Ambiguous/);
  }
});
test("basic and operator profiles remain scoped to their own association", () => {
  const profile = membershipAccessProfile({}, [
    {role: "org:member", organization: {id: "org_a"}},
    {role: "org:operator", organization: {id: "org_b"}}
  ], associations, [{tenant_id: "band-a", member_id: "mem_a"}, {tenant_id: "other", member_id: "mem_b"}]);
  assert.equal(profile.tenant_profiles["band-a"], "basic");
  assert.equal(profile.tenant_profiles["band-b"], "full");
  assert.deepEqual(profile.member_links, [{tenant_id: "band-a", member_id: "mem_a"}]);
  assert.equal(profile.global_role, "none");
});
test("org admins and user-editable metadata cannot grant platform admin", () => {
  const profile = membershipAccessProfile({unsafeMetadata: {rental: {global_role: "platform_admin"}}}, [
    {role: "org:admin", organization: {id: "org_a"}},
    {role: "org:admin", organization: {id: "unmapped", slug: "band-b"}},
    {role: "org:unknown", organization: {id: "org_b"}}
  ], associations);
  assert.deepEqual(profile.tenant_roles, [{tenant_id: "band-a", role: "admin"}]);
  assert.equal(profile.global_role, "none");
});
test("private metadata global roles are ignored", () => {
  const profile = membershipAccessProfile({privateMetadata: {rental: {global_role: "platform_admin"}}}, [], associations);
  assert.equal(profile.global_role, "none");
  assert.equal(profile.tenant_roles.length, 0);
});
test("membership lookup includes every page", async () => {
  const offsets = [];
  const result = await listUserMemberships({users: {getOrganizationMembershipList: async ({offset}) => {
    offsets.push(offset);
    return {data: Array.from({length: offset ? 1 : 100}, (_, i) => ({id: offset + i})), totalCount: 101};
  }}}, "user_a");
  assert.equal(result.length, 101);
  assert.deepEqual(offsets, [0, 100]);
});

function assignmentFixture() {
  const legacy = {global_role: "platform_admin", access_profile: "full", member_links: [{tenant_id: "band-a", member_id: "member_a"}]};
  const registry = new Map([
    ["associations:index", ["band-a", "band-b"]],
    ...associations.map(item => [`associations:${item.tenant_id}`, item])
  ]);
  let memberships = [{role: "org:member", organization: {id: "org_a"}}, {role: "org:operator", organization: {id: "org_b"}}];
  const claims = {
    sub: "user_a", email: "member@example.test", clerkUser: {}, activeOrganizationId: "org_a",
    clerkClient: {users: {getOrganizationMembershipList: async () => ({data: memberships, totalCount: memberships.length})}}
  };
  const env = {
    RENTAL_KV: {get: async key => registry.get(key) ?? null},
    TENANT_ACCESS_KV: {get: async key => key.startsWith("user:") ? legacy : null}
  };
  return {claims, env, legacy, revoke: () => { memberships = []; }};
}

test("malformed association registry is a non-permission data failure", async () => {
  const {claims, env} = assignmentFixture();
  for (const value of [{private: "invalid index"}, [null], ["missing-association"]]) {
    env.RENTAL_KV.get = async key => key === "associations:index" ? value : null;
    await assert.rejects(loadTenantAssignment(claims, env, new URL("https://example.test/api/context")), error => {
      assert.equal(error.status, 503);
      assert.equal(error.errorCode, "DATA_INTEGRITY_ERROR");
      assert.doesNotMatch(error.message, /private|missing-association/);
      return true;
    });
  }
});

test("gateway uses Clerk roles per tenant, never the old KV global role", async () => {
  const {claims, env} = assignmentFixture();
  const basic = await loadTenantAssignment(claims, env, new URL("https://rental.test/api/context"));
  assert.equal(basic.tenant_id, "band-a");
  assert.equal(basic.global_role, undefined);
  assert.equal(basic.role, "viewer");
  assert.equal(basic.access_profile, "basic");
  assert.equal(basic.member_id, undefined);
  const operator = await loadTenantAssignment(claims, env, new URL("https://rental.test/api/tid-band-b/instruments"));
  assert.equal(operator.role, "operator");
  assert.equal(operator.access_profile, "full");
  assert.equal(operator.member_id, undefined);
  await assert.rejects(loadTenantAssignment(claims, env, new URL("https://rental.test/api/tid-other/instruments")), /not allowed/);
});

test("revoked membership and provider failure never fall back to old KV grants", async () => {
  const fixture = assignmentFixture();
  fixture.revoke();
  await assert.rejects(loadTenantAssignment(fixture.claims, fixture.env, new URL("https://rental.test/api/context")), {errorCode: "ACCESS_ORGANIZATION_ACCESS_DENIED"});
  fixture.claims.clerkClient.users.getOrganizationMembershipList = async () => {throw new Error("offline");};
  await assert.rejects(loadTenantAssignment(fixture.claims, fixture.env, new URL("https://rental.test/api/context")), {errorCode: "AUTH_PROVIDER_UNAVAILABLE", status: 503});
});

test("private metadata cannot bootstrap or bypass missing organization membership", async () => {
  const {claims, env, revoke} = assignmentFixture();
  revoke();
  claims.clerkUser.privateMetadata = {rental: {global_role: "platform_admin"}};
  await assert.rejects(loadTenantAssignment(claims, env, new URL("https://rental.test/api/admin/associations")), {errorCode: "ACCESS_ORGANIZATION_ACCESS_DENIED"});
});


test("selected Clerk organization chooses the initial tenant only with a current membership", async () => {
  const {claims, env} = assignmentFixture();
  claims.activeOrganizationId = "org_b";
  const url = new URL("https://rental.test/api/context");
  assert.equal((await loadTenantAssignment(claims, env, url)).tenant_id, "band-b");
  // An explicit authorized tenant route still wins over the initial selection.
  assert.equal((await loadTenantAssignment(claims, env, new URL("https://rental.test/api/tid-band-a/instruments"))).tenant_id, "band-a");
  claims.activeOrganizationId = "org_unmapped";
  await assert.rejects(loadTenantAssignment(claims, env, url), {errorCode: "ACCESS_ORGANIZATION_UNMAPPED"});
  claims.clerkClient.users.getOrganizationMembershipList = async () => ({data: [{role: "org:member", organization: {id: "org_a"}}], totalCount: 1});
  claims.activeOrganizationId = "org_b";
  await assert.rejects(loadTenantAssignment(claims, env, url), {errorCode: "ACCESS_ORGANIZATION_ACCESS_DENIED"});
});


test("missing active organization prompts Clerk selection instead of choosing an arbitrary tenant", async () => {
  const {claims, env} = assignmentFixture();
  claims.activeOrganizationId = null;
  await assert.rejects(loadTenantAssignment(claims, env, new URL("https://rental.test/api/context")), {errorCode: "ACCESS_ORGANIZATION_REQUIRED"});
});

 test("legacy KV permissions, status and member links are never read for authorization", async () => {
  const {claims, env, legacy} = assignmentFixture();
  legacy.status = "disabled";
  env.TENANT_ACCESS_KV.get = async key => { if (key.startsWith("user:")) throw new Error("legacy permission lookup"); return null; };
  const assignment = await loadTenantAssignment(claims, env, new URL("https://rental.test/api/context"));
  assert.equal(assignment.role, "viewer");
  assert.equal(assignment.member_id, undefined);
});

test("an unsupported Clerk role is distinguished from a missing mapping", async () => {
  const {claims, env} = assignmentFixture();
  claims.clerkClient.users.getOrganizationMembershipList = async () => ({data: [{role: "org:custom", organization: {id: "org_a"}}], totalCount: 1});
  await assert.rejects(loadTenantAssignment(claims, env, new URL("https://rental.test/api/context")), {errorCode: "ACCESS_ORGANIZATION_ROLE_UNSUPPORTED"});
});

async function memberFixture() {
  const fixture = assignmentFixture();
  fixture.claims.activeOrganizationId = null;
  fixture.revoke();
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(fixture.claims.email))), byte => byte.toString(16).padStart(2, "0")).join("");
  const members = new Map([
    ["tenant:band-a:index:members", ["member_a"]],
    ["tenant:band-a:members:member_a", {id: "member_a", access_email_hash: hash, is_active: true}]
  ]);
  const registryGet = fixture.env.RENTAL_KV.get;
  fixture.env.RENTAL_KV.get = async key => members.get(key) ?? await registryGet(key);
  return {...fixture, members, hash};
}

test("a verified email match grants own-rentals access without Clerk org membership", async () => {
  const {claims, env} = await memberFixture();
  const assignment = await loadTenantAssignment(claims, env, new URL("https://rental.test/api/context"));
  assert.equal(assignment.role, "viewer");
  assert.equal(assignment.access_profile, "basic");
  assert.equal(assignment.tenant_id, "band-a");
  assert.deepEqual(assignment.member_associations, [{tenant_id: "band-a", display_name: "band-a"}]);
  await assert.rejects(loadTenantAssignment(claims, env, new URL("https://rental.test/api/tid-band-b/rentals")), {errorCode: "ACCESS_PROFILE_NOT_FOUND"});
});

test("unsupported roles and unrelated selected orgs do not block a member's own rentals", async () => {
  const {claims, env} = await memberFixture();
  claims.activeOrganizationId = "org_unmapped";
  assert.equal((await loadTenantAssignment(claims, env, new URL("https://rental.test/api/context"))).access_profile, "basic");
  claims.activeOrganizationId = "org_a";
  claims.clerkClient.users.getOrganizationMembershipList = async () => ({data: [{role: "org:custom", organization: {id: "org_a"}}], totalCount: 1});
  assert.equal((await loadTenantAssignment(claims, env, new URL("https://rental.test/api/context"))).access_profile, "basic");
});

test("Clerk tool roles remain separate from explicitly selected own-rentals scope", async () => {
  const {claims, env} = await memberFixture();
  claims.activeOrganizationId = "org_a";
  claims.clerkClient.users.getOrganizationMembershipList = async () => ({data: [{role: "org:admin", organization: {id: "org_a"}}], totalCount: 1});
  assert.equal((await loadTenantAssignment(claims, env, new URL("https://rental.test/api/context"))).role, "admin");
  const own = await loadTenantAssignment(claims, env, new URL("https://rental.test/api/tid-band-a/rentals?member_association=band-a"));
  assert.equal(own.role, "viewer");
  assert.equal(own.access_profile, "basic");
  await assert.rejects(loadTenantAssignment(claims, env, new URL("https://rental.test/api/context?member_association=band-b")), {errorCode: "TENANT_ACCESS_DENIED"});
});

test("inactive, missing email matches and banned accounts never grant member access", async () => {
  const {claims, env, members} = await memberFixture();
  members.get("tenant:band-a:members:member_a").is_active = false;
  await assert.rejects(loadTenantAssignment(claims, env, new URL("https://rental.test/api/context")), {errorCode: "ACCESS_PROFILE_NOT_FOUND"});
  members.get("tenant:band-a:members:member_a").is_active = true;
  members.get("tenant:band-a:members:member_a").access_email_hash = "different";
  await assert.rejects(loadTenantAssignment(claims, env, new URL("https://rental.test/api/context")), {errorCode: "ACCESS_PROFILE_NOT_FOUND"});
  claims.clerkUser.banned = true;
  await assert.rejects(loadTenantAssignment(claims, env, new URL("https://rental.test/api/context")), {errorCode: "ACCESS_PROFILE_DISABLED"});
});

test("members can select only their matched associations and roles fail safely on provider errors", async () => {
  const {claims, env, members, hash} = await memberFixture();
  members.set("tenant:band-b:index:members", ["member_b"]);
  members.set("tenant:band-b:members:member_b", {id: "member_b", access_email_hash: hash});
  claims.clerkClient.users.getOrganizationMembershipList = async () => { throw new Error("offline"); };
  const context = await loadTenantAssignment(claims, env, new URL("https://rental.test/api/context?member_association=band-b"));
  assert.equal(context.tenant_id, "band-b");
  assert.equal(context.member_associations.length, 2);
  assert.equal(context.role, "viewer");
});
