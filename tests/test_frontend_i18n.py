import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "public" / "app.js"
INDEX_HTML = ROOT / "public" / "index.html"
STYLES_CSS = ROOT / "public" / "styles.css"


def extract_translation_body(source: str, language: str) -> str:
    marker = f"  {language}: {{"
    start = source.index(marker) + len(marker)
    depth = 1
    index = start
    in_string = False
    escaped = False
    while index < len(source):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return source[start:index]
        index += 1
    raise AssertionError(f"Could not parse {language} translations")


def translation_keys(source: str, language: str) -> set[str]:
    body = extract_translation_body(source, language)
    return set(re.findall(r'"([^"]+)":', body))


class FrontendI18nTests(unittest.TestCase):
    def setUp(self):
        self.app_js = APP_JS.read_text(encoding="utf-8")
        self.index_html = INDEX_HTML.read_text(encoding="utf-8")
        self.styles_css = STYLES_CSS.read_text(encoding="utf-8")
        self.en_keys = translation_keys(self.app_js, "en")
        self.de_keys = translation_keys(self.app_js, "de")

    def test_english_and_german_dictionaries_have_same_keys(self):
        self.assertEqual(self.en_keys, self.de_keys)

    def test_html_i18n_attributes_reference_existing_keys(self):
        keys = set()
        keys.update(re.findall(r'data-i18n="([^"]+)"', self.index_html))
        keys.update(re.findall(r'data-i18n-title="([^"]+)"', self.index_html))
        keys.update(re.findall(r'data-i18n-aria-label="([^"]+)"', self.index_html))

        self.assertTrue(keys)
        self.assertLessEqual(keys, self.en_keys)

    def test_static_translation_calls_reference_existing_keys(self):
        keys = set(re.findall(r'(?<![A-Za-z0-9_$])t\("([^"`{]+)"', self.app_js))
        self.assertTrue(keys)
        self.assertLessEqual(keys, self.en_keys)

    def test_language_switch_exposes_en_and_de(self):
        self.assertIn('data-lang="en"', self.index_html)
        self.assertIn('data-lang="de"', self.index_html)

    def test_mobile_appbar_keeps_minimal_sticky_navigation(self):
        self.assertIn('class="mobile-appbar"', self.index_html)
        self.assertIn('id="mobileTenantLabel"', self.index_html)
        self.assertIn('id="mobileUserMenu" class="user-menu mobile-user-menu"', self.index_html)
        self.assertIn('href="#mainNav"', self.index_html)
        self.assertIn('class="to-top-button"', self.index_html)
        self.assertIn('id="mainNav" class="nav"', self.index_html)
        self.assertIn('id="associationHelp" class="association-help"', self.index_html)
        self.assertIn("const mobileTenantLabel = document.querySelector(\"#mobileTenantLabel\");", self.app_js)
        self.assertIn("if (mobileTenantLabel) mobileTenantLabel.textContent = state.tenant;", self.app_js)
        self.assertIn(".mobile-appbar {\n  display: none;", self.styles_css)
        self.assertIn(".mobile-appbar {\n    position: sticky;\n    top: 0;", self.styles_css)
        self.assertIn("min-height: 46px;", self.styles_css)
        self.assertIn(".mobile-menu-button", self.styles_css)
        self.assertIn(".sidebar > .brand {\n    display: none;", self.styles_css)
        self.assertIn(".to-top-button {\n    position: fixed;", self.styles_css)

    def test_unauthenticated_start_screen_is_localized(self):
        self.assertIn('authStatus: "checking"', self.app_js)
        self.assertIn('authReason: "checking"', self.app_js)
        self.assertIn('authEmail: ""', self.app_js)
        self.assertIn('state.authStatus = "signed_out"', self.app_js)
        self.assertIn("state.authReason = authReasonFromError(error);", self.app_js)
        self.assertIn("state.authEmail = authEmailFromError(error);", self.app_js)
        self.assertIn("try {\n    context = await apiContext();", self.app_js)
        self.assertIn("await loadData();\n    state.isLoading = false;\n    render();\n  } catch (error) {\n    state.isLoading = false;\n    render();\n    showMessage(error.message, true);", self.app_js)
        self.assertIn('function renderAuthStart()', self.app_js)
        self.assertIn('function authStartSteps()', self.app_js)
        self.assertIn('data-auth-retry', self.app_js)
        self.assertIn('data-join-request', self.app_js)
        self.assertIn('id="joinEmail"', self.app_js)
        self.assertIn('name="email"', self.app_js)
        self.assertIn('class="auth-request-row"', self.app_js)
        self.assertIn('"auth.email_help": "Use the same email you use to sign in."', self.app_js)
        self.assertIn('"auth.start_lead": "Rental Desk is available after your sign-in email and association permissions are confirmed."', self.app_js)
        self.assertIn('"auth.sign_in": "Sign-in"', self.app_js)
        self.assertIn('"auth.access_check": "After sign-in, we check your app access."', self.app_js)
        self.assertIn('"auth.access_check": "Nach der Anmeldung prüfen wir deinen App-Zugang."', self.app_js)
        self.assertIn('"auth.pending_hint": "Your request is pending.', self.app_js)
        self.assertIn('"auth.association_code": "Association code"', self.app_js)
        self.assertIn('"auth.association_code_placeholder": "association code"', self.app_js)
        self.assertIn('"messages.invalid_email": "Enter a valid email address"', self.app_js)
        self.assertIn('function accessRequestApi(payload)', self.app_js)
        self.assertIn('fetch("/api/access-requests"', self.app_js)
        self.assertIn("await accessRequestApi({email, tenant_id: tenant});", self.app_js)
        self.assertIn("state.accessRequestResult = result.data;", self.app_js)
        self.assertIn("saveStoredAccessRequest(result.data);", self.app_js)
        self.assertIn("auth.request_submitted", self.app_js)
        self.assertIn("auth.request_reference", self.app_js)
        self.assertIn("auth.request_contact", self.app_js)
        self.assertIn('"actions.request_join": "Request to join"', self.app_js)
        self.assertIn('"actions.request_join": "Beitritt anfragen"', self.app_js)
        self.assertIn('"actions.sign_in": "Sign in"', self.app_js)
        self.assertIn('"actions.sign_in": "Anmelden"', self.app_js)
        self.assertIn('window.location.assign("/api/auth/login")', self.app_js)
        self.assertIn('credentials: "same-origin"', self.app_js)
        self.assertIn('data-logout>${t("actions.logout")}', self.app_js)
        self.assertIn('function updateJoinRequestSubmit(form)', self.app_js)
        self.assertIn('function authEmailFromError(error)', self.app_js)
        self.assertIn('const emailValue = state.authEmail || request?.email || "";', self.app_js)
        self.assertIn('value="${escapeHtml(emailValue)}"', self.app_js)
        self.assertIn('button.disabled = !validAssociationTenantId(tenant);', self.app_js)
        self.assertIn('event.target.matches(\'[data-join-request] [name="tenant_id"]\')', self.app_js)
        self.assertIn('data-join-submit disabled', self.app_js)
        self.assertIn('placeholder="${escapeHtml(t("auth.association_code_placeholder"))}"', self.app_js)
        self.assertIn('const showAccessRequestForm = hasLikelySignInToken();', self.app_js)
        self.assertIn('step.action === "sign_in"', self.app_js)
        self.assertIn('class="primary-button auth-step-action" data-auth-retry', self.app_js)
        self.assertIn('${showAccessRequestForm ? `<div class="auth-start-actions">', self.app_js)
        self.assertIn('"auth.start_title": "Start with your association account"', self.app_js)
        self.assertIn('"auth.registration_hint": "Need access? Ask your association administrator', self.app_js)
        self.assertIn('"auth.start_title": "Mit dem Vereinszugang starten"', self.app_js)
        self.assertIn('"auth.registration_hint": "Brauchst du Zugriff? Bitte deine Vereinsadministration', self.app_js)
        self.assertIn('document.body.classList.toggle("is-auth-start", state.authStatus !== "signed_in")', self.app_js)
        self.assertIn(".auth-request-row {\n  display: grid;\n  grid-template-columns: minmax(0, 1fr) auto;", self.styles_css)
        self.assertIn(".auth-session-actions", self.styles_css)
        self.assertIn(".auth-request-row {\n    grid-template-columns: 1fr;", self.styles_css)
        self.assertIn(".auth-request-result", self.styles_css)
        auth_start_source = self.app_js[self.app_js.index("function renderAuthStart()"):self.app_js.index("function renderDashboard()")]
        self.assertNotIn("Cloudflare", auth_start_source)
        self.assertNotIn('value="${escapeHtml(state.tenant)}"', auth_start_source)

    def test_state_aware_landing_persists_access_requests(self):
        self.assertIn('const accessRequestStorageKey = "rentalAccessRequest";', self.app_js)
        self.assertIn("function loadStoredAccessRequest()", self.app_js)
        self.assertIn("localStorage.getItem(accessRequestStorageKey)", self.app_js)
        self.assertIn("JSON.parse(raw)", self.app_js)
        self.assertIn("function saveStoredAccessRequest(request)", self.app_js)
        self.assertIn("localStorage.setItem(accessRequestStorageKey, JSON.stringify(request));", self.app_js)
        self.assertIn("state.accessRequestResult = loadStoredAccessRequest();", self.app_js)
        self.assertIn("function authReasonFromError(error)", self.app_js)
        self.assertIn('return "missing_token";', self.app_js)
        self.assertIn('return "no_profile";', self.app_js)
        self.assertIn('return "access_denied";', self.app_js)
        self.assertIn('return "auth_error";', self.app_js)
        self.assertIn('message.includes("missing signed tenant context")', self.app_js)
        self.assertIn('message.includes("no user access profile")', self.app_js)
        self.assertIn('message.includes("user is not allowed for this tenant")', self.app_js)
        self.assertIn('error?.status === 401', self.app_js)
        self.assertIn("function hasLikelySignInToken()", self.app_js)
        self.assertIn("function currentAuthStartState()", self.app_js)
        self.assertIn('return state.accessRequestResult ? "pending_request" : state.authReason;', self.app_js)
        self.assertIn('state.authStatus === "signed_out" && ["no_profile", "access_denied"].includes(state.authReason)', self.app_js)
        self.assertIn('authState === "pending_request"', self.app_js)
        self.assertIn('authState === "access_denied"', self.app_js)
        self.assertIn('if (target.dataset.logout !== undefined) {\n      beginLogout();', self.app_js)
        self.assertIn('${hasLikelySignInToken() ? `<button type="button" class="ghost-button" data-logout>', self.app_js)
        self.assertIn('function normalizeAuthPath()', self.app_js)
        self.assertIn('window.history.replaceState(null, "", "/");', self.app_js)
        self.assertIn(".auth-start-steps .auth-step-current", self.styles_css)
        self.assertIn(".auth-start-steps .auth-step-done,\n.auth-start-steps .auth-step-waiting", self.styles_css)
        self.assertIn(".primary-button:disabled", self.styles_css)
        self.assertIn('const tenantRoutePrefix = "tid-";', self.app_js)
        self.assertIn("const reservedTenantIds = new Set", self.app_js)
        self.assertIn("function validAssociationTenantId(tenant)", self.app_js)
        self.assertIn('fetch(`/api/${tenantRoutePrefix}${state.tenant}${path}`', self.app_js)
        self.assertIn("const tenantAvailable = validAssociationTenantId(state.tenant);", self.app_js)

    def test_logout_return_clears_stale_authenticated_state(self):
        self.assertIn('const logoutPendingStorageKey = "rentalLogoutPending";', self.app_js)
        self.assertIn('const logoutReturnValue = "logged-out";', self.app_js)
        self.assertIn("function resetAuthenticatedState()", self.app_js)
        self.assertIn("function logoutReturnPending()", self.app_js)
        self.assertIn("function consumeLogoutReturn()", self.app_js)
        self.assertIn("function beginLogout()", self.app_js)
        self.assertIn('sessionStorage.setItem(logoutPendingStorageKey, "1");', self.app_js)
        self.assertIn('window.location.replace("/auth/logout");', self.app_js)
        self.assertIn("if (consumeLogoutReturn()) {", self.app_js)
        self.assertIn('window.addEventListener("pageshow", (event) => {', self.app_js)
        self.assertIn("if (event.persisted) window.location.reload();", self.app_js)

    def test_initial_loading_state_has_visual_placeholder(self):
        self.assertIn("isLoading: true", self.app_js)
        self.assertIn('document.body.classList.toggle("is-loading", Boolean(state.isLoading));', self.app_js)
        self.assertIn("state.isLoading = false;", self.app_js)
        self.assertIn("@keyframes loading-shimmer", self.styles_css)
        self.assertIn(".is-loading .workspace::before", self.styles_css)
        self.assertIn(".is-loading .view::before", self.styles_css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.styles_css)

    def test_messages_auto_dismiss_late_and_can_be_closed(self):
        self.assertIn('id="messageText"', self.index_html)
        self.assertIn('id="messageClose"', self.index_html)
        self.assertIn("}, 60000);", self.app_js)
        self.assertIn("messageClose?.addEventListener(\"click\"", self.app_js)
        self.assertIn(".message-close", self.styles_css)
        self.assertIn(".message[hidden]", self.styles_css)

    def test_static_shell_has_low_pii_security_metadata(self):
        self.assertIn('http-equiv="Content-Security-Policy"', self.index_html)
        self.assertIn("default-src 'self'", self.index_html)
        self.assertIn("connect-src 'self'", self.index_html)
        self.assertIn("object-src 'none'", self.index_html)
        self.assertIn("base-uri 'none'", self.index_html)
        self.assertIn('name="referrer" content="no-referrer"', self.index_html)

    def test_member_hint_labels_are_low_pii(self):
        self.assertIn('"fields.member_ref": "Roster ref"', self.app_js)
        self.assertIn('"fields.contact_hint": "Roster note"', self.app_js)
        self.assertIn('"fields.access_email": "Access email"', self.app_js)
        self.assertIn('"fields.access_email_configured": "Access email configured"', self.app_js)
        self.assertIn('"fields.access_email_help": "Leave empty to keep the configured email, or enter a new email to replace it."', self.app_js)
        self.assertIn('"table.contact": "Roster note"', self.app_js)
        self.assertIn('"fields.member_ref": "Mitgliederreferenz"', self.app_js)
        self.assertIn('"fields.contact_hint": "Listenhinweis"', self.app_js)
        self.assertIn('"fields.access_email": "Access-E-Mail"', self.app_js)
        self.assertIn('"fields.access_email_configured": "Access-E-Mail hinterlegt"', self.app_js)
        self.assertIn('"fields.access_email_help": "Leer lassen, um die hinterlegte E-Mail zu behalten, oder eine neue E-Mail zum Ersetzen eingeben."', self.app_js)
        self.assertIn('"table.contact": "Listenhinweis"', self.app_js)
        self.assertIn("renderField(name, label, type, required, span, record[name], record)", self.app_js)
        self.assertIn('name === "access_email" && record.access_email_hash && !value', self.app_js)
        self.assertIn('placeholder="${escapeHtml(t("fields.access_email_configured"))}"', self.app_js)

    def test_tenant_and_instrument_imports_have_client_pii_preflight(self):
        self.assertIn('const blockedImportPiiFields = new Set(["email", "phone", "telephone", "mobile", "address", "birthday", "birthdate"])', self.app_js)
        self.assertIn('const emailLikeImportValueFields = new Set(["display_name", "given_name", "family_name", "member_ref", "contact_hint", "description", "note", "provider", "actor", "contact_ref", "hitobito_group_ref", "inventory_ref"])', self.app_js)
        self.assertIn('const phoneLikeImportValueFields = new Set(["display_name", "contact_hint", "description", "note", "provider", "actor", "contact_ref", "hitobito_group_ref", "inventory_ref"])', self.app_js)
        self.assertIn("importEmailPattern.test(child)", self.app_js)
        self.assertIn("importPhonePattern.test(child)", self.app_js)
        self.assertIn('function assertLowPiiImport(payload)', self.app_js)
        tenant_import = re.search(r'const result = await api\("/import".{0,180}', self.app_js, re.DOTALL)
        instrument_import = re.search(r'const result = await api\("/instruments/import".{0,180}', self.app_js, re.DOTALL)
        hitobito_import = re.search(r'const result = await api\("/members/import/hitobito".{0,180}', self.app_js, re.DOTALL)

        self.assertIsNotNone(tenant_import)
        self.assertIsNotNone(instrument_import)
        self.assertIsNotNone(hitobito_import)
        self.assertIn("assertLowPiiImport(payload)", self.app_js[tenant_import.start() - 120:tenant_import.start()])
        self.assertIn("assertLowPiiImport(payload)", self.app_js[instrument_import.start() - 120:instrument_import.start()])
        self.assertNotIn("assertLowPiiImport(payload)", self.app_js[hitobito_import.start() - 120:hitobito_import.start()])

    def test_crud_forms_have_client_pii_preflight(self):
        self.assertIn('"messages.write_blocked_pii": "Remove contact details before saving ({fields})"', self.app_js)
        self.assertIn('"messages.write_blocked_pii": "Kontaktdaten vor dem Speichern entfernen ({fields})"', self.app_js)
        self.assertIn("function assertLowPiiWrite(payload, entity)", self.app_js)
        submit_handler = re.search(r'recordForm\.addEventListener\("submit".{0,420}', self.app_js, re.DOTALL)

        self.assertIsNotNone(submit_handler)
        self.assertIn("assertLowPiiWrite(payload, entity)", submit_handler.group(0))
        self.assertIn('const allowedFields = entity === "user_access" ? new Set(["email"]) : entity === "associations" ? new Set(["contact"]) : new Set()', self.app_js)

    def test_nullable_date_fields_can_be_cleared_from_forms(self):
        self.assertIn('"fields.return_date": "Return date"', self.app_js)
        self.assertIn('"fields.return_date": "Rückgabedatum"', self.app_js)
        self.assertIn('["return_date", "fields.return_date", "date", false]', self.app_js)
        self.assertIn("function shouldKeepEmptyField(entity, key)", self.app_js)
        self.assertIn('rentals: new Set(["due_date", "return_date"])', self.app_js)
        self.assertIn('service_records: new Set(["next_service_date"])', self.app_js)
        self.assertIn('if (payload[key] === "" && !shouldKeepEmptyField(entity, key)) delete payload[key];', self.app_js)

    def test_import_handlers_use_localized_json_parse_error(self):
        self.assertIn('"messages.import_invalid_json": "Import blocked: choose a valid JSON file"', self.app_js)
        self.assertIn('"messages.import_invalid_json": "Import blockiert: Bitte eine gültige JSON-Datei auswählen"', self.app_js)
        self.assertIn("async function readJsonFile(file)", self.app_js)
        self.assertIn('throw new Error(t("messages.import_invalid_json"))', self.app_js)
        self.assertEqual(self.app_js.count("JSON.parse(await file.text())"), 1)
        self.assertEqual(self.app_js.count("await readJsonFile(file)"), 3)

    def test_toolbar_filters_cover_service_and_member_states(self):
        self.assertIn('"filter.service_due_soon": "service due soon"', self.app_js)
        self.assertIn('"filter.service_overdue": "service overdue"', self.app_js)
        self.assertIn('"filter.service_due_soon": "Service bald fällig"', self.app_js)
        self.assertIn('"filter.service_overdue": "Service überfällig"', self.app_js)
        self.assertIn('["all", "available", "rented", "overdue", "watch", "needs_service", "in_service", "service_due_soon", "service_overdue"]', self.app_js)
        self.assertIn('["all", "good", "watch", "needs_service", "in_service", "retired", "service_due_soon", "service_overdue"]', self.app_js)
        self.assertIn('["all", "active", "inactive"]', self.app_js)
        self.assertIn("function filterLabel(filter)", self.app_js)
        self.assertIn("function itemMatchesFilter(item, filter)", self.app_js)
        self.assertIn('dueStatus === "due_soon"', self.app_js)
        self.assertIn('dueStatus === "overdue"', self.app_js)
        self.assertIn("(item.service_condition || item.condition) === filter", self.app_js)
        self.assertIn('filter === "inactive" && "is_active" in item', self.app_js)

    def test_service_records_are_a_clickable_crud_view(self):
        self.assertIn('data-view="service_records"', self.index_html)
        self.assertIn('"views.service_records": "Service"', self.app_js)
        self.assertIn('"actions.new_service_records": "New Service"', self.app_js)
        self.assertIn('"sections.service_details": "Service details"', self.app_js)
        self.assertIn('if (state.view === "service_records") renderCollection("service_records")', self.app_js)
        self.assertIn('function renderServiceTable(items)', self.app_js)
        self.assertIn('data-open="service_records"', self.app_js)
        self.assertIn('function renderServiceDetail(item)', self.app_js)
        self.assertIn('renderServiceJourney(services, caps, item.id)', self.app_js)
        self.assertIn('["instrument_id", "fields.instrument_id", "instrument", true]', self.app_js)

    def test_rental_and_service_instrument_selectors_are_distinct(self):
        self.assertIn('["instrument_id", "fields.instrument_id", "rental_instrument", true]', self.app_js)
        self.assertIn('if (type === "rental_instrument")', self.app_js)
        self.assertIn('item.status === "available" || item.id === value', self.app_js)
        self.assertIn('function renderInstrumentSelect(name, label, requiredAttr, full, value, options)', self.app_js)
        self.assertIn('function instrumentOptionLabel(item)', self.app_js)
        self.assertIn('item.service_condition || "good"', self.app_js)

    def test_service_due_status_uses_date_only_math(self):
        self.assertIn("function dateOrdinal(value)", self.app_js)
        self.assertIn("function todayOrdinal()", self.app_js)
        self.assertIn("const daysUntilDue = due - todayOrdinal()", self.app_js)
        self.assertNotIn("(due - today) / 86400000", self.app_js)

    def test_admin_center_uses_platform_admin_capability(self):
        self.assertIn("platform_admin", self.app_js)
        self.assertIn('capabilities().platform_admin ? adminApi("/associations")', self.app_js)
        self.assertIn('capabilities().admin ? adminApi("/users")', self.app_js)
        self.assertIn('capabilities().admin ? adminApi("/access-requests")', self.app_js)
        self.assertIn('button.hidden = !caps.admin', self.app_js)
        self.assertIn('if (state.view === "admin" && !caps.admin)', self.app_js)

    def test_admin_center_exposes_user_management(self):
        self.assertIn('"actions.new_user": "New User"', self.app_js)
        self.assertIn('"actions.new_user": "Neuer Benutzer"', self.app_js)
        self.assertIn('"actions.export_tenant_access": "Export Access KV"', self.app_js)
        self.assertIn('"actions.export_tenant_access": "Access-KV exportieren"', self.app_js)
        self.assertIn('"sections.users": "Users"', self.app_js)
        self.assertIn('"sections.users": "Benutzer"', self.app_js)
        self.assertIn('"sections.access_requests": "Join requests"', self.app_js)
        self.assertIn('"sections.access_requests": "Beitrittsanfragen"', self.app_js)
        self.assertIn("users: []", self.app_js)
        self.assertIn("accessRequests: []", self.app_js)
        self.assertIn("function renderUserTable(items)", self.app_js)
        self.assertIn("function renderUserDetail(userId)", self.app_js)
        self.assertIn("function renderAccessRequestTable(items)", self.app_js)
        self.assertIn("function approveAccessRequest(id)", self.app_js)
        self.assertIn("function denyAccessRequest(id)", self.app_js)
        self.assertIn('data-new-user', self.app_js)
        self.assertIn("data-edit-user", self.app_js)
        self.assertIn("data-delete-user", self.app_js)
        self.assertIn("data-approve-request", self.app_js)
        self.assertIn("data-deny-request", self.app_js)
        self.assertIn("data-export-tenant-access", self.app_js)
        self.assertIn('data-open="user_access"', self.app_js)
        self.assertIn('["email", "fields.email", "email", true]', self.app_js)
        self.assertIn('["tenant_roles", "fields.tenant_roles", "tenant_roles", false, "full"]', self.app_js)
        self.assertIn('["member_links", "fields.member_links", "member_links", false, "full"]', self.app_js)
        self.assertIn('function renderTenantRoleRow(role = {})', self.app_js)
        self.assertIn('function renderMemberLinkRow(link = {})', self.app_js)
        self.assertIn('function renderTenantSelect(name, value)', self.app_js)
        self.assertIn('function renderMemberLinkSelect(value)', self.app_js)
        self.assertIn('data-add-tenant-role', self.app_js)
        self.assertIn('data-remove-tenant-role', self.app_js)
        self.assertIn('data-add-member-link', self.app_js)
        self.assertIn('data-remove-member-link', self.app_js)
        self.assertIn('[name="tenant_roles_tenant_id"]', self.app_js)
        self.assertIn('[name="member_links_tenant_id"]', self.app_js)
        self.assertIn('[name="member_links_member_id"]', self.app_js)
        self.assertIn('await adminApi("/users", {method: "POST"', self.app_js)
        self.assertIn('await adminApi(`/users/${id}`, {method: "PUT"', self.app_js)
        self.assertIn('await adminApi(`/users/${id}`, {method: "DELETE"', self.app_js)
        self.assertIn('adminApi("/users/export/tenant-access")', self.app_js)
        self.assertIn('state.detail.entity === "user_access"', self.app_js)
        self.assertIn("function globalRolePill(role)", self.app_js)
        self.assertIn("function accessProfilePill(profile)", self.app_js)

    def test_row_action_buttons_do_not_trigger_drilldown_clicks(self):
        self.assertIn('const target = event.target.closest("button");', self.app_js)
        self.assertIn("event.stopPropagation();", self.app_js)
        self.assertIn('const row = event.target.closest("[data-open]");', self.app_js)

    def test_mobile_layout_turns_tables_into_labeled_cards(self):
        self.assertIn("@media (max-width: 680px)", self.styles_css)
        self.assertIn("table,\n  thead,\n  tbody,\n  tr,\n  td {\n    display: block;", self.styles_css)
        self.assertIn("td::before", self.styles_css)
        self.assertIn("content: attr(data-label)", self.styles_css)
        self.assertIn("table {\n    min-width: 0;", self.styles_css)
        self.assertIn('data-label="${t("table.name")}"', self.app_js)
        self.assertIn('data-label="${t("table.status")}"', self.app_js)
        self.assertIn('data-label="${t("table.action")}"', self.app_js)

    def test_mobile_rows_render_inline_detail_flydown(self):
        self.assertIn("function renderInlineDetail(entity, id, colspan)", self.app_js)
        self.assertIn("function renderAnyDetail(entity, id)", self.app_js)
        self.assertIn('renderInlineDetail("instruments", item.id, 8)', self.app_js)
        self.assertIn('renderInlineDetail("members", item.id, 5)', self.app_js)
        self.assertIn('renderInlineDetail("rentals", item.id, 6)', self.app_js)
        self.assertIn('renderInlineDetail("service_records", item.id, 6)', self.app_js)
        self.assertIn('renderInlineDetail("history", item.id, 6)', self.app_js)
        self.assertIn('renderInlineDetail("associations", item.tenant_id, 7)', self.app_js)
        self.assertIn('renderInlineDetail("user_access", item.id, 6)', self.app_js)
        self.assertIn(".inline-detail-row {\n  display: none;", self.styles_css)
        self.assertIn(".inline-detail-row {\n    display: block;", self.styles_css)
        self.assertIn(".split-view > .detail-panel {\n    display: none;", self.styles_css)
        self.assertIn("data-close-detail", self.app_js)

    def test_mobile_top_controls_wrap_without_overlap(self):
        self.assertIn("body {\n  margin: 0;\n  min-height: 100vh;\n  background: var(--bg);\n  color: var(--ink);\n  overflow-x: hidden;", self.styles_css)
        self.assertIn(".sidebar {\n    position: sticky;", self.styles_css)
        self.assertIn(".nav {\n    display: flex;\n    overflow-x: auto;", self.styles_css)
        self.assertIn(".sidebar {\n    position: static;\n    padding: 12px;\n    gap: 8px;", self.styles_css)
        self.assertIn(".nav {\n    display: grid;\n    grid-template-columns: repeat(4, minmax(0, 1fr));", self.styles_css)
        self.assertIn("overflow: visible;", self.styles_css)
        self.assertIn(".language-box > span {\n    display: none;", self.styles_css)
        self.assertIn(".topbar-actions {\n    display: grid;", self.styles_css)
        self.assertIn("grid-template-columns: repeat(5, 36px);", self.styles_css)
        self.assertIn(".topbar-actions .utility-action::before", self.styles_css)
        self.assertIn(".segmented {\n    width: 100%;", self.styles_css)
        self.assertIn("overflow-wrap: anywhere;", self.styles_css)
        self.assertIn(".record-dialog {\n    width: 100%;", self.styles_css)
        self.assertIn("margin: 0;", self.styles_css)

    def test_mobile_utility_actions_and_user_menu_are_scoped(self):
        self.assertIn('id="sessionButton"', self.index_html)
        self.assertIn('id="mobileSessionButton"', self.index_html)
        self.assertIn("data-session-action", self.index_html)
        self.assertIn('id="userMenu" class="user-menu tenant-user-menu"', self.index_html)
        self.assertIn('id="userMenuEmail"', self.index_html)
        self.assertIn('id="mobileUserMenuEmail"', self.index_html)
        self.assertIn('data-logout data-i18n="actions.logout"', self.index_html)
        self.assertIn('"actions.logout": "Log out"', self.app_js)
        self.assertIn('"actions.logout": "Abmelden"', self.app_js)
        self.assertIn('window.location.replace("/auth/logout")', self.app_js)
        self.assertIn('class="ghost-button utility-action" data-icon="⇩"', self.index_html)
        self.assertIn('class="ghost-button utility-action" data-icon="⇧"', self.index_html)
        self.assertIn("const userMenu = document.querySelector(\"#userMenu\");", self.app_js)
        self.assertIn("const mobileUserMenu = document.querySelector(\"#mobileUserMenu\");", self.app_js)
        self.assertIn("function renderUserMenu()", self.app_js)
        self.assertIn("function renderSessionButtons()", self.app_js)
        self.assertIn('const label = t(signedIn ? "actions.logout" : "actions.sign_in");', self.app_js)
        self.assertIn('const sessionAction = event.target.closest("[data-session-action]");', self.app_js)
        self.assertIn("[mobileUserMenu, mobileUserMenuEmail, mobileUserMenuTenant, mobileUserMenuRole, mobileUserMenuAccess]", self.app_js)
        self.assertIn("menu.hidden = state.authStatus !== \"signed_in\";", self.app_js)
        self.assertIn('hitobitoImportButton.hidden = basic || state.view !== "members";', self.app_js)
        self.assertIn("context?.user_email || context?.actor_id", self.app_js)
        self.assertIn(".user-menu summary::before", self.styles_css)
        self.assertIn(".user-menu summary::after", self.styles_css)
        self.assertIn("grid-template-columns: minmax(0, 1fr) 42px 42px;", self.styles_css)
        self.assertIn(".tenant-user-menu {\n    display: none;", self.styles_css)
        self.assertIn(".user-card {\n  position: absolute;", self.styles_css)
        self.assertIn(".tenant-user-menu .user-card {\n  left: calc(-1 * (24px + 18px));\n  right: auto;\n  top: auto;\n  bottom: calc(100% + 8px);", self.styles_css)
        self.assertIn(".mobile-user-menu .user-card {\n    right: 0;\n    left: auto;", self.styles_css)
        self.assertIn("color: var(--ink);", self.styles_css)
        self.assertIn(".logout-button {\n  width: 100%;", self.styles_css)
        self.assertIn(".sidebar-session-button {\n  width: 100%;", self.styles_css)
        self.assertIn(".mobile-session-button {\n    display: flex;", self.styles_css)
        self.assertIn("function closeUserMenus(except = null)", self.app_js)
        self.assertIn('menu.addEventListener("toggle", () => {', self.app_js)
        self.assertIn('document.addEventListener("focusin", (event) => {', self.app_js)
        self.assertIn('if (event.key !== "Escape") return;', self.app_js)
        self.assertIn('if (menu.hidden) menu.open = false;', self.app_js)

    def test_basic_profile_gets_customer_dashboard_and_hidden_chrome(self):
        self.assertIn("function isBasicProfile()", self.app_js)
        self.assertIn('capabilities().access_profile === "basic"', self.app_js)
        self.assertIn('if (basic && state.view !== "dashboard")', self.app_js)
        self.assertIn('button.hidden = button.dataset.view !== "dashboard";', self.app_js)
        self.assertIn('const userMenuVisible = state.authStatus === "signed_in";', self.app_js)
        self.assertIn('if (tenantBox) tenantBox.hidden = !switcherVisible && !metaVisible && !userMenuVisible;', self.app_js)
        self.assertIn('if (tenantRow) tenantRow.hidden = !switcherVisible && !userMenuVisible;', self.app_js)
        self.assertIn("const associationHelp = document.querySelector(\"#associationHelp\");", self.app_js)
        self.assertIn("function renderAssociationHelp()", self.app_js)
        self.assertIn('isBasicProfile() && Boolean(contact)', self.app_js)
        self.assertIn('mailto:${escapeHtml(contact)}', self.app_js)
        self.assertIn('renderAssociationHelp();', self.app_js)
        self.assertIn('"labels.need_help": "Need help?"', self.app_js)
        self.assertIn('"labels.need_help": "Brauchst du Hilfe?"', self.app_js)
        self.assertIn("function renderBasicDashboard()", self.app_js)
        self.assertIn("function renderCustomerRentalCard(rental)", self.app_js)
        self.assertIn("function renderCustomerRentalJourney(rental)", self.app_js)
        self.assertIn('"fields.forever": "Forever"', self.app_js)
        self.assertIn('"fields.forever": "Unbefristet"', self.app_js)
        self.assertIn("daysUntilDue <= 31", self.app_js)
        self.assertIn("is-soon", self.app_js)
        self.assertIn("is-overdue", self.app_js)
        self.assertIn('"sections.my_rentals": "My rentals"', self.app_js)
        self.assertIn('"sections.my_rentals": "Meine Ausleihen"', self.app_js)
        self.assertIn(".rental-card-grid", self.styles_css)
        self.assertIn(".mini-journey", self.styles_css)
        self.assertIn("align-items: start;", self.styles_css)
        self.assertIn(".mini-journey strong,\n.mini-journey small {\n  display: block;\n  min-height: 1.2em;", self.styles_css)
        self.assertIn(".mini-journey .is-soon::before", self.styles_css)
        self.assertIn(".mini-journey .is-overdue::before", self.styles_css)
        self.assertIn(".association-help {\n  display: grid;", self.styles_css)
        self.assertIn(".association-help[hidden] {\n  display: none;", self.styles_css)

    def test_reader_chrome_hides_switcher_and_operational_meta(self):
        self.assertIn("const tenantBox = document.querySelector(\".tenant-box\");", self.app_js)
        self.assertIn("const tenantMeta = document.querySelector(\".tenant-meta\");", self.app_js)
        self.assertIn("function shouldShowTenantSwitcher()", self.app_js)
        self.assertIn('context.mode === "local" || context.mode === "open"', self.app_js)
        self.assertIn("context.tenant_switchable || hasGlobalRole() || Number(context.tenant_count || 0) > 1", self.app_js)
        self.assertIn("function shouldShowOperationalMeta()", self.app_js)
        self.assertIn("return Boolean(caps.write || caps.admin);", self.app_js)
        self.assertIn("if (tenantBox) tenantBox.hidden = !switcherVisible && !metaVisible && !userMenuVisible;", self.app_js)
        self.assertIn("if (tenantMeta) tenantMeta.hidden = !metaVisible;", self.app_js)

    def test_signed_context_home_tenant_wins_over_local_storage(self):
        self.assertIn('state.tenant = context.mode === "local" || context.mode === "open"', self.app_js)
        self.assertIn("? localStorage.getItem(\"rentalTenant\") || state.tenant || context.tenant_id", self.app_js)
        self.assertIn(": context.tenant_id;", self.app_js)
        self.assertIn("if (state.context?.tenant_locked && !shouldShowTenantSwitcher()) return;", self.app_js)
        self.assertEqual(self.app_js.count("if (state.context?.tenant_locked && !shouldShowTenantSwitcher()) return;"), 2)

    def test_load_demo_button_disappears_when_tenant_has_data(self):
        self.assertIn("function hasExistingTenantData()", self.app_js)
        self.assertIn("Object.values(state.records).some((records) => Array.isArray(records) && records.length > 1)", self.app_js)
        self.assertIn("seedButton.hidden = basic || hasExistingTenantData();", self.app_js)
        self.assertIn("seedButton.disabled = !caps.admin || seedButton.hidden;", self.app_js)

    def test_data_refresh_clears_missing_detail_selection(self):
        self.assertIn("reconcileDetailSelection();", self.app_js)
        self.assertIn("function reconcileDetailSelection()", self.app_js)
        self.assertIn('state.detail.entity === "associations"', self.app_js)
        self.assertIn("state.associations.some((item) => item.tenant_id === state.detail.id)", self.app_js)
        self.assertIn("records.some((item) => item.id === state.detail.id)", self.app_js)


if __name__ == "__main__":
    unittest.main()
