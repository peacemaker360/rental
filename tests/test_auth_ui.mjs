import assert from "node:assert/strict";
import {test} from "node:test";
import {commitVisible, observeCommit} from "../public/api_response.js";

test("dashboard and table creation actions respect access and pending writes", async () => {
  const {readFile} = await import("node:fs/promises");
  const {runInNewContext} = await import("node:vm");
  const source = await readFile(new URL("../public/app.js", import.meta.url), "utf8");
  const functionSource = name => {
    const start = source.indexOf(`function ${name}(`);
    return source.slice(start, source.indexOf("\nfunction ", start + 1));
  };
  const state = {view: "members", mutationBusy: false};
  const caps = {write: true};
  const {dashboard, row} = runInNewContext(`${functionSource("renderDashboardActions")}\n${functionSource("renderCollectionCreateAction")}\n${functionSource("renderCollectionCreateRow")}\n({dashboard: renderDashboardActions, row: renderCollectionCreateRow})`, {
    state, capabilities: () => caps, isBasicProfile: () => caps.basic, t: key => key
  });
  for (const entity of ["rentals", "instruments", "members", "service_records"]) {
    assert.match(dashboard(), new RegExp(`data-create="${entity}"`));
  }
  assert.match(row("members", 5), /colspan="5".*data-create="members"/s);
  assert.equal(row("rentals", 6), "");
  state.mutationBusy = true;
  assert.equal((dashboard().match(/disabled/g) || []).length, 4);
  assert.match(row("members", 5), /disabled/);
  caps.write = false;
  assert.equal(dashboard(), "");
  assert.equal(row("members", 5), "");
  caps.write = true;
  caps.basic = true;
  assert.equal(dashboard(), "");
  assert.equal(row("members", 5), "");
});

test("JSON shortcuts are hidden for non-admins and dashboard import is hidden for admins", async () => {
  const {readFile} = await import("node:fs/promises");
  const {runInNewContext} = await import("node:vm");
  const source = await readFile(new URL("../public/app.js", import.meta.url), "utf8");
  const guards = source.split("\n").filter(line => /^  (exportButton|importButton)\.hidden =/.test(line)).join("\n");
  for (const admin of [false, true]) {
    for (const view of ["dashboard", "instruments", "members"]) {
      const context = {caps: {admin}, basic: false, state: {view}, exportButton: {}, importButton: {}};
      runInNewContext(guards, context);
      assert.equal(context.exportButton.hidden, !admin);
      assert.equal(context.importButton.hidden, !admin || view === "dashboard");
    }
  }
});

