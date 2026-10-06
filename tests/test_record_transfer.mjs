import assert from "node:assert/strict";
import {test} from "node:test";
import {readFile} from "node:fs/promises";
import {runInNewContext} from "node:vm";
import {parseCsv, suggestMapping, makeDraft, validateDraft, serializeCsv, transferSamples} from "../public/record_transfer.js";

const draftFor = (csv, entity, existing = []) => {
  const parsed = parseCsv(csv);
  return validateDraft(makeDraft(parsed, suggestMapping(parsed.headers, entity), entity), entity, existing);
};

test("CSV accepts BOM, Excel separators, multiline quotes, CRLF and escaped quotes", () => {
  const parsed = parseCsv('\uFEFFsep=;\r\nname;serial;description\r\n"Clarinet; alto";CL-1;"Line 1\r\nLine ""2"""\r\n');
  assert.deepEqual(parsed.headers, ["name", "serial", "description"]);
  assert.deepEqual(parsed.rows, [["Clarinet; alto", "CL-1", 'Line 1\r\nLine "2"']]);
  assert.deepEqual(parseCsv('"name"\t"serial"\n"Violin"\t"V-1"').rows, [["Violin", "V-1"]]);
  assert.deepEqual(parseCsv('"name, label";serial\nFlute;F-1').headers, ["name, label", "serial"]);
});

test("CSV rejects malformed quotes, duplicate/empty headers, empty data and large files", () => {
  for (const csv of ['name,serial\n"bad,F-1', 'name,serial\n"bad"text,F-1', 'name,serial\nbad"quote,F-1']) assert.throws(() => parseCsv(csv), /csv/);
  assert.throws(() => parseCsv('name,NAME\na,b'), /headers/);
  assert.throws(() => parseCsv('name,\na,b'), /headers/);
  assert.throws(() => parseCsv('name,serial\n'), /empty/);
  assert.throws(() => parseCsv('x'.repeat(5 * 1024 * 1024 + 1)), /large/);
  assert.throws(() => parseCsv('name\n' + 'Flute\n'.repeat(2001)), /rows/);
});

