import assert from "node:assert/strict";
import test from "node:test";
import {requestJson, commitVisible, observeCommit} from "../public/api_response.js";

const settings = {recover: true, translate: (key, values) => key + (values?.reference || ""), wait: async () => {}};

test("commit observation waits for both the acknowledged version and removed records", async () => {
  const expected = {revision: 4, commit_id: "commit"};
  const verify = records => !records.members.some(item => item.id === "deleted");
  const states = [
    {meta: {revision: 3}, records: {members: [{id: "deleted"}]}},
    {meta: {revision: 4, commit_id: "other"}, records: {members: []}},
    {meta: expected, records: {members: [{id: "deleted"}]}},
    {meta: expected, records: {members: []}}
  ];
  let calls = 0;
  const observed = await observeCommit(async () => states[calls++], expected, verify, () => true, {wait: async () => {}});
  assert.deepEqual(observed, states[3]);
  assert.equal(calls, 4);
  assert.equal(commitVisible({meta: {revision: 5}, records: {members: []}}, expected, verify), true);
});

test("commit waiting is bounded and stops on tenant changes without replaying a mutation", async () => {
  let calls = 0;
  const read = async () => { calls++; return {meta: {revision: 1}, records: {}}; };
  assert.equal(await observeCommit(read, {revision: 2}, () => true, () => true, {attempts: 3, wait: async () => {}}), null);
  assert.equal(calls, 3);
  calls = 0;
  assert.equal(await observeCommit(read, {revision: 2}, () => true, () => calls === 0, {wait: async () => {}}), null);
  assert.equal(calls, 1);
});

test("temporary data read failure recovers once, without retrying writes or system reads", async () => {
  for (const [method, recover, expected] of [["GET", true, 2], ["POST", true, 1], ["PUT", true, 1], ["DELETE", true, 1], ["GET", false, 1]]) {
    let calls = 0;
    const fetcher = async () => ++calls === 1 ? new Response("Bad Request", {status: 500}) : Response.json({data: ["recovered"]});
    const promise = requestJson(fetcher, "/api/test", {method}, {...settings, recover});
    if (expected === 2) assert.deepEqual(await promise, {data: ["recovered"]});
    else await assert.rejects(promise);
    assert.equal(calls, expected);
  }
});

test("data integrity, configuration, permission and conflict errors never auto retry", async () => {
  for (const [status, data] of [[503, {errorCode: "DATA_INTEGRITY_ERROR"}], [503, {errorCode: "AUTH_CONFIGURATION_ERROR"}], [503, {retryable: false}], [403, {error: "denied"}], [409, {error: "conflict", meta: {revision: 4}}]]) {
    let calls = 0;
    await assert.rejects(requestJson(async () => { calls += 1; return Response.json(data, {status}); }, "/api/test", {}, settings));
    assert.equal(calls, 1);
  }
});

test("exhausted recovery shows a safe reference and hides internal server contents", async () => {
  let calls = 0;
  await assert.rejects(requestJson(async () => {
    calls += 1;
    return Response.json({error: "secret path and private rental", stack: "private", requestId: "b".repeat(32)}, {status: 500});
  }, "/api/test", {}, settings), error => {
    assert.match(error.message, /bbbb/);
    assert.doesNotMatch(JSON.stringify({message: error.message, data: error.data}), /secret|private/);
    return true;
  });
  assert.equal(calls, 2);
});

test("network and invalid JSON failures get one read retry", async () => {
  for (const fail of [() => { throw new TypeError("secret URL"); }, () => new Response("bad json")]) {
    let calls = 0;
    const data = await requestJson(async () => ++calls === 1 ? fail() : Response.json({ok: true}), "/api/test", {}, settings);
    assert.deepEqual(data, {ok: true});
    assert.equal(calls, 2);
  }
});

test("auth-provider failures are not replayed as data requests", async () => {
  let calls = 0;
  await assert.rejects(requestJson(async () => {
    calls += 1;
    throw Object.assign(new Error("Sign-in unavailable"), {data: {errorCode: "AUTH_PROVIDER_UNAVAILABLE"}});
  }, "/api/test", {}, settings), /Sign-in unavailable/);
  assert.equal(calls, 1);
});