test("collection headers contain selection while attached rows contain only CSV transfer tools", async () => {
  const {readFile} = await import("node:fs/promises");
  const {runInNewContext} = await import("node:vm");
  const source = await readFile(new URL("../public/app.js", import.meta.url), "utf8");
  const functions = ["renderCollection", "renderCollectionCreateAction", "renderCollectionSelectionHeader", "renderCollectionCreateRow", "renderTableAction", "renderInstrumentTable", "renderMemberTable", "renderServiceTable", "renderRentalTable"].map(name => {
    const start = source.indexOf(`function ${name}(`);
    return source.slice(start, source.indexOf("\nfunction ", start + 1));
  }).join("\n");
  const entities = ["instruments", "members", "rentals", "service_records"];
  const state = {records: Object.fromEntries(entities.map(entity => [entity, []])), advancedToolsOpen: {instruments: true, members: true}, selectedIds: new Set(), detail: null};
  const caps = {admin: true, write: true};
  const view = {innerHTML: ""};
  const render = runInNewContext(`${functions}\nrenderCollection`, {
    state, view, capabilities: () => caps, isBasicProfile: () => caps.basic,
    filterItems: items => items, renderToolbar: () => "", renderDetail: () => '<aside class="detail-panel">Details</aside>', t: key => key,
    escapeHtml: value => String(value || ""), formatDate: () => "", conditionPill: () => "", statusPill: () => "",
    renderRecordSelection: () => "", renderInlineDetail: () => "", serviceDueStatus: () => "",
    serviceInstrumentName: () => "", serviceDuePill: () => ""
  });
  for (const entity of entities) {
    state.view = entity;
    for (const records of [[], [{id: "example"}]]) {
      state.records[entity] = records;
      render(entity);
      const header = view.innerHTML.slice(view.innerHTML.indexOf("<thead"), view.innerHTML.indexOf("</thead>"));
      assert.match(header, /data-bulk-toggle/);
      assert.equal((view.innerHTML.match(/data-create=/g) || []).length, 2);
      assert.doesNotMatch(view.innerHTML, /transfer-technical|data-import-instruments|data-export-instruments/);
      if (records.length) {
        assert.doesNotMatch(view.innerHTML, /table-action is-icon-only/);
        state.detail = {entity, id: "example"};
        render(entity);
        assert.match(view.innerHTML, /split-view collection-context/);
        assert.match(view.innerHTML, /table-action is-icon-only/);
        assert.match(view.innerHTML, /aria-label="actions.edit: example" title="actions.edit: example"/);
        assert.match(view.innerHTML, /aria-label="actions.delete: example" title="actions.delete: example"/);
        if (entity === "rentals") assert.match(view.innerHTML, /aria-label="actions.return: example"/);
        state.detail = null;
      }
      if (["members", "instruments"].includes(entity)) {
        assert.equal((view.innerHTML.match(/data-advanced-toggle=/g) || []).length, 2);
        assert.equal((view.innerHTML.match(/data-transfer=/g) || []).length, 4);
        assert.match(view.innerHTML, new RegExp(`id="transfer-${entity}-top"`));
        assert.match(view.innerHTML, new RegExp(`id="transfer-${entity}-bottom"`));
      }
    }
  }
  caps.admin = false;
  render("members");
  assert.doesNotMatch(view.innerHTML, /data-bulk-toggle|data-advanced-toggle/);
  caps.write = false;
  render("members");
  assert.doesNotMatch(view.innerHTML, /data-create=/);
});

test("admin data remains available when operational reads fail and admin navigation avoids them", async () => {
  const {readFile} = await import("node:fs/promises");
  const {runInNewContext} = await import("node:vm");
  const source = await readFile(new URL("../public/app.js", import.meta.url), "utf8");
  const start = source.indexOf("async function loadAdminData()");
  const end = source.indexOf("function stopMetadataPolling()", start);
  const state = {view: "dashboard", tenant: "tenant-a", records: {}, selectedIds: new Set()};
  let workingCalls = 0;
  const loadData = runInNewContext(`${source.slice(start, end)}; loadData`, {
    state, authGeneration: 1, capabilities: () => ({admin: true}), getAuthState: () => ({provider: "clerk"}),
    adminApi: async path => ({data: path === "/admissions" ? {organizations: [{id: "org_a"}]} : []}),
    api: async () => { workingCalls++; throw new Error("working data unavailable"); },
    render() {}, renderOrganizationChrome() {}, startMetadataPolling() {}
  });
  await assert.rejects(loadData(), /working data unavailable/);
  assert.equal(state.admissions.organizations[0].id, "org_a");
  state.view = "admin";
  await loadData();
  assert.equal(workingCalls, 1);
  assert.equal(state.adminErrors.length, 0);
});

