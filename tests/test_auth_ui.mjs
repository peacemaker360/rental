import assert from "node:assert/strict";
import {test} from "node:test";

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
