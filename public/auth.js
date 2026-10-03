let clerk = null;
let configuration = null;
let initialization = null;
let mountedFlow = null;
const timeoutMs = 15000;
const taskMethods = {
  "choose-organization": "TaskChooseOrganization",
  "reset-password": "TaskResetPassword",
  "setup-mfa": "TaskSetupMFA"
};

function authError(message, errorCode, authReason) {
  return Object.assign(new Error(message), {data: {errorCode, authReason}});
}

function withTimeout(promise) {
  let timer;
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      timer = setTimeout(() => reject(authError("Sign-in took too long to respond. Check your connection and try again.", "AUTH_PROVIDER_UNAVAILABLE")), timeoutMs);
    })
  ]).finally(() => clearTimeout(timer));
}

function loadScript(src, publishableKey) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    const timer = setTimeout(() => {
      script.remove();
      reject(authError("Unable to load sign-in. Check your connection and try again.", "AUTH_PROVIDER_UNAVAILABLE"));
    }, timeoutMs);
    script.src = src;
    script.async = true;
    script.crossOrigin = "anonymous";
    if (publishableKey) script.dataset.clerkPublishableKey = publishableKey;
    script.onload = () => { clearTimeout(timer); resolve(); };
    script.onerror = () => {
      clearTimeout(timer);
      script.remove();
      reject(authError("Unable to load sign-in. Please retry.", "AUTH_PROVIDER_UNAVAILABLE"));
    };
    document.head.appendChild(script);
  });
}

export function getAuthState() {
  const session = clerk?.session;
  return {
    provider: configuration?.provider,
    status: session?.currentTask || session?.status === "pending" ? "pending" : session?.status === "active" ? "active" : "signed_out",
    task: session?.currentTask?.key || null,
    email: clerk?.user?.primaryEmailAddress?.emailAddress || session?.user?.primaryEmailAddress?.emailAddress || ""
  };
}