test("deletion stays busy through stale visibility, rejects duplicate clicks, and never requests admin data", async () => {
  const {readFile} = await import("node:fs/promises");
  const {runInNewContext} = await import("node:vm");
  const source = await readFile(new URL("../public/app.js", import.meta.url), "utf8");
  const start = source.indexOf("async function loadAdminData()");
  const end = source.indexOf("function stopMetadataPolling()", start);
  const state = {tenant: "tenant-a", records: {members: [{id: "member"}]}, selectedIds: new Set(["member"])};
  const states = [];
  let writes = 0;
  let reads = 0;
  let acknowledge;
  const runDeletion = runInNewContext(`${source.slice(start, end)}; runDeletion`, {
    state, authGeneration: 1, commitVisible,
    observeCommit: (read, expected, verify, current) => observeCommit(read, expected, verify, current, {wait: async () => {}}),
    api: async path => {
      assert.equal(path, "/snapshot");
      assert.equal(state.mutationBusy, true);
      return ++reads === 1 ? {meta: {revision: 1}, records: {members: [{id: "member"}]}}
        : {meta: {revision: 2}, records: {members: []}, summary: {members: 0}};
    },
    render: () => states.push(state.operationStatus), applyMeta() {}, reconcileDetailSelection() {},
    showMessage() {}, t: key => key, handleMutationError: async () => assert.fail("Unexpected mutation failure")
  });
  const request = () => { writes++; return new Promise(resolve => { acknowledge = resolve; }); };
  const pending = runDeletion(request, records => !records.members.length);
  assert.equal(state.mutationBusy, true);
  await runDeletion(request, () => true);
  assert.equal(writes, 1);
  acknowledge({meta: {revision: 2}});
  await pending;
  assert.equal(reads, 2);
  assert.equal(state.mutationBusy, false);
  assert.equal(state.pendingCommit, null);
  assert.equal(state.records.members.length, 0);
  assert.ok(states.includes("delete.saving"));
  assert.ok(states.includes("delete.syncing"));
});

test("collection add action works on empty and populated lists and respects read-only access", async () => {
  const {readFile} = await import("node:fs/promises");
  const {runInNewContext} = await import("node:vm");
  const source = await readFile(new URL("../public/app.js", import.meta.url), "utf8");
  const start = source.indexOf("function renderCollection(entity)");
  const end = source.indexOf("function renderDetail(", start);
  const eventStart = source.indexOf('view.addEventListener("click",');
  const eventEnd = source.indexOf('view.addEventListener("submit",', eventStart);
  const entities = ["instruments", "members", "rentals", "service_records"];
  const state = {records: Object.fromEntries(entities.map(entity => [entity, []])), detail: null};
  const handlers = {};
  const view = {innerHTML: "", addEventListener: (name, fn) => { handlers[name] = fn; }};
  const dialogs = [];
  const caps = {write: true};
  const table = items => items.length ? '<div class="table-wrap"><table></table></div>' : '<div class="empty">No items</div>';
  const context = {
    state, view, capabilities: () => caps, isBasicProfile: () => caps.access_profile === "basic",
    t: key => key, filterItems: items => items, renderToolbar: () => "",
    renderInstrumentTable: table, renderMemberTable: table, renderServiceTable: table, renderRentalTable: table,
    openDialog: (entity, defaults) => dialogs.push({entity, defaults})
  };
  const renderCollection = runInNewContext(`${source.slice(start, end)}\n${source.slice(eventStart, eventEnd)}\nrenderCollection`, context);
  for (const entity of entities) {
    for (const records of [[], [{id: "existing"}]]) {
      state.records[entity] = records;
      renderCollection(entity);
      assert.match(view.innerHTML, new RegExp(`data-create="${entity}"`));
      assert.ok(view.innerHTML.lastIndexOf("collection-create") > view.innerHTML.indexOf(records.length ? "<table>" : "No items"));
    }
    const button = {dataset: {create: entity}};
    await handlers.click({target: {closest: selector => selector === "button" ? button : null}, stopPropagation() {}});
    assert.equal(dialogs.at(-1).entity, entity);
    if (entity === "service_records") assert.equal(dialogs.at(-1).defaults.condition, "good");
    else assert.equal(dialogs.at(-1).defaults.is_active, true);
  }
  for (const restricted of [{write: false}, {write: true, access_profile: "basic"}]) {
    Object.assign(caps, restricted);
    renderCollection("instruments");
    assert.doesNotMatch(view.innerHTML, /data-create/);
    const button = {dataset: {create: "instruments"}};
    await handlers.click({target: {closest: selector => selector === "button" ? button : null}, stopPropagation() {}});
    assert.equal(dialogs.length, 4);
  }
});