test("templates round trip, export excludes internal/contact/access fields and neutralizes formulas", () => {
  for (const entity of ["members", "instruments"]) {
    const csv = serializeCsv(entity, [{...transferSamples[entity], access_email: "secret@example.org", access_email_hash: "secret", tenant_id: "private", email: "private", created_at: "yesterday"}], ";");
    assert.doesNotMatch(csv, /secret|private|yesterday|access_email/);
    const draft = draftFor(csv, entity);
    assert.deepEqual(draft.rows[0].errors, []);
  }
  const csv = serializeCsv("instruments", [{name: '=HYPERLINK("bad")', serial: "+REF", description: "\t@SUM(A1)"}]);
  assert.match(csv, /'=HYPERLINK/);
  const draft = draftFor(csv, "instruments");
  assert.equal(draft.rows[0].values.name, '=HYPERLINK("bad")');
  assert.equal(draft.rows[0].values.serial, "+REF");
});

test("mapped fields convert locally and unknown contact columns are omitted", () => {
  const draft = draftFor('Name;Mitgliedsnummer;Aktiv;Gruppen;Email\nAlex Example;M-1;nein;Woodwinds|Youth;private@example.org', "members");
  const row = draft.rows[0];
  assert.deepEqual(row.errors, []);
  assert.equal(row.record.is_active, false);
  assert.deepEqual(row.record.groups, ["Woodwinds", "Youth"]);
  assert.equal(row.record.member_ref, "M-1");
  assert.equal("Email" in row.record, false);
  assert.equal("contact_hint" in row.record, false);
  const instruments = draftFor('name;serial;value_chf;purchase_year\nFlute;F-1;1’250,50;2024', "instruments");
  assert.equal(instruments.rows[0].record.value_chf, 1250.5);
  assert.equal(instruments.rows[0].record.purchase_year, 2024);
});

test("invalid rows stay editable, become selected when fixed, and preserve explicit deselection", () => {
  const draft = draftFor('name,serial,value_chf,purchase_year\nFlute,,bad,24\nClarinet,C-1,100,2020', "instruments");
  const row = draft.rows[0];
  assert.equal(row.selected, false);
  assert.deepEqual(row.errors.map(error => error.code).sort(), ["number", "required", "year"]);
  row.values.serial = "F-1"; row.values.value_chf = "150,50"; row.values.purchase_year = "2024";
  draft.rows[1].selected = false; draft.rows[1].touched = true;
  validateDraft(draft, "instruments");
  assert.equal(row.selected, true);
  assert.deepEqual(row.errors, []);
  assert.equal(draft.rows[1].selected, false);
  const contact = draftFor('display_name,member_ref,contact_hint\nAlex,M-1,private@example.org', "members");
  assert.equal(contact.rows[0].errors[0].code, "contact");
});

test("duplicate references and ambiguous existing matches are blocked, exported member IDs preserve links", () => {
  const duplicate = draftFor('name,serial\nFlute,F-1\nFlute,f-1', "instruments");
  assert.ok(duplicate.rows.every(row => row.errors.some(issue => issue.code === "duplicate") && !row.selected));
  const existing = [{id: "m1", member_ref: "M-1"}, {id: "m2", member_ref: "M-2"}];
  const draft = draftFor('id,display_name,member_ref\nm1,Alex,M-1\nm2,Robin,M-2', "members", existing);
  assert.equal(draft.rows[0].targetId, "m1");
  assert.equal(draft.rows[0].action, "update");
  assert.equal("id" in draft.rows[0].record, false);
  const conflicting = draftFor('id,display_name,member_ref\nm1,Alex,M-2', "members", existing);
  assert.ok(conflicting.rows[0].errors.some(issue => issue.code === "ambiguous"));
  const unknown = draftFor('id,display_name,member_ref\nmissing,Alex,M-3', "members", existing);
  assert.ok(unknown.rows[0].errors.some(issue => issue.code === "unknownId"));
  const sameTarget = draftFor('id,display_name,member_ref\nm1,Alex,\n,Alex,M-1', "members", existing);
  assert.ok(sameTarget.rows.every(row => row.errors.some(issue => issue.code === "duplicate")));
});

test("ragged rows require explicit acknowledgement; no extra cells enter JSON", () => {
  const draft = draftFor('name,serial\nFlute,F-1,extra', "instruments");
  assert.equal(draft.rows[0].selected, false);
  assert.equal(draft.rows[0].errors[0].code, "shape");
  assert.deepEqual(draft.rows[0].record, {name: "Flute", serial: "F-1"});
  draft.rows[0].shapeError = false;
  validateDraft(draft, "instruments");
  assert.equal(draft.rows[0].selected, true);
});

async function appHarness() {
  const source = await readFile(new URL("../public/app.js", import.meta.url), "utf8");
  const start = source.indexOf("function openSpreadsheetFlow(");
  const end = source.indexOf("async function exportInstruments()", start);
  const state = {tenant: "test-association", lang: "en", authStatus: "signed_in", operationalLoaded: true, mutationBusy: false, records: {members: [], instruments: []}, meta: {revision: 1}};
  let flow;
  const requests = [];
  const context = {state, authGeneration: 1, capabilities: () => ({admin: true}), isBasicProfile: () => false, render() {}, t: key => key,
    openRecordTransfer: options => { flow = options; }, loadData: async () => {}, applyMeta: meta => { state.meta = meta; },
    api: async (url, options) => { requests.push({url, options, revision: state.meta.revision}); return {meta: {revision: state.meta.revision + 1}}; }
  };
  const open = runInNewContext(`${source.slice(start, end)}\nopenSpreadsheetFlow`, context);
  return {open, context, state, requests, get flow() {return flow;}};
}

test("member submission uses existing JSON CRUD, advances revisions, preserves IDs and stops on first failure", async () => {
  const harness = await appHarness();
  harness.open("members");
  const rows = [{targetId: "member/one", record: {display_name: "Alex", member_ref: "M-1"}}, {record: {display_name: "Robin", member_ref: "M-2"}}];
  const saved = [];
  await harness.flow.submit(rows, row => saved.push(row));
  assert.deepEqual(harness.requests.map(item => [item.url, item.options.method, item.revision]), [["/members/member%2Fone", "PUT", 1], ["/members", "POST", 2]]);
  assert.equal(saved.length, 2);
  assert.equal(harness.state.mutationBusy, false);
  harness.context.api = async () => { throw new Error("unavailable"); };
  await assert.rejects(harness.flow.submit(rows, () => assert.fail("must not confirm a failed write")), /unavailable/);
  assert.equal(harness.state.mutationBusy, false);
});

test("instrument submission keeps the merge endpoint; permissions and tenant changes stop uploads", async () => {
  const harness = await appHarness();
  harness.context.capabilities = () => ({admin: false});
  harness.open("instruments");
  assert.equal(harness.flow, undefined);
  harness.context.capabilities = () => ({admin: true});
  harness.open("instruments");
  await harness.flow.submit([{record: {name: "Flute", serial: "F-1"}}], () => {});
  assert.equal(harness.requests[0].url, "/instruments/import");
  assert.deepEqual(JSON.parse(harness.requests[0].options.body), {instruments: [{name: "Flute", serial: "F-1"}]});
  harness.state.tenant = "other-association";
  await assert.rejects(harness.flow.submit([], () => {}), /revision_conflict/);
  assert.equal(harness.requests.length, 1);
});

test("preview-only required fields do not clear omitted columns when updating existing records", () => {
  const instruments = draftFor('serial,value_chf\nF-1,350', "instruments", [{id: "i1", name: "Concert flute", serial: "F-1", brand: "Yamaha"}]);
  assert.deepEqual(instruments.rows[0].record, {serial: "F-1", value_chf: 350});
  assert.deepEqual(instruments.rows[0].errors, []);
  const members = draftFor('id,display_name\nm1,Alex Updated', "members", [{id: "m1", display_name: "Alex", member_ref: "M-1"}]);
  assert.deepEqual(members.rows[0].record, {display_name: "Alex Updated"});
  assert.deepEqual(members.rows[0].errors, []);
  members.rows[0].editedFields.add("member_ref");
  members.rows[0].values.member_ref = "";
  validateDraft(members, "members", [{id: "m1", display_name: "Alex", member_ref: "M-1"}]);
  assert.equal(members.rows[0].record.member_ref, "");
});
