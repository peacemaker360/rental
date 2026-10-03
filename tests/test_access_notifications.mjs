import assert from "node:assert/strict";
import test from "node:test";
import {notifyOrganizationAdmins} from "../frontdoor/access_notifications.js";
import {createAccessRequest} from "../frontdoor/access_context_worker.js";

const association = {tenant_id: "band-a", clerk_organization_id: "org_a", display_name: "Band A"};
const request = {id: "access_request:test", email: "new@example.test", tenant_id: "band-a"};
function fixture() {
  const sent = [];
  const client = {
    organizations: {getOrganizationMembershipList: async ({organizationId}) => {
      assert.equal(organizationId, "org_a");
      return {totalCount: 3, data: [
        {role: "org:admin", publicUserData: {userId: "admin_a"}},
        {role: "org:operator", publicUserData: {userId: "operator"}},
        {role: "org:custom", permissions: ["org:sys_memberships:manage"], publicUserData: {userId: "admin_b"}},
      ]};
    }},
    users: {getUser: async id => ({primaryEmailAddressId: id, emailAddresses: [{id, emailAddress: `${id}@example.test`, verification: {status: "verified"}}]})}
  };
  const env = {ACCESS_REQUEST_FROM: "rental@example.test", ACCESS_REQUEST_EMAIL: {send: async message => sent.push(message)}};
  return {client, env, sent};
}

test("notifies only current admins of the requested org using verified email", async () => {
  const {client, env, sent} = fixture();
  const result = await notifyOrganizationAdmins(request, association, env, client, "https://rental.example.test");
  assert.equal(result.status, "sent");
  assert.deepEqual(sent.map(item => item.to), ["admin_a@example.test", "admin_b@example.test"]);
  assert.ok(sent.every(item => item.text.includes("?view=admin") && item.html.includes("Band A")));
  await notifyOrganizationAdmins({...request, notification: result}, association, env, client, "https://rental.example.test");
  assert.equal(sent.length, 2);
});

test("partial delivery can be retried without resending to successful recipients", async () => {
  const {client, env, sent} = fixture();
  const send = env.ACCESS_REQUEST_EMAIL.send;
  env.ACCESS_REQUEST_EMAIL.send = async message => {
    if (message.to.startsWith("admin_b")) throw new Error("private provider error");
    await send(message);
  };
  const first = await notifyOrganizationAdmins(request, association, env, client, "https://rental.example.test");
  assert.equal(first.status, "failed");
  assert.deepEqual(first.sent_user_ids, ["admin_a"]);
  assert.ok(!JSON.stringify(first).includes("private provider"));
  env.ACCESS_REQUEST_EMAIL.send = send;
  const second = await notifyOrganizationAdmins({...request, notification: first}, association, env, client, "https://rental.example.test");
  assert.equal(second.status, "sent");
  assert.equal(sent.length, 2);
});

test("unconfigured email and users without verified addresses are explicit failures", async () => {
  const {client, env, sent} = fixture();
  assert.equal((await notifyOrganizationAdmins(request, association, {}, client, "https://rental.example.test")).status, "not_configured");
  client.users.getUser = async () => ({emailAddresses: []});
  assert.equal((await notifyOrganizationAdmins(request, association, env, client, "https://rental.example.test")).status, "failed");
  assert.equal(sent.length, 0);
});

test("request creation validates mapping, derives identity and suppresses sequential duplicate mail", async () => {
  const {client, env, sent} = fixture();
  const values = new Map();
  env.RENTAL_KV = {get: async key => key === "associations:band-a" ? association : null};
  env.TENANT_ACCESS_KV = {get: async key => values.get(key) || null, put: async (key, value) => values.set(key, JSON.parse(value))};
  const claims = {email: "verified@example.test", clerkClient: client};
  const makeRequest = tenant => new Request("https://rental.example.test/api/access-requests", {method: "POST", body: JSON.stringify({tenant_id: tenant, email: "forged@example.test"})});
  await assert.rejects(createAccessRequest(makeRequest("unknown"), env, claims), {status: 404});
  assert.equal(values.size, 0);
  const response = await createAccessRequest(makeRequest("band-a"), env, claims);
  const body = await response.json();
  assert.equal(body.data.email, "verified@example.test");
  assert.equal(body.data.notification_status, "sent");
  assert.equal(body.data.notification, undefined);
  assert.ok(!JSON.stringify(body).includes("admin_a"));
  const duplicate = await createAccessRequest(makeRequest("band-a"), env, claims);
  assert.equal(duplicate.status, 200);
  assert.equal(sent.length, 2);
});