test("offline mock sign-in uses the normal bearer flow and clears the session on logout", async () => {
  const originals = {window: globalThis.window, sessionStorage: globalThis.sessionStorage, fetch: globalThis.fetch};
  const storage = new Map();
  const requests = [];
  const navigations = [];
  globalThis.window = {location: {
    hostname: "localhost", origin: "http://localhost:8787",
    replace: value => navigations.push(value),
  }};
  globalThis.sessionStorage = {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: key => storage.delete(key),
  };
  globalThis.fetch = async (url, options) => {
    requests.push({url, options});
    return new Response(JSON.stringify({provider: "mock"}));
  };
  try {
    const auth = await import("../public/auth.js?mock-test");
    await auth.initializeAuth();
    assert.deepEqual(requests.map(request => request.url), ["/api/auth/config"]);

    await auth.authFetch("/api/context");
    assert.equal(requests.at(-1).options.headers.has("authorization"), false);
    auth.signIn();
    assert.equal(navigations.at(-1), "/");
    await auth.authFetch("/api/context", {headers: {"x-test": "preserved"}});
    assert.equal(requests.at(-1).options.headers.get("authorization"), "Bearer rental-local-mock");
    assert.equal(requests.at(-1).options.headers.get("x-test"), "preserved");
    assert.equal(requests.at(-1).options.redirect, "error");

    await auth.signOut();
    assert.equal(storage.size, 0);
    assert.equal(navigations.at(-1), "/");
    await auth.authFetch("/api/context");
    assert.equal(requests.at(-1).options.headers.has("authorization"), false);

    window.location.hostname = "rental.example.org";
    await assert.rejects(auth.initializeAuth(), /only available on localhost/);
    storage.set("rentalMockSession", "1");
    await auth.authFetch("/api/context");
    assert.equal(requests.at(-1).options.headers.has("authorization"), false);
  } finally {
    for (const [key, value] of Object.entries(originals)) {
      if (value === undefined) delete globalThis[key];
      else globalThis[key] = value;
    }
  }
});

test("record save blocks duplicate submissions and exposes recoverable dialog errors", async () => {
  const {readFile} = await import("node:fs/promises");
  const {runInNewContext} = await import("node:vm");
  const source = await readFile(new URL("../public/app.js", import.meta.url), "utf8");
  const start = source.indexOf('recordForm.addEventListener("submit",');
  const end = source.indexOf('recordForm.addEventListener("click",', start);
  const attributes = new Map();
  let submit;
  let requests = 0;
  let rejectRequest;
  const saveButton = {disabled: false, textContent: "Save"};
  const errorSummary = {hidden: true, focused: false, focus() { this.focused = true; }};
  const dialog = {open: true, close() { this.open = false; }};
  runInNewContext(source.slice(start, end), {
    recordForm: {
      dataset: {entity: "instruments"},
      addEventListener: (_, callback) => { submit = callback; },
      getAttribute: key => attributes.get(key),
      setAttribute: (key, value) => attributes.set(key, value),
      removeAttribute: key => attributes.delete(key),
    },
    document: {querySelector: selector => selector === "#saveRecord" ? saveButton : errorSummary},
    dialog,
    formPayload: () => ({name: "Violin"}),
    assertLowPiiWrite: () => {},
    api: () => { requests++; return new Promise((_, reject) => { rejectRequest = reject; }); },
    handleMutationError: async () => {},
    t: key => key,
  });
  const event = {preventDefault() {}, submitter: {value: "default"}};
  const pending = submit(event);
  assert.equal(saveButton.disabled, true);
  assert.equal(saveButton.textContent, "actions.saving");
  await submit(event);
  await submit({...event, submitter: {value: "cancel"}});
  assert.equal(requests, 1);
  assert.equal(dialog.open, true);
  rejectRequest(new Error("Unable to save"));
  await pending;
  assert.equal(errorSummary.hidden, false);
  assert.equal(errorSummary.textContent, "Unable to save");
  assert.equal(errorSummary.focused, true);
  assert.equal(saveButton.disabled, false);
  assert.equal(saveButton.textContent, "actions.save");
  assert.equal(attributes.has("aria-busy"), false);
});

