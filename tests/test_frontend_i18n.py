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

    def test_unauthenticated_start_screen_is_localized(self):
        self.assertIn('authStatus: "checking"', self.app_js)
        self.assertIn('state.authStatus = "signed_out"', self.app_js)
        self.assertIn("try {\n    context = await apiContext();", self.app_js)
        self.assertIn("await loadData();\n  } catch (error) {\n    render();\n    showMessage(error.message, true);", self.app_js)
        self.assertIn('function renderAuthStart()', self.app_js)
        self.assertIn('data-auth-retry', self.app_js)
        self.assertIn('data-join-request', self.app_js)
        self.assertIn('function accessRequestApi(payload)', self.app_js)
        self.assertIn('fetch("/api/access-requests"', self.app_js)
        self.assertIn('"actions.request_join": "Request to join"', self.app_js)
        self.assertIn('"actions.request_join": "Beitritt anfragen"', self.app_js)
        self.assertIn('window.location.reload()', self.app_js)
        self.assertIn('"auth.start_title": "Start with your association account"', self.app_js)
        self.assertIn('"auth.registration_hint": "Need access? Ask your association administrator', self.app_js)
        self.assertIn('"auth.start_title": "Mit dem Vereinszugang starten"', self.app_js)
        self.assertIn('"auth.registration_hint": "Brauchst du Zugriff? Bitte deine Vereinsadministration', self.app_js)
        self.assertIn('document.body.classList.toggle("is-auth-start", state.authStatus !== "signed_in")', self.app_js)

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
        self.assertIn('"table.contact": "Roster note"', self.app_js)
        self.assertIn('"fields.member_ref": "Mitgliederreferenz"', self.app_js)
        self.assertIn('"fields.contact_hint": "Listenhinweis"', self.app_js)
        self.assertIn('"table.contact": "Listenhinweis"', self.app_js)

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
        self.assertIn('const allowedFields = entity === "user_access" ? new Set(["email"]) : new Set()', self.app_js)

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
        self.assertIn('function renderTenantRoleRow(role = {})', self.app_js)
        self.assertIn('data-add-tenant-role', self.app_js)
        self.assertIn('data-remove-tenant-role', self.app_js)
        self.assertIn('[name="tenant_roles_tenant_id"]', self.app_js)
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

    def test_mobile_top_controls_wrap_without_overlap(self):
        self.assertIn("body {\n  margin: 0;\n  min-height: 100vh;\n  background: var(--bg);\n  color: var(--ink);\n  overflow-x: hidden;", self.styles_css)
        self.assertIn(".sidebar {\n    position: sticky;", self.styles_css)
        self.assertIn(".nav {\n    display: flex;\n    overflow-x: auto;", self.styles_css)
        self.assertIn(".nav {\n    display: grid;\n    grid-template-columns: repeat(3, minmax(0, 1fr));", self.styles_css)
        self.assertIn("overflow: visible;", self.styles_css)
        self.assertIn(".topbar-actions {\n    display: grid;", self.styles_css)
        self.assertIn("grid-template-columns: 1fr;", self.styles_css)
        self.assertIn(".segmented {\n    width: 100%;", self.styles_css)
        self.assertIn("overflow-wrap: anywhere;", self.styles_css)
        self.assertIn(".record-dialog {\n    width: 100%;", self.styles_css)
        self.assertIn("margin: 0;", self.styles_css)

    def test_reader_chrome_hides_switcher_and_operational_meta(self):
        self.assertIn("const tenantBox = document.querySelector(\".tenant-box\");", self.app_js)
        self.assertIn("const tenantMeta = document.querySelector(\".tenant-meta\");", self.app_js)
        self.assertIn("function shouldShowTenantSwitcher()", self.app_js)
        self.assertIn('context.mode === "local" || context.mode === "open"', self.app_js)
        self.assertIn("context.tenant_switchable || hasGlobalRole() || Number(context.tenant_count || 0) > 1", self.app_js)
        self.assertIn("function shouldShowOperationalMeta()", self.app_js)
        self.assertIn("return Boolean(caps.write || caps.admin);", self.app_js)
        self.assertIn("if (tenantBox) tenantBox.hidden = !switcherVisible && !metaVisible;", self.app_js)
        self.assertIn("if (tenantMeta) tenantMeta.hidden = !metaVisible;", self.app_js)

    def test_load_demo_button_disappears_when_tenant_has_data(self):
        self.assertIn("function hasExistingTenantData()", self.app_js)
        self.assertIn("Object.values(state.records).some((records) => Array.isArray(records) && records.length > 1)", self.app_js)
        self.assertIn("seedButton.hidden = hasExistingTenantData();", self.app_js)
        self.assertIn("seedButton.disabled = !caps.admin || seedButton.hidden;", self.app_js)

    def test_data_refresh_clears_missing_detail_selection(self):
        self.assertIn("reconcileDetailSelection();", self.app_js)
        self.assertIn("function reconcileDetailSelection()", self.app_js)
        self.assertIn('state.detail.entity === "associations"', self.app_js)
        self.assertIn("state.associations.some((item) => item.tenant_id === state.detail.id)", self.app_js)
        self.assertIn("records.some((item) => item.id === state.detail.id)", self.app_js)


if __name__ == "__main__":
    unittest.main()