export function initializeAuth() {
  if (configuration?.provider === "mock" && !["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname)) {
    configuration = null;
    initialization = null;
    return Promise.reject(new Error("Mock sign-in is only available on localhost"));
  }
  if (!initialization) initialization = loadAuth().catch(error => {
    initialization = null;
    throw error;
  });
  return initialization;
}

async function loadAuth() {
  const response = await fetch("/api/auth/config", {cache: "no-store", signal: AbortSignal.timeout(timeoutMs)});
  configuration = await response.json();
  if (!response.ok) throw authError(configuration.error || "Sign-in is unavailable", configuration.errorCode || "AUTH_CONFIGURATION_ERROR");
  if (configuration.provider === "local") return;
  if (configuration.provider === "mock") {
    if (!["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname)) {
      configuration = null;
      throw new Error("Mock sign-in is only available on localhost");
    }
    return;
  }
  if (configuration.provider !== "clerk") throw authError("Sign-in is not configured", "AUTH_CONFIGURATION_ERROR");
  const origin = new URL(configuration.frontendApi).origin;
  if (!window.__internal_ClerkUICtor) await loadScript(`${origin}/npm/@clerk/ui@1/dist/ui.browser.js`);
  if (!window.Clerk) await loadScript(`${origin}/npm/@clerk/clerk-js@6/dist/clerk.browser.js`, configuration.publishableKey);
  clerk = window.Clerk;
  await withTimeout(clerk.load({
    ui: {ClerkUI: window.__internal_ClerkUICtor},
    taskUrls: Object.fromEntries(Object.keys(taskMethods).map(task => [task, `/?authTask=${task}`]))
  }));
  // A pending session is not a completed login. Never interrupt Clerk with a
  // redirect just because it created a session (or selected an organization).
  const fingerprint = () => JSON.stringify([clerk.session?.id, getAuthState().status, getAuthState().task, clerk.organization?.id]);
  let previous = fingerprint();
  clerk.addListener(() => {
    const next = fingerprint();
    if (next === previous) return;
    previous = next;
    window.dispatchEvent(new Event("rental-auth-change"));
  });
}

export function unmountAuthFlow() {
  if (!mountedFlow) return;
  const {node, component} = mountedFlow;
  mountedFlow = null;
  clerk?.[`unmount${component}`]?.(node);
}

export function mountAuthFlow(node) {
  if (!clerk || !node) return false;
  const auth = getAuthState();
  if (auth.status === "active") return false;
  const params = new URLSearchParams(window.location.search);
  let component;
  if (auth.status === "pending") {
    component = taskMethods[auth.task];
    if (!component || typeof clerk[`mount${component}`] !== "function") {
      throw authError("Your account has an unfinished sign-in step. Sign out and try again, or contact your association administrator.", "AUTH_TASK_UNSUPPORTED");
    }
  } else {
    component = params.get("__clerk_status") === "sign_up" || params.get("auth") === "sign-up" ? "SignUp" : "SignIn";
  }
  unmountAuthFlow();
  // Keep invitation query parameters in place for Clerk's prebuilt flow.
  const props = auth.status === "pending"
    ? {redirectUrlComplete: window.location.origin}
    : {routing: "hash", signInUrl: "/?auth=sign-in", signUpUrl: "/?auth=sign-up", forceRedirectUrl: window.location.origin, signInForceRedirectUrl: window.location.origin, signUpForceRedirectUrl: window.location.origin};
  clerk[`mount${component}`](node, props);
  mountedFlow = {node, component};
  return true;
}

export async function authFetch(url, options = {}) {
  const headers = new Headers(options.headers);
  if (configuration?.provider === "mock" && sessionStorage.getItem("rentalMockSession")) {
    headers.set("authorization", "Bearer rental-local-mock");
  }
  if (getAuthState().status === "pending") {
    throw authError("Complete your account setup to continue", "ACCESS_SESSION_PENDING", "session-pending");
  }
  if (getAuthState().status === "active") {
    const token = await withTimeout(clerk.session.getToken());
    if (token) headers.set("authorization", `Bearer ${token}`);
  }
  return fetch(url, {...options, headers, credentials: "same-origin", redirect: "error", signal: options.signal || AbortSignal.timeout(timeoutMs)});
}

export async function signIn() {
  if (configuration?.provider === "mock") {
    sessionStorage.setItem("rentalMockSession", "1");
    window.location.replace("/");
    return;
  }
  if (!clerk) throw authError("Sign-in is not ready. Please try again.", "AUTH_PROVIDER_UNAVAILABLE");
  if (clerk.session) {
    await withTimeout(clerk.session.reload());
    if (getAuthState().status === "active") await withTimeout(clerk.session.getToken({skipCache: true}));
    return;
  }
  if (mountedFlow) {
    mountedFlow.node.querySelector("input, button")?.focus();
    return;
  }
  clerk.openSignIn({forceRedirectUrl: window.location.origin, signUpForceRedirectUrl: window.location.origin});
}

export async function signOut() {
  sessionStorage.removeItem("rentalMockSession");
  if (clerk) await withTimeout(clerk.signOut({redirectUrl: window.location.origin}));
  else window.location.replace("/");
}

export function openAccount() {
  clerk?.openUserProfile();
}

const organizationSwitchers = new Set();

export function getActiveOrganization() {
  const organization = clerk?.organization;
  if (!organization) return null;
  return {id: organization.id, name: organization.name, imageUrl: organization.hasImage ? organization.imageUrl : null};
}

export function mountOrganizationSwitcher(node) {
  for (const previous of organizationSwitchers) {
    if (!previous.isConnected || getAuthState().status !== "active") {
      clerk?.unmountOrganizationSwitcher(previous);
      organizationSwitchers.delete(previous);
    }
  }
  if (!node || !clerk || getAuthState().status !== "active" || organizationSwitchers.has(node)) return;
  clerk.mountOrganizationSwitcher(node, {hidePersonal: true, organizationProfileMode: "modal"});
  organizationSwitchers.add(node);
}

export async function openOrganization(organizationId) {
  if (!clerk || getAuthState().status !== "active") throw new Error("Sign in before managing an organization");
  // Clerk independently enforces membership permissions in its profile UI.
  // A platform administrator without org membership must use Clerk Dashboard.
  if (clerk.organization?.id !== organizationId) await withTimeout(clerk.setActive({organization: organizationId}));
  clerk.openOrganizationProfile();
}