test("Clerk pending tasks resume without redirects or protected requests", async () => {
  const originals = {window: globalThis.window, fetch: globalThis.fetch};
  const events = [];
  const mounted = [];
  const requests = [];
  let listener;
  let loads = 0;
  let options;
  const pending = {id: "sess_1", status: "pending", currentTask: {key: "choose-organization"}, reload: async () => {}};
  const clerk = {
    session: null,
    load: async value => { loads++; options = value; },
    addListener: callback => { listener = callback; },
    mountTaskChooseOrganization: (node, props) => mounted.push({node, props, component: "organization"}),
    unmountTaskChooseOrganization: () => mounted.push({component: "unmount"}),
    mountTaskResetPassword: () => mounted.push({component: "password"}),
    unmountTaskResetPassword() {},
    mountTaskSetupMFA: () => mounted.push({component: "mfa"}),
    unmountTaskSetupMFA() {},
    mountSignUp: () => mounted.push({component: "signup"}),
    unmountSignUp() {},
    mountSignIn: () => mounted.push({component: "signin"}),
    unmountSignIn() {},
  };
  globalThis.window = {Clerk: clerk, __internal_ClerkUICtor: {}, location: {
    hostname: "localhost", origin: "http://localhost:8795", search: "?__clerk_status=sign_up&__clerk_ticket=invite-ticket",
    replace() { assert.fail("Authentication must not redirect on session creation"); },
  }, dispatchEvent: event => events.push(event.type)};
  globalThis.fetch = async (url, requestOptions) => {
    requests.push({url, options: requestOptions});
    return new Response(JSON.stringify({provider: "clerk", frontendApi: "https://example.clerk.accounts.dev", publishableKey: "pk_test_example"}));
  };
  try {
    const auth = await import("../public/auth.js?pending-flow-test");
    await Promise.all([auth.initializeAuth(), auth.initializeAuth()]);
    assert.equal(loads, 1);
    assert.equal(options.taskUrls["choose-organization"], "/?authTask=choose-organization");
    auth.mountAuthFlow({});
    assert.equal(mounted.at(-1).component, "signup");
    assert.match(window.location.search, /invite-ticket/);
    clerk.session = pending;
    listener();
    assert.deepEqual(events, ["rental-auth-change"]);
    listener();
    assert.equal(events.length, 1);
    auth.mountAuthFlow({});
    assert.equal(mounted.at(-1).component, "organization");
    assert.equal(mounted.at(-1).props.redirectUrlComplete, window.location.origin);
    await auth.signIn();
    await assert.rejects(auth.authFetch("/api/context"), error => error.data.errorCode === "ACCESS_SESSION_PENDING");
    assert.equal(requests.length, 1);
    for (const [key, component] of [["reset-password", "password"], ["setup-mfa", "mfa"]]) {
      pending.currentTask = {key};
      auth.mountAuthFlow({});
      assert.equal(mounted.at(-1).component, component);
    }
    pending.currentTask = {key: "future-task"};
    assert.throws(() => auth.mountAuthFlow({}), error => error.data.errorCode === "AUTH_TASK_UNSUPPORTED");
    // Completing the task changes status, even when the session ID stays the same.
    pending.status = "active";
    pending.currentTask = null;
    pending.getToken = async () => "active-token";
    listener();
    assert.equal(events.length, 2);
    auth.unmountAuthFlow();
    assert.equal(auth.mountAuthFlow({}), false);
    await auth.authFetch("/api/context");
    assert.equal(requests.at(-1).options.headers.get("authorization"), "Bearer active-token");
    clerk.organization = {id: "org_b"};
    listener();
    assert.equal(events.length, 3);
  } finally {
    for (const [key, value] of Object.entries(originals)) {
      if (value === undefined) delete globalThis[key];
      else globalThis[key] = value;
    }
  }
});

test("Clerk loading failures can be retried and are not cached as success", async () => {
  const originals = {window: globalThis.window, fetch: globalThis.fetch};
  let attempts = 0;
  globalThis.window = {Clerk: {
    load: async () => { if (++attempts === 1) throw new Error("Service unavailable"); },
    addListener() {},
  }, __internal_ClerkUICtor: {}};
  globalThis.fetch = async () => new Response(JSON.stringify({provider: "clerk", frontendApi: "https://example.clerk.accounts.dev", publishableKey: "pk_test_example"}));
  try {
    const auth = await import("../public/auth.js?retry-flow-test");
    await assert.rejects(auth.initializeAuth(), /Service unavailable/);
    await auth.initializeAuth();
    assert.equal(attempts, 2);
  } finally {
    for (const [key, value] of Object.entries(originals)) {
      if (value === undefined) delete globalThis[key];
      else globalThis[key] = value;
    }
  }
});

test("auth errors distinguish setup, membership, verification and service failures", async () => {
  const {readFile} = await import("node:fs/promises");
  const {runInNewContext} = await import("node:vm");
  const source = await readFile(new URL("../public/app.js", import.meta.url), "utf8");
  const start = source.indexOf("function authReasonFromError(");
  const end = source.indexOf("function authEmailFromError(", start);
  const classify = runInNewContext(`${source.slice(start, end)}; authReasonFromError`);
  for (const [data, expected] of [
    [{errorCode: "ACCESS_SESSION_PENDING"}, "session_pending"],
    [{errorCode: "ACCESS_TOKEN_INVALID", authReason: "session-pending"}, "session_pending"],
    [{errorCode: "ACCESS_TOKEN_INVALID", authReason: "token-expired"}, "invalid_token"],
    [{errorCode: "ACCESS_PROFILE_NOT_FOUND"}, "no_profile"],
    [{errorCode: "ACCESS_REQUEST_PENDING"}, "pending_request"],
    [{errorCode: "AUTH_PROVIDER_UNAVAILABLE"}, "provider_unavailable"],
    [{errorCode: "AUTH_CONFIGURATION_ERROR"}, "configuration_error"],
    [{errorCode: "ACCESS_EMAIL_UNVERIFIED"}, "email_unverified"],
    [{errorCode: "ACCESS_PROFILE_DISABLED"}, "account_disabled"],
  ]) assert.equal(classify({data}), expected);
  assert.equal(classify({name: "TimeoutError"}), "provider_unavailable");
});


test("account setup and access failures produce distinct recovery copy", async () => {
  const {readFile} = await import("node:fs/promises");
  const {runInNewContext} = await import("node:vm");
  const source = await readFile(new URL("../public/app.js", import.meta.url), "utf8");
  const start = source.indexOf("function authStartPresentation()");
  const end = source.indexOf("function updateJoinRequestSubmit", start);
  const state = {authStatus: "signed_out", authReason: "session_pending"};
  const presentation = runInNewContext(`${source.slice(start, end)}; authStartPresentation`, {
    state, getAuthState: () => ({task: "choose-organization"})
  });
  assert.equal(presentation()[1], "auth.choose_organization");
  for (const [reason, description] of [
    ["invalid_token", "auth.expired"], ["no_profile", "auth.no_access_body"],
    ["pending_request", "auth.pending_body"], ["provider_unavailable", "auth.unavailable"],
    ["configuration_error", "auth.configuration"], ["account_disabled", "auth.account_disabled"]
  ]) {
    state.authReason = reason;
    assert.equal(presentation()[1], description);
  }
});

test("embedded provider controls keep click and keyboard propagation for organization selection", async () => {
  const {readFile} = await import("node:fs/promises");
  const {runInNewContext} = await import("node:vm");
  const source = await readFile(new URL("../public/app.js", import.meta.url), "utf8");
  const start = source.indexOf('view.addEventListener("click",');
  const end = source.indexOf('view.addEventListener("submit",', start);
  const handlers = {};
  const state = {detail: {entity: "instruments", id: "existing"}};
  let renders = 0;
  runInNewContext(source.slice(start, end), {
    view: {addEventListener: (name, fn) => { handlers[name] = fn; }},
    state, render: () => { renders++; }
  });
  const providerRoot = {};
  let stopped = false;
  const providerEvent = {
    target: {closest: selector => selector === "[data-auth-provider-ui]" ? providerRoot : {dataset: {}}},
    stopPropagation() { stopped = true; },
    preventDefault() { throw new Error("Provider event was cancelled"); }
  };
  await handlers.click(providerEvent);
  for (const key of ["Enter", "Escape"]) handlers.keydown({...providerEvent, key});
  assert.equal(stopped, false);
  assert.equal(renders, 0);
  assert.equal(state.detail.id, "existing");
  const appButton = {dataset: {}};
  await handlers.click({target: {closest: selector => selector === "button" ? appButton : null}, stopPropagation() { stopped = true; }});
  assert.equal(stopped, true);
  handlers.keydown({target: {closest: () => null}, key: "Escape"});
  assert.equal(state.detail, null);
  assert.equal(renders, 1);
  assert.match(source, /id="authOrganizationSwitcher"[^>]*data-auth-provider-ui/);
  assert.match(source, /id="clerkAuthFlow"[^>]*data-auth-provider-ui/);
});

test("organization switcher stays mounted while opened and changes refresh the app from personal or another org", async () => {
  const originals = {window: globalThis.window, fetch: globalThis.fetch};
  let listener;
  const mounts = [], unmounts = [], events = [];
  const clerk = {
    session: {id: "session_a", status: "active"}, organization: null,
    load: async () => {}, addListener: fn => { listener = fn; },
    mountOrganizationSwitcher: (node, props) => mounts.push({node, props}),
    unmountOrganizationSwitcher: node => unmounts.push(node),
  };
  globalThis.window = {Clerk: clerk, __internal_ClerkUICtor: {}, dispatchEvent: event => events.push(event.type)};
  globalThis.fetch = async () => new Response(JSON.stringify({provider: "clerk", frontendApi: "https://example.clerk.accounts.dev", publishableKey: "pk_test_example"}));
  try {
    const auth = await import("../public/auth.js?org-selection-regression");
    await auth.initializeAuth();
    const node = {isConnected: true};
    auth.mountOrganizationSwitcher(node);
    auth.mountOrganizationSwitcher(null);
    auth.mountOrganizationSwitcher(node);
    assert.equal(mounts.length, 1);
    assert.equal(mounts[0].props.hidePersonal, false);
    listener(); // Opening the menu without a session/org change must not trigger a rerender.
    assert.equal(events.length, 0);
    clerk.organization = {id: "org_a", name: "Association A"};
    listener();
    assert.deepEqual(events, ["rental-auth-change"]);
    clerk.organization = {id: "org_b", name: "Association B"};
    listener();
    clerk.organization = null;
    listener();
    assert.equal(events.length, 3);
    node.isConnected = false;
    const replacement = {isConnected: true};
    auth.mountOrganizationSwitcher(replacement);
    assert.deepEqual(unmounts, [node]);
    assert.equal(mounts.length, 2);
  } finally {
    for (const [key, value] of Object.entries(originals)) {
      if (value === undefined) delete globalThis[key]; else globalThis[key] = value;
    }
  }
});
