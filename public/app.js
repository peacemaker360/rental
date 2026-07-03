const state = {
  tenant: localStorage.getItem("rentalTenant") || "demo-association",
  lang: localStorage.getItem("rentalLang") || (navigator.language?.toLowerCase().startsWith("de") ? "de" : "en"),
  view: "dashboard",
  search: "",
  status: "all",
  sort: "name",
  sortDirection: "asc",
  detail: null,
  records: {
    instruments: [],
    members: [],
    rentals: [],
    service_records: [],
    history: []
  },
  associations: [],
  users: [],
  summary: {},
  meta: {revision: 0, updated_at: null},
  context: null
};

const viewTitle = document.querySelector("#viewTitle");
const view = document.querySelector("#view");
const adminNavItem = document.querySelector('[data-view="admin"]');
const message = document.querySelector("#message");
const primaryAction = document.querySelector("#primaryAction");
const seedButton = document.querySelector("#seedButton");
const exportButton = document.querySelector("#exportButton");
const importButton = document.querySelector("#importButton");
const importFile = document.querySelector("#importFile");
const hitobitoImportButton = document.querySelector("#hitobitoImportButton");
const hitobitoFile = document.querySelector("#hitobitoFile");
const instrumentFile = document.querySelector("#instrumentFile");
const refreshButton = document.querySelector("#refreshButton");
const tenantInput = document.querySelector("#tenantInput");
const tenantLabel = document.querySelector("#tenantLabel");
const tenantRevision = document.querySelector("#tenantRevision");
const tenantUpdatedAt = document.querySelector("#tenantUpdatedAt");
const saveTenant = document.querySelector("#saveTenant");
const dialog = document.querySelector("#recordDialog");
const recordForm = document.querySelector("#recordForm");
const formFields = document.querySelector("#formFields");
const dialogTitle = document.querySelector("#dialogTitle");
const tenantPattern = /^[a-z0-9][a-z0-9_-]{1,62}$/;
const blockedImportPiiFields = new Set(["email", "phone", "telephone", "mobile", "address", "birthday", "birthdate"]);
const emailLikeImportValueFields = new Set(["display_name", "given_name", "family_name", "member_ref", "contact_hint", "description", "note", "provider", "actor", "contact_ref", "hitobito_group_ref", "inventory_ref"]);
const phoneLikeImportValueFields = new Set(["display_name", "contact_hint", "description", "note", "provider", "actor", "contact_ref", "hitobito_group_ref", "inventory_ref"]);
const importEmailPattern = /[^@\s]+@[^@\s]+\.[^@\s]+/;
const importPhonePattern = /(?=(?:\D*\d){7,})\+?[\d][\d\s()./-]{6,}\d/;
const languageButtons = document.querySelectorAll("[data-lang]");

const translations = {
  en: {
    "app.title": "Rental Desk",
    "app.eyebrow": "Instrument rental",
    "views.dashboard": "Dashboard",
    "views.instruments": "Instruments",
    "views.members": "Members",
    "views.rentals": "Rentals",
    "views.service_records": "Service",
    "views.history": "History",
    "views.admin": "Admin Center",
    "labels.tenant": "Tenant",
    "labels.language": "Language",
    "labels.revision": "Revision",
    "labels.updated_at": "Updated {date}",
    "labels.sort": "Sort",
    "tenant.title": "2-63 lowercase letters, numbers, hyphens, or underscores",
    "tenant.locked": "Tenant is provided by the signed-in context",
    "tenant.invalid": "Tenant id must use 2-63 lowercase letters, numbers, hyphens, or underscores",
    "actions.switch_tenant": "Switch tenant",
    "actions.load_demo": "Load Demo",
    "actions.export": "Export",
    "actions.import": "Import",
    "actions.import_hitobito": "Hitobito",
    "actions.export_instruments": "Export Inventory",
    "actions.import_instruments": "Import Inventory",
    "actions.export_tenant_access": "Export Access KV",
    "actions.refresh": "Refresh",
    "actions.cancel": "Cancel",
    "actions.close": "Close",
    "actions.save": "Save",
    "actions.edit": "Edit",
    "actions.open": "Open",
    "actions.delete": "Delete",
    "actions.return": "Return",
    "actions.view_all": "View All",
    "actions.history": "History",
    "actions.add_service": "Add Service",
    "actions.new_association": "New Association",
    "actions.new_user": "New User",
    "actions.new_instruments": "New Instrument",
    "actions.new_members": "New Member",
    "actions.new_rentals": "New Rental",
    "actions.new_service_records": "New Service",
    "actions.yes": "Yes",
    "actions.no": "No",
    "dialog.new": "New {entity}",
    "dialog.edit": "Edit {entity}",
    "entities.instrument": "Instrument",
    "entities.member": "Member",
    "entities.rental": "Rental",
    "entities.service_record": "Service Record",
    "entities.association": "Association",
    "entities.user_access": "User Access",
    "entities.associations": "associations",
    "entities.users": "users",
    "entities.instruments": "instruments",
    "entities.members": "members",
    "entities.service_records": "service records",
    "entities.history": "history",
    "fields.name": "Instrument",
    "fields.brand": "Brand",
    "fields.type": "Type",
    "fields.serial": "Serial",
    "fields.value_chf": "Value CHF",
    "fields.purchase_year": "Purchase year",
    "fields.description": "Description",
    "fields.display_name": "Name",
    "fields.given_name": "Given name",
    "fields.family_name": "Family name",
    "fields.member_ref": "Roster ref",
    "fields.contact_hint": "Roster note",
    "fields.is_active": "Active",
    "fields.instrument_id": "Instrument",
    "fields.member_id": "Member",
    "fields.start_date": "Start date",
    "fields.due_date": "Due date",
    "fields.note": "Note",
    "fields.service_date": "Service date",
    "fields.next_service_date": "Next service",
    "fields.condition": "Condition",
    "fields.job_type": "Job type",
    "fields.provider": "Provider",
    "fields.cost_chf": "Cost CHF",
    "fields.display_name_association": "Association name",
    "fields.short_name": "Short name",
    "fields.status": "Status",
    "fields.email": "Email",
    "fields.global_role": "Global role",
    "fields.access_profile": "Access profile",
    "fields.tenant_roles": "Tenant roles",
    "fields.member_links": "Member links",
    "fields.region": "Region",
    "fields.locale": "Locale",
    "fields.contact_ref": "Contact ref",
    "fields.hitobito_group_ref": "Hitobito group ref",
    "fields.inventory_ref": "Inventory ref",
    "table.name": "Name",
    "table.type": "Type",
    "table.serial": "Serial",
    "table.value": "Value",
    "table.status": "Status",
    "table.condition": "Condition",
    "table.last_service": "Last service",
    "table.next_service": "Next service",
    "table.tenant": "Tenant",
    "table.region": "Region",
    "table.updated": "Updated",
    "table.reference": "Reference",
    "table.contact": "Roster note",
    "table.instrument": "Instrument",
    "table.member": "Member",
    "table.start": "Start",
    "table.due": "Due",
    "table.when": "When",
    "table.action": "Action",
    "table.actor": "Actor",
    "table.rental": "Rental",
    "table.service": "Service",
    "stats.instruments": "Instruments",
    "stats.available": "Available",
    "stats.members": "Members",
    "stats.active_rentals": "Active rentals",
    "stats.overdue": "Overdue",
    "stats.service_attention": "Service attention",
    "sections.open_rentals": "Open rentals",
    "sections.attention": "Attention",
    "sections.instrument_details": "Instrument details",
    "sections.member_details": "Member details",
    "sections.rental_details": "Rental details",
    "sections.service_details": "Service details",
    "sections.association_details": "Association details",
    "sections.user_details": "User details",
    "sections.history_details": "History details",
    "sections.service_journey": "Service journey",
    "sections.rental_journey": "Rental journey",
    "sections.event_journey": "Event journey",
    "sections.associations": "Associations",
    "sections.users": "Users",
    "empty.no_overdue": "No overdue rentals",
    "empty.no_attention": "No rentals or service items need attention",
    "empty.no_service_records": "No service records",
    "empty.no_associations": "No associations",
    "empty.no_users": "No users",
    "empty.no_tenant_roles": "No tenant roles",
    "empty.no_instruments": "No instruments",
    "empty.no_members": "No members",
    "empty.no_rentals": "No rentals",
    "empty.no_history": "No history",
    "search.placeholder": "Search {entity}",
    "select.placeholder": "Select...",
    "sort.name": "Name",
    "sort.status": "Status",
    "sort.condition": "Condition",
    "sort.service_date": "Last service",
    "sort.next_service_date": "Next service",
    "sort.due_date": "Due date",
    "sort.date": "Date",
    "sort.tenant": "Tenant",
    "sort.asc": "Ascending",
    "sort.desc": "Descending",
    "filter.service_due_soon": "service due soon",
    "filter.service_overdue": "service overdue",
    "confirm.delete": "Delete this record?",
    "confirm.import": "Replace tenant \"{tenant}\" with records from this JSON file?",
    "confirm.import_hitobito": "Import members from this Hitobito JSON file into tenant \"{tenant}\"?",
    "confirm.import_instruments": "Merge instruments from this JSON file into tenant \"{tenant}\"?",
    "messages.saved": "{entity} saved",
    "messages.deleted": "{entity} deleted",
    "messages.returned": "Rental returned",
    "messages.demo_loaded": "Demo data loaded",
    "messages.export_downloaded": "Tenant export downloaded",
    "messages.import_complete": "Import complete: {instruments} instruments, {members} members",
    "messages.hitobito_import_complete": "Hitobito import complete: {created} created, {updated} updated",
    "messages.instrument_export_downloaded": "Instrument inventory export downloaded",
    "messages.tenant_access_export_downloaded": "Access KV export downloaded",
    "messages.instrument_import_complete": "Instrument import complete: {created} created, {updated} updated",
    "messages.import_blocked_pii": "Import blocked: remove contact fields before uploading ({fields})",
    "messages.import_invalid_json": "Import blocked: choose a valid JSON file",
    "messages.write_blocked_pii": "Remove contact details before saving ({fields})",
    "messages.revision_conflict": "This tenant changed in another session. The latest data is loaded; review and try again.",
    "status.all": "all",
    "status.available": "available",
    "status.rented": "rented",
    "status.active": "active",
    "status.overdue": "overdue",
    "status.returned": "returned",
    "status.inactive": "inactive",
    "status.paused": "paused",
    "status.disabled": "disabled",
    "status.archived": "archived",
    "status.created": "created",
    "status.updated": "updated",
    "status.deleted": "deleted",
    "status.imported": "imported",
    "condition.good": "good",
    "condition.watch": "watch",
    "condition.needs_service": "needs service",
    "condition.in_service": "in service",
    "condition.retired": "retired",
    "service_due.ok": "planned",
    "service_due.due_soon": "due soon",
    "service_due.overdue": "overdue",
    "global_role.none": "no global role",
    "global_role.reader": "global reader",
    "global_role.operator": "global operator",
    "global_role.admin": "global admin",
    "global_role.platform_admin": "platform admin",
    "tenant_role.reader": "tenant reader",
    "tenant_role.operator": "tenant operator",
    "tenant_role.admin": "tenant admin",
    "access_profile.full": "full",
    "access_profile.basic": "basic"
  },
  de: {
    "app.title": "Verleihverwaltung",
    "app.eyebrow": "Instrumentenverleih",
    "views.dashboard": "Übersicht",
    "views.instruments": "Instrumente",
    "views.members": "Mitglieder",
    "views.rentals": "Ausleihen",
    "views.service_records": "Service",
    "views.history": "Verlauf",
    "views.admin": "Admin Center",
    "labels.tenant": "Mandant",
    "labels.language": "Sprache",
    "labels.revision": "Revision",
    "labels.updated_at": "Aktualisiert {date}",
    "labels.sort": "Sortierung",
    "tenant.title": "2-63 Kleinbuchstaben, Zahlen, Bindestriche oder Unterstriche",
    "tenant.locked": "Der Mandant wird durch die Anmeldung vorgegeben",
    "tenant.invalid": "Mandant muss aus 2-63 Kleinbuchstaben, Zahlen, Bindestrichen oder Unterstrichen bestehen",
    "actions.switch_tenant": "Mandant wechseln",
    "actions.load_demo": "Demo laden",
    "actions.export": "Export",
    "actions.import": "Import",
    "actions.import_hitobito": "Hitobito",
    "actions.export_instruments": "Inventar exportieren",
    "actions.import_instruments": "Inventar importieren",
    "actions.export_tenant_access": "Access-KV exportieren",
    "actions.refresh": "Aktualisieren",
    "actions.cancel": "Abbrechen",
    "actions.close": "Schliessen",
    "actions.save": "Speichern",
    "actions.edit": "Bearbeiten",
    "actions.open": "Öffnen",
    "actions.delete": "Löschen",
    "actions.return": "Rückgabe",
    "actions.view_all": "Alle anzeigen",
    "actions.history": "Verlauf",
    "actions.add_service": "Service erfassen",
    "actions.new_association": "Neue Organisation",
    "actions.new_user": "Neuer Benutzer",
    "actions.new_instruments": "Neues Instrument",
    "actions.new_members": "Neues Mitglied",
    "actions.new_rentals": "Neue Ausleihe",
    "actions.new_service_records": "Neuer Service",
    "actions.yes": "Ja",
    "actions.no": "Nein",
    "dialog.new": "{entity} erstellen",
    "dialog.edit": "{entity} bearbeiten",
    "entities.instrument": "Instrument",
    "entities.member": "Mitglied",
    "entities.rental": "Ausleihe",
    "entities.service_record": "Serviceeintrag",
    "entities.association": "Organisation",
    "entities.user_access": "Benutzerzugriff",
    "entities.associations": "Organisationen",
    "entities.users": "Benutzer",
    "entities.instruments": "Instrumente",
    "entities.members": "Mitglieder",
    "entities.service_records": "Serviceeinträge",
    "entities.history": "Verlauf",
    "fields.name": "Instrument",
    "fields.brand": "Marke",
    "fields.type": "Typ",
    "fields.serial": "Seriennummer",
    "fields.value_chf": "Wert CHF",
    "fields.purchase_year": "Kaufjahr",
    "fields.description": "Beschreibung",
    "fields.display_name": "Name",
    "fields.given_name": "Vorname",
    "fields.family_name": "Nachname",
    "fields.member_ref": "Mitgliederreferenz",
    "fields.contact_hint": "Listenhinweis",
    "fields.is_active": "Aktiv",
    "fields.instrument_id": "Instrument",
    "fields.member_id": "Mitglied",
    "fields.start_date": "Startdatum",
    "fields.due_date": "Fälligkeitsdatum",
    "fields.note": "Notiz",
    "fields.service_date": "Servicedatum",
    "fields.next_service_date": "Nächster Service",
    "fields.condition": "Zustand",
    "fields.job_type": "Art der Arbeit",
    "fields.provider": "Werkstatt",
    "fields.cost_chf": "Kosten CHF",
    "fields.display_name_association": "Organisationsname",
    "fields.short_name": "Kurzname",
    "fields.status": "Status",
    "fields.email": "E-Mail",
    "fields.global_role": "Globale Rolle",
    "fields.access_profile": "Zugriffsprofil",
    "fields.tenant_roles": "Mandantenrollen",
    "fields.member_links": "Mitgliedsverknüpfungen",
    "fields.region": "Region",
    "fields.locale": "Sprache/Region",
    "fields.contact_ref": "Kontaktreferenz",
    "fields.hitobito_group_ref": "Hitobito-Gruppenreferenz",
    "fields.inventory_ref": "Inventarreferenz",
    "table.name": "Name",
    "table.type": "Typ",
    "table.serial": "Seriennummer",
    "table.value": "Wert",
    "table.status": "Status",
    "table.condition": "Zustand",
    "table.last_service": "Letzter Service",
    "table.next_service": "Nächster Service",
    "table.tenant": "Mandant",
    "table.region": "Region",
    "table.updated": "Aktualisiert",
    "table.reference": "Referenz",
    "table.contact": "Listenhinweis",
    "table.instrument": "Instrument",
    "table.member": "Mitglied",
    "table.start": "Start",
    "table.due": "Fällig",
    "table.when": "Zeitpunkt",
    "table.action": "Aktion",
    "table.actor": "Akteur",
    "table.rental": "Ausleihe",
    "table.service": "Service",
    "stats.instruments": "Instrumente",
    "stats.available": "Verfügbar",
    "stats.members": "Mitglieder",
    "stats.active_rentals": "Aktive Ausleihen",
    "stats.overdue": "Überfällig",
    "stats.service_attention": "Servicebedarf",
    "sections.open_rentals": "Offene Ausleihen",
    "sections.attention": "Aufmerksamkeit",
    "sections.instrument_details": "Instrumentdetails",
    "sections.member_details": "Mitgliedsdetails",
    "sections.rental_details": "Ausleihdetails",
    "sections.service_details": "Servicedetails",
    "sections.association_details": "Organisationsdetails",
    "sections.user_details": "Benutzerdetails",
    "sections.history_details": "Verlaufdetails",
    "sections.service_journey": "Serviceverlauf",
    "sections.rental_journey": "Ausleihverlauf",
    "sections.event_journey": "Ereignisverlauf",
    "sections.associations": "Organisationen",
    "sections.users": "Benutzer",
    "empty.no_overdue": "Keine überfälligen Ausleihen",
    "empty.no_attention": "Keine Ausleihen oder Servicepunkte benötigen Aufmerksamkeit",
    "empty.no_service_records": "Keine Serviceeinträge",
    "empty.no_associations": "Keine Organisationen",
    "empty.no_users": "Keine Benutzer",
    "empty.no_tenant_roles": "Keine Mandantenrollen",
    "empty.no_instruments": "Keine Instrumente",
    "empty.no_members": "Keine Mitglieder",
    "empty.no_rentals": "Keine Ausleihen",
    "empty.no_history": "Kein Verlauf",
    "search.placeholder": "{entity} suchen",
    "select.placeholder": "Auswählen...",
    "sort.name": "Name",
    "sort.status": "Status",
    "sort.condition": "Zustand",
    "sort.service_date": "Letzter Service",
    "sort.next_service_date": "Nächster Service",
    "sort.due_date": "Fälligkeit",
    "sort.date": "Datum",
    "sort.tenant": "Mandant",
    "sort.asc": "Aufsteigend",
    "sort.desc": "Absteigend",
    "filter.service_due_soon": "Service bald fällig",
    "filter.service_overdue": "Service überfällig",
    "confirm.delete": "Diesen Eintrag löschen?",
    "confirm.import": "Mandant \"{tenant}\" durch die Einträge aus dieser JSON-Datei ersetzen?",
    "confirm.import_hitobito": "Mitglieder aus dieser Hitobito-JSON-Datei in Mandant \"{tenant}\" importieren?",
    "confirm.import_instruments": "Instrumente aus dieser JSON-Datei in Mandant \"{tenant}\" zusammenführen?",
    "messages.saved": "{entity} gespeichert",
    "messages.deleted": "{entity} gelöscht",
    "messages.returned": "Ausleihe zurückgegeben",
    "messages.demo_loaded": "Demo-Daten geladen",
    "messages.export_downloaded": "Mandantenexport heruntergeladen",
    "messages.import_complete": "Import abgeschlossen: {instruments} Instrumente, {members} Mitglieder",
    "messages.hitobito_import_complete": "Hitobito-Import abgeschlossen: {created} erstellt, {updated} aktualisiert",
    "messages.instrument_export_downloaded": "Instrumenteninventar exportiert",
    "messages.tenant_access_export_downloaded": "Access-KV exportiert",
    "messages.instrument_import_complete": "Instrumentenimport abgeschlossen: {created} erstellt, {updated} aktualisiert",
    "messages.import_blocked_pii": "Import blockiert: Kontaktfelder vor dem Hochladen entfernen ({fields})",
    "messages.import_invalid_json": "Import blockiert: Bitte eine gültige JSON-Datei auswählen",
    "messages.write_blocked_pii": "Kontaktdaten vor dem Speichern entfernen ({fields})",
    "messages.revision_conflict": "Dieser Mandant wurde in einer anderen Sitzung geändert. Die aktuellen Daten sind geladen; bitte prüfen und erneut versuchen.",
    "status.all": "alle",
    "status.available": "verfügbar",
    "status.rented": "ausgeliehen",
    "status.active": "aktiv",
    "status.overdue": "überfällig",
    "status.returned": "zurückgegeben",
    "status.inactive": "inaktiv",
    "status.paused": "pausiert",
    "status.disabled": "deaktiviert",
    "status.archived": "archiviert",
    "status.created": "erstellt",
    "status.updated": "aktualisiert",
    "status.deleted": "gelöscht",
    "status.imported": "importiert",
    "condition.good": "gut",
    "condition.watch": "beobachten",
    "condition.needs_service": "braucht Service",
    "condition.in_service": "im Service",
    "condition.retired": "ausgemustert",
    "service_due.ok": "geplant",
    "service_due.due_soon": "bald fällig",
    "service_due.overdue": "überfällig",
    "global_role.none": "keine globale Rolle",
    "global_role.reader": "global lesen",
    "global_role.operator": "global bedienen",
    "global_role.admin": "global verwalten",
    "global_role.platform_admin": "Plattformverwaltung",
    "tenant_role.reader": "Mandant lesen",
    "tenant_role.operator": "Mandant bedienen",
    "tenant_role.admin": "Mandant verwalten",
    "access_profile.full": "voll",
    "access_profile.basic": "basis"
  }
};

function t(key, values = {}) {
  let text = translations[state.lang]?.[key] || translations.en[key] || key;
  Object.entries(values).forEach(([name, value]) => {
    text = text.replaceAll(`{${name}}`, value);
  });
  return text;
}

function locale() {
  return state.lang === "de" ? "de-CH" : "en-US";
}

tenantInput.value = state.tenant;
tenantLabel.textContent = state.tenant;

const schemas = {
  instruments: [
    ["name", "fields.name", "text", true],
    ["brand", "fields.brand", "text", false],
    ["type", "fields.type", "text", false],
    ["serial", "fields.serial", "text", true],
    ["value_chf", "fields.value_chf", "number", false],
    ["purchase_year", "fields.purchase_year", "number", false],
    ["description", "fields.description", "textarea", false, "full"]
  ],
  members: [
    ["display_name", "fields.display_name", "text", true],
    ["given_name", "fields.given_name", "text", false],
    ["family_name", "fields.family_name", "text", false],
    ["member_ref", "fields.member_ref", "text", false],
    ["contact_hint", "fields.contact_hint", "text", false, "full"],
    ["is_active", "fields.is_active", "checkbox", false]
  ],
  rentals: [
    ["instrument_id", "fields.instrument_id", "rental_instrument", true],
    ["member_id", "fields.member_id", "member", true],
    ["start_date", "fields.start_date", "date", true],
    ["due_date", "fields.due_date", "date", false],
    ["note", "fields.note", "textarea", false, "full"]
  ],
  service_records: [
    ["instrument_id", "fields.instrument_id", "instrument", true],
    ["service_date", "fields.service_date", "date", true],
    ["next_service_date", "fields.next_service_date", "date", false],
    ["condition", "fields.condition", "condition", true],
    ["job_type", "fields.job_type", "text", false],
    ["provider", "fields.provider", "text", false],
    ["cost_chf", "fields.cost_chf", "number", false],
    ["note", "fields.note", "textarea", false, "full"]
  ],
  associations: [
    ["tenant_id", "labels.tenant", "text", true],
    ["display_name", "fields.display_name_association", "text", true],
    ["short_name", "fields.short_name", "text", false],
    ["status", "fields.status", "association_status", true],
    ["region", "fields.region", "text", false],
    ["locale", "fields.locale", "text", false],
    ["contact_ref", "fields.contact_ref", "text", false],
    ["hitobito_group_ref", "fields.hitobito_group_ref", "text", false],
    ["inventory_ref", "fields.inventory_ref", "text", false],
    ["note", "fields.note", "textarea", false, "full"]
  ],
  user_access: [
    ["email", "fields.email", "email", true],
    ["display_name", "fields.display_name", "text", false],
    ["status", "fields.status", "user_status", true],
    ["global_role", "fields.global_role", "global_role", true],
    ["access_profile", "fields.access_profile", "access_profile", true],
    ["tenant_roles", "fields.tenant_roles", "json", false, "full"],
    ["member_links", "fields.member_links", "json", false, "full"]
  ]
};

function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = {"content-type": "application/json", ...(options.headers || {})};
  if (["POST", "PUT", "DELETE"].includes(method) && options.expectRevision !== false) {
    headers["x-rental-expected-revision"] = String(Number(state.meta.revision || 0));
  }
  return fetch(`/api/${state.tenant}${path}`, {...options, method, headers}).then(async (response) => {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (data.meta) applyMeta(data.meta);
      const error = new Error(data.error || `Request failed (${response.status})`);
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  });
}

async function apiContext() {
  const response = await fetch("/api/context", {headers: {"content-type": "application/json"}});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status})`);
  }
  return data;
}

function adminApi(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = {"content-type": "application/json", ...(options.headers || {})};
  return fetch(`/api/admin${path}`, {...options, method, headers}).then(async (response) => {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || `Request failed (${response.status})`);
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  });
}

function applyContext(context) {
  state.context = context;
  if (context.tenant_locked) {
    state.tenant = context.tenant_id;
    tenantInput.value = state.tenant;
    tenantInput.disabled = true;
    saveTenant.disabled = true;
    saveTenant.title = t("tenant.locked");
  } else {
    tenantInput.disabled = false;
    saveTenant.disabled = false;
    state.tenant = localStorage.getItem("rentalTenant") || state.tenant || context.tenant_id;
    tenantInput.value = state.tenant;
  }
  tenantLabel.textContent = state.tenant;
  applyMeta(context.meta);
}

function applyMeta(meta = state.meta) {
  if (meta && typeof meta === "object") {
    state.meta = {...state.meta, ...meta};
  }
  const revision = Number(state.meta.revision || 0);
  tenantRevision.textContent = Number.isFinite(revision) ? String(revision) : "0";
  if (!state.meta.updated_at) {
    tenantUpdatedAt.textContent = "";
    return;
  }
  const updatedAt = new Date(state.meta.updated_at);
  tenantUpdatedAt.textContent = Number.isNaN(updatedAt.getTime())
    ? ""
    : t("labels.updated_at", {date: updatedAt.toLocaleString(locale())});
}

function applyLanguage() {
  document.documentElement.lang = state.lang;
  document.title = t("app.title");
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((element) => {
    element.title = t(element.dataset.i18nTitle);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
    element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
  });
  languageButtons.forEach((button) => {
    const active = button.dataset.lang === state.lang;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  if (state.context?.tenant_locked) {
    saveTenant.title = t("tenant.locked");
  }
  applyMeta();
}

function downloadJson(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: "application/json"});
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

async function readJsonFile(file) {
  try {
    return JSON.parse(await file.text());
  } catch {
    throw new Error(t("messages.import_invalid_json"));
  }
}

function blockedPiiPaths(value, path = "payload", matches = [], allowedFields = new Set()) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => blockedPiiPaths(item, `${path}[${index}]`, matches, allowedFields));
    return matches;
  }
  if (!value || typeof value !== "object") return matches;
  Object.entries(value).forEach(([key, child]) => {
    const normalizedKey = key.toLowerCase();
    const childPath = `${path}.${key}`;
    if (blockedImportPiiFields.has(normalizedKey) && !allowedFields.has(normalizedKey)) matches.push(childPath);
    if (typeof child === "string") {
      if (emailLikeImportValueFields.has(normalizedKey) && importEmailPattern.test(child)) matches.push(childPath);
      if (phoneLikeImportValueFields.has(normalizedKey) && importPhonePattern.test(child)) matches.push(childPath);
    }
    blockedPiiPaths(child, childPath, matches, allowedFields);
  });
  return matches;
}

function assertLowPiiImport(payload) {
  const blocked = blockedPiiPaths(payload);
  if (!blocked.length) return;
  const visible = blocked.slice(0, 3).join(", ");
  throw new Error(t("messages.import_blocked_pii", {fields: visible}));
}

function assertLowPiiWrite(payload, entity) {
  const allowedFields = entity === "user_access" ? new Set(["email"]) : new Set();
  const blocked = blockedPiiPaths(payload, "payload", [], allowedFields);
  if (!blocked.length) return;
  const visible = blocked.slice(0, 3).join(", ");
  throw new Error(t("messages.write_blocked_pii", {fields: visible}));
}

function showMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("is-error", isError);
  message.hidden = false;
  window.clearTimeout(showMessage.timer);
  showMessage.timer = window.setTimeout(() => {
    message.hidden = true;
  }, 4200);
}

async function handleMutationError(error) {
  if (error.status === 409) {
    await loadData().catch(() => {});
    showMessage(t("messages.revision_conflict"), true);
    return;
  }
  showMessage(error.message, true);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatDate(value) {
  return value ? new Date(`${value}T00:00:00`).toLocaleDateString(locale()) : "";
}

function dateOrdinal(value) {
  const [year, month, day] = String(value || "").split("-").map(Number);
  if (!year || !month || !day) return null;
  return Date.UTC(year, month - 1, day) / 86400000;
}

function todayOrdinal() {
  const today = new Date();
  return Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) / 86400000;
}

function serviceDueStatus(nextServiceDate) {
  if (!nextServiceDate) return "ok";
  const due = dateOrdinal(nextServiceDate);
  if (due === null) return "ok";
  const daysUntilDue = due - todayOrdinal();
  if (daysUntilDue < 0) return "overdue";
  return daysUntilDue <= 30 ? "due_soon" : "ok";
}

function statusPill(status) {
  return `<span class="pill ${escapeHtml(status)}">${escapeHtml(t(`status.${status}`))}</span>`;
}

function conditionPill(condition) {
  return `<span class="pill condition-${escapeHtml(condition)}">${escapeHtml(t(`condition.${condition}`))}</span>`;
}

function serviceDuePill(status) {
  return `<span class="pill service-${escapeHtml(status)}">${escapeHtml(t(`service_due.${status || "ok"}`))}</span>`;
}

function globalRolePill(role) {
  return `<span class="pill role-${escapeHtml(role)}">${escapeHtml(t(`global_role.${role}`))}</span>`;
}

function tenantRolePill(role) {
  return `<span class="pill role-${escapeHtml(role)}">${escapeHtml(t(`tenant_role.${role}`))}</span>`;
}

function accessProfilePill(profile) {
  return `<span class="pill profile-${escapeHtml(profile)}">${escapeHtml(t(`access_profile.${profile}`))}</span>`;
}

function capabilities() {
  return state.context?.capabilities || {read: true, write: true, admin: true, platform_admin: true};
}

function defaultSortFor(viewName) {
  if (viewName === "service_records") return "service_date";
  if (viewName === "rentals") return "due_date";
  if (viewName === "history") return "date";
  if (viewName === "admin" || viewName === "associations") return "name";
  return "name";
}

function defaultSortDirectionFor(viewName) {
  return viewName === "history" || viewName === "service_records" ? "desc" : "asc";
}

function switchView(viewName) {
  state.view = viewName;
  state.search = "";
  state.status = "all";
  state.sort = defaultSortFor(viewName);
  state.sortDirection = defaultSortDirectionFor(viewName);
  state.detail = null;
}

async function loadData() {
  const associationsPromise = capabilities().platform_admin ? adminApi("/associations").catch(() => ({data: []})) : Promise.resolve({data: []});
  const usersPromise = capabilities().platform_admin ? adminApi("/users").catch(() => ({data: []})) : Promise.resolve({data: []});
  const [summary, instruments, members, rentals, serviceRecords, history, associations, users] = await Promise.all([
    api("/summary"),
    api("/instruments"),
    api("/members"),
    api("/rentals"),
    api("/service_records"),
    api("/history"),
    associationsPromise,
    usersPromise
  ]);
  state.summary = summary;
  applyMeta(summary.meta);
  state.records = {
    instruments: instruments.data || [],
    members: members.data || [],
    rentals: rentals.data || [],
    service_records: serviceRecords.data || [],
    history: history.data || []
  };
  state.associations = associations.data || [];
  state.users = users.data || [];
  reconcileDetailSelection();
  render();
}

function reconcileDetailSelection() {
  if (!state.detail) return;
  if (state.detail.entity === "associations") {
    if (!state.associations.some((item) => item.tenant_id === state.detail.id)) state.detail = null;
    return;
  }
  if (state.detail.entity === "user_access") {
    if (!state.users.some((item) => item.id === state.detail.id)) state.detail = null;
    return;
  }
  const records = state.records[state.detail.entity];
  if (!records || !records.some((item) => item.id === state.detail.id)) state.detail = null;
}

function render() {
  applyLanguage();
  const caps = capabilities();
  if (adminNavItem) adminNavItem.hidden = !caps.platform_admin;
  if (state.view === "admin" && !caps.platform_admin) {
    switchView("dashboard");
  }
  viewTitle.textContent = t(`views.${state.view}`);
  tenantLabel.textContent = state.tenant;
  primaryAction.hidden = state.view === "history" || (state.view === "admin" && !caps.platform_admin);
  primaryAction.textContent = state.view === "admin" ? t("actions.new_association") : state.view === "instruments" ? t("actions.new_instruments") : state.view === "members" ? t("actions.new_members") : state.view === "service_records" ? t("actions.new_service_records") : t("actions.new_rentals");
  primaryAction.disabled = state.view === "admin" ? !caps.platform_admin : !caps.write;
  seedButton.disabled = !caps.admin;
  exportButton.disabled = !caps.admin;
  importButton.disabled = !caps.admin;
  hitobitoImportButton.disabled = !caps.admin;

  document.querySelectorAll(".nav-item").forEach((button) => {
    if (button.dataset.view === "admin") {
      button.hidden = !caps.platform_admin;
    }
    button.classList.toggle("is-active", button.dataset.view === state.view);
  });

  if (state.view === "dashboard") renderDashboard();
  if (state.view === "instruments") renderCollection("instruments");
  if (state.view === "members") renderCollection("members");
  if (state.view === "rentals") renderCollection("rentals");
  if (state.view === "service_records") renderCollection("service_records");
  if (state.view === "history") renderHistory();
  if (state.view === "admin") renderAdmin();
}

function renderDashboard() {
  const rentals = state.records.rentals.filter((rental) => rental.status !== "returned").slice(0, 6);
  const overdue = state.records.rentals.filter((rental) => rental.status === "overdue");
  const serviceAttention = state.records.instruments
    .filter((item) => ["watch", "needs_service", "in_service"].includes(item.service_condition) || ["due_soon", "overdue"].includes(item.service_due_status))
    .sort((a, b) => String(a.next_service_date || "").localeCompare(String(b.next_service_date || ""), locale(), {numeric: true, sensitivity: "base"}))
    .slice(0, 6);
  view.innerHTML = `
    ${renderStats()}
    <div class="content-grid">
      <section class="panel">
        <div class="panel-head">
          <h2>${t("sections.open_rentals")}</h2>
          <button class="ghost-button" data-jump="rentals">${t("actions.view_all")}</button>
        </div>
        ${renderRentalTable(rentals, true)}
      </section>
      <section class="panel">
        <div class="panel-head">
          <h2>${t("sections.attention")}</h2>
          <button class="ghost-button" data-jump="instruments">${t("actions.view_all")}</button>
        </div>
        ${overdue.length || serviceAttention.length ? `
          <div class="attention-stack">
            ${overdue.length ? renderRentalTable(overdue, true) : ""}
            ${serviceAttention.length ? renderServiceAttentionList(serviceAttention) : ""}
          </div>
        ` : `<div class="empty">${t("empty.no_attention")}</div>`}
      </section>
    </div>
  `;
}

function renderServiceAttentionList(items) {
  return `<div class="attention-list">${items.map((item) => `
    <article class="attention-item clickable-row" data-open-dashboard-instrument="${item.id}" tabindex="0">
      <div>
        <strong>${escapeHtml(item.name)}</strong>
        <div class="muted">${[item.type, item.serial].filter(Boolean).map(escapeHtml).join(" / ")}</div>
      </div>
      <div class="attention-badges">
        ${conditionPill(item.service_condition || "good")}
        ${item.next_service_date ? serviceDuePill(item.service_due_status) : ""}
      </div>
    </article>
  `).join("")}</div>`;
}

function renderStats() {
  const stats = [
    [t("stats.instruments"), state.summary.instruments || 0],
    [t("stats.available"), state.summary.available_instruments || 0],
    [t("stats.members"), state.summary.members || 0],
    [t("stats.active_rentals"), state.summary.active_rentals || 0],
    [t("stats.overdue"), state.summary.overdue_rentals || 0],
    [t("stats.service_attention"), state.summary.service_attention || 0]
  ];
  return `<section class="stats-grid">${stats.map(([label, value]) => `
    <div class="stat"><span>${label}</span><strong>${value}</strong></div>
  `).join("")}</section>`;
}

function renderAdmin() {
  if (!capabilities().platform_admin) {
    view.innerHTML = `<div class="empty">${t("tenant.locked")}</div>`;
    return;
  }
  const associationItems = filterAssociationItems(state.associations);
  const userItems = filterUserItems(state.users);
  const detail = state.detail?.entity === "associations"
    ? renderAssociationDetail(state.detail.id)
    : state.detail?.entity === "user_access"
      ? renderUserDetail(state.detail.id)
      : "";
  view.innerHTML = `${renderToolbar("associations")}<div class="${detail ? "split-view" : ""}">
    <div class="admin-stack">
      <section class="panel">
        <div class="panel-head">
          <h2>${t("sections.associations")}</h2>
        </div>
        ${renderAssociationTable(associationItems)}
      </section>
      <section class="panel">
        <div class="panel-head">
          <h2>${t("sections.users")}</h2>
          <div class="panel-actions">
            <button class="ghost-button" data-export-tenant-access>${t("actions.export_tenant_access")}</button>
            <button class="primary-button" data-new-user>${t("actions.new_user")}</button>
          </div>
        </div>
        ${renderUserTable(userItems)}
      </section>
    </div>
    ${detail}
  </div>`;
}

function filterAssociationItems(items) {
  let filtered = [...items];
  if (state.search) {
    const search = state.search.toLowerCase();
    filtered = filtered.filter((item) => JSON.stringify(item).toLowerCase().includes(search));
  }
  return sortItems(filtered);
}

function filterUserItems(items) {
  let filtered = [...items];
  if (state.search) {
    const search = state.search.toLowerCase();
    filtered = filtered.filter((item) => JSON.stringify(item).toLowerCase().includes(search));
  }
  return sortItems(filtered);
}

function renderAssociationTable(items) {
  if (!items.length) return `<div class="empty">${t("empty.no_associations")}</div>`;
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>${t("table.tenant")}</th><th>${t("table.name")}</th><th>${t("table.status")}</th><th>${t("table.region")}</th><th>Hitobito</th><th>${t("table.updated")}</th><th></th></tr></thead>
        <tbody>${items.map((item) => `
          <tr class="clickable-row ${state.detail?.id === item.tenant_id ? "is-selected" : ""}" data-open="associations" data-id="${item.tenant_id}" tabindex="0">
            <td><strong>${escapeHtml(item.tenant_id)}</strong><div class="muted">${escapeHtml(item.short_name || "")}</div></td>
            <td>${escapeHtml(item.display_name)}</td>
            <td>${statusPill(item.status || "active")}</td>
            <td>${escapeHtml(item.region || "")}</td>
            <td>${escapeHtml(item.hitobito_group_ref || "")}</td>
            <td>${item.meta?.updated_at ? new Date(item.meta.updated_at).toLocaleString(locale()) : ""}</td>
            <td><div class="row-actions">
              <button class="ghost-button" data-edit-association="${item.tenant_id}">${t("actions.edit")}</button>
              ${state.context?.tenant_locked ? "" : `<button class="primary-button" data-open-association="${item.tenant_id}">${t("actions.open")}</button>`}
            </div></td>
          </tr>
        `).join("")}</tbody>
      </table>
    </div>
  `;
}

function renderUserTable(items) {
  if (!items.length) return `<div class="empty">${t("empty.no_users")}</div>`;
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>${t("fields.email")}</th><th>${t("fields.global_role")}</th><th>${t("fields.access_profile")}</th><th>${t("fields.tenant_roles")}</th><th>${t("table.status")}</th><th></th></tr></thead>
        <tbody>${items.map((item) => `
          <tr class="clickable-row ${state.detail?.entity === "user_access" && state.detail?.id === item.id ? "is-selected" : ""}" data-open="user_access" data-id="${item.id}" tabindex="0">
            <td><strong>${escapeHtml(item.email)}</strong><div class="muted">${escapeHtml(item.display_name || item.id)}</div></td>
            <td>${globalRolePill(item.global_role || "none")}</td>
            <td>${accessProfilePill(item.access_profile || "full")}</td>
            <td>${escapeHtml((item.tenant_roles || []).map((role) => `${role.tenant_id}:${role.role}`).join(", "))}</td>
            <td>${statusPill(item.status || "active")}</td>
            <td><div class="row-actions">
              <button class="ghost-button" data-edit-user="${item.id}">${t("actions.edit")}</button>
              <button class="danger-button" data-delete-user="${item.id}">${t("actions.delete")}</button>
            </div></td>
          </tr>
        `).join("")}</tbody>
      </table>
    </div>
  `;
}

function renderAssociationDetail(tenantId) {
  const item = state.associations.find((association) => association.tenant_id === tenantId);
  if (!item) return "";
  const canOpen = !state.context?.tenant_locked;
  return `
    <aside class="detail-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">${t("sections.association_details")}</p>
          <h2>${escapeHtml(item.display_name)}</h2>
        </div>
        ${detailCloseButton()}
      </div>
      <div class="detail-facts">
        ${statusPill(item.status || "active")}
        <span>${escapeHtml(item.tenant_id)}</span>
        <span>${escapeHtml(item.locale || "")}</span>
        <span>${escapeHtml(item.region || "")}</span>
      </div>
      <div class="journey">
        <article class="journey-stop ${escapeHtml(item.status || "active")}">
          <div class="journey-marker"></div>
          <div>
            <div class="journey-head">
              <strong>${t("table.status")}</strong>
              ${statusPill(item.status || "active")}
            </div>
            <div>${escapeHtml(item.short_name || item.display_name)}</div>
          </div>
        </article>
        <article class="journey-stop active">
          <div class="journey-marker"></div>
          <div>
            <div class="journey-head">
              <strong>${t("table.updated")}</strong>
              <span>${item.meta?.revision ? `#${escapeHtml(item.meta.revision)}` : ""}</span>
            </div>
            <div>${item.meta?.updated_at ? new Date(item.meta.updated_at).toLocaleString(locale()) : ""}</div>
          </div>
        </article>
      </div>
      <dl class="detail-list">
        <div><dt>${t("fields.contact_ref")}</dt><dd>${escapeHtml(item.contact_ref || "")}</dd></div>
        <div><dt>${t("fields.hitobito_group_ref")}</dt><dd>${escapeHtml(item.hitobito_group_ref || "")}</dd></div>
        <div><dt>${t("fields.inventory_ref")}</dt><dd>${escapeHtml(item.inventory_ref || "")}</dd></div>
      </dl>
      ${item.note ? `<p class="muted">${escapeHtml(item.note)}</p>` : ""}
      <div class="row-actions">
        <button class="ghost-button" data-edit-association="${item.tenant_id}">${t("actions.edit")}</button>
        ${canOpen ? `<button class="primary-button" data-open-association="${item.tenant_id}">${t("actions.open")}</button>` : ""}
      </div>
    </aside>
  `;
}

function renderUserDetail(userId) {
  const item = state.users.find((user) => user.id === userId);
  if (!item) return "";
  const tenantRoles = item.tenant_roles || [];
  const memberLinks = item.member_links || [];
  return `
    <aside class="detail-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">${t("sections.user_details")}</p>
          <h2>${escapeHtml(item.display_name || item.email)}</h2>
        </div>
        ${detailCloseButton()}
      </div>
      <div class="detail-facts">
        ${statusPill(item.status || "active")}
        ${globalRolePill(item.global_role || "none")}
        ${accessProfilePill(item.access_profile || "full")}
      </div>
      <div class="journey">
        <article class="journey-stop active">
          <div class="journey-marker"></div>
          <div>
            <div class="journey-head">
              <strong>${t("fields.email")}</strong>
              <span>${escapeHtml(item.id)}</span>
            </div>
            <div>${escapeHtml(item.email)}</div>
          </div>
        </article>
        ${tenantRoles.length ? tenantRoles.map((role) => `
          <article class="journey-stop ${escapeHtml(role.role)}">
            <div class="journey-marker"></div>
            <div>
              <div class="journey-head">
                <strong>${escapeHtml(role.tenant_id)}</strong>
                ${tenantRolePill(role.role)}
              </div>
              <div>${memberLinks.filter((link) => link.tenant_id === role.tenant_id).map((link) => escapeHtml(link.member_id)).join(", ") || t("access_profile.full")}</div>
            </div>
          </article>
        `).join("") : `
          <article class="journey-stop paused">
            <div class="journey-marker"></div>
            <div>
              <div class="journey-head"><strong>${t("fields.tenant_roles")}</strong></div>
              <div class="muted">${t("empty.no_tenant_roles")}</div>
            </div>
          </article>
        `}
      </div>
      <dl class="detail-list">
        <div><dt>${t("fields.email")}</dt><dd>${escapeHtml(item.email)}</dd></div>
        <div><dt>${t("fields.global_role")}</dt><dd>${escapeHtml(t(`global_role.${item.global_role || "none"}`))}</dd></div>
        <div><dt>${t("fields.access_profile")}</dt><dd>${escapeHtml(t(`access_profile.${item.access_profile || "full"}`))}</dd></div>
        <div><dt>${t("fields.member_links")}</dt><dd>${escapeHtml(memberLinks.map((link) => `${link.tenant_id}:${link.member_id}`).join(", "))}</dd></div>
      </dl>
      <div class="row-actions">
        <button class="ghost-button" data-edit-user="${item.id}">${t("actions.edit")}</button>
        <button class="danger-button" data-delete-user="${item.id}">${t("actions.delete")}</button>
      </div>
    </aside>
  `;
}

function renderToolbar(entity) {
  const caps = capabilities();
  const statusOptions = entity === "instruments"
    ? ["all", "available", "rented", "overdue", "watch", "needs_service", "in_service", "service_due_soon", "service_overdue"]
    : entity === "rentals"
      ? ["all", "active", "overdue", "returned"]
      : entity === "service_records"
        ? ["all", "good", "watch", "needs_service", "in_service", "retired", "service_due_soon", "service_overdue"]
      : entity === "members"
        ? ["all", "active", "inactive"]
      : [];
  const sortOptions = entity === "instruments"
    ? ["name", "status", "condition", "service_date", "next_service_date"]
    : entity === "rentals"
      ? ["due_date", "status", "name"]
      : entity === "service_records"
        ? ["service_date", "next_service_date", "condition", "name"]
      : entity === "history"
        ? ["date", "name"]
        : entity === "associations"
          ? ["name", "tenant", "status"]
          : ["name"];
  return `
    <div class="toolbar">
      <input data-search placeholder="${escapeHtml(t("search.placeholder", {entity: t(`entities.${entity}`)}))}" value="${escapeHtml(state.search)}">
      ${statusOptions.length ? `<div class="segmented">
        ${statusOptions.map((status) => `
          <button data-status="${status}" class="${state.status === status ? "is-active" : ""}">${filterLabel(status)}</button>
        `).join("")}
      </div>` : ""}
      <label class="sort-control">
        <span>${t("labels.sort")}</span>
        <select data-sort>
          ${sortOptions.map((option) => `<option value="${option}" ${state.sort === option ? "selected" : ""}>${t(`sort.${option}`)}</option>`).join("")}
        </select>
      </label>
      <button class="icon-button" data-sort-direction aria-label="${escapeHtml(t(`sort.${state.sortDirection}`))}" title="${escapeHtml(t(`sort.${state.sortDirection}`))}">
        <span aria-hidden="true">${state.sortDirection === "asc" ? "↑" : "↓"}</span>
      </button>
      ${entity === "instruments" && caps.admin ? `<div class="toolbar-actions">
        <button class="ghost-button" data-export-instruments>${t("actions.export_instruments")}</button>
        <button class="ghost-button" data-import-instruments>${t("actions.import_instruments")}</button>
      </div>` : ""}
    </div>
  `;
}

function filterItems(items) {
  let filtered = [...items];
  if (state.search) {
    const search = state.search.toLowerCase();
    filtered = filtered.filter((item) => JSON.stringify(item).toLowerCase().includes(search));
  }
  if (state.status !== "all") {
    filtered = filtered.filter((item) => itemMatchesFilter(item, state.status));
  }
  return sortItems(filtered);
}

function serviceInstrument(record) {
  return state.records.instruments.find((item) => item.id === record.instrument_id);
}

function serviceInstrumentName(record) {
  return record.instrument_name || serviceInstrument(record)?.name || record.instrument_id || "";
}

function filterLabel(filter) {
  if (filter === "service_due_soon" || filter === "service_overdue") return t(`filter.${filter}`);
  if (["good", "watch", "needs_service", "in_service", "retired"].includes(filter)) return t(`condition.${filter}`);
  return t(`status.${filter}`);
}

function itemMatchesFilter(item, filter) {
  if (filter === "active" && "is_active" in item) return item.is_active !== false;
  if (filter === "inactive" && "is_active" in item) return item.is_active === false;
  const dueStatus = item.service_due_status || serviceDueStatus(item.next_service_date);
  if (filter === "service_due_soon") return dueStatus === "due_soon";
  if (filter === "service_overdue") return dueStatus === "overdue";
  if (["good", "watch", "needs_service", "in_service", "retired"].includes(filter)) {
    return (item.service_condition || item.condition) === filter;
  }
  return item.status === filter;
}

function sortItems(items) {
  const valueFor = (item) => {
    if (state.sort === "condition") return item.service_condition || item.condition || "";
    if (state.sort === "service_date") return item.last_service_date || item.service_date || "";
    if (state.sort === "next_service_date") return item.next_service_date || "";
    if (state.sort === "due_date") return item.due_date || "";
    if (state.sort === "date") return item.created_at || item.service_date || "";
    if (state.sort === "status") return item.status || "";
    if (state.sort === "tenant") return item.tenant_id || "";
    return item.name || item.display_name || item.email || item.instrument_name || serviceInstrumentName(item) || item.member_name || "";
  };
  const direction = state.sortDirection === "desc" ? -1 : 1;
  return [...items].sort((a, b) => direction * String(valueFor(a)).localeCompare(String(valueFor(b)), locale(), {numeric: true, sensitivity: "base"}));
}

function renderCollection(entity) {
  const items = filterItems(state.records[entity]);
  const table = entity === "instruments"
    ? renderInstrumentTable(items)
    : entity === "members"
      ? renderMemberTable(items)
      : entity === "service_records"
        ? renderServiceTable(items)
        : renderRentalTable(items);
  const detail = state.detail?.entity === entity ? renderDetail(entity, state.detail.id) : "";
  view.innerHTML = `${renderToolbar(entity)}<div class="${detail ? "split-view" : ""}"><div>${table}</div>${detail}</div>`;
}

function renderDetail(entity, id) {
  if (entity === "instruments") return renderInstrumentDetail(state.records.instruments.find((item) => item.id === id));
  if (entity === "members") return renderMemberDetail(state.records.members.find((item) => item.id === id));
  if (entity === "rentals") return renderRentalDetail(state.records.rentals.find((item) => item.id === id));
  if (entity === "service_records") return renderServiceDetail(state.records.service_records.find((item) => item.id === id));
  return "";
}

function detailCloseButton() {
  return `<button class="icon-button detail-close" data-close-detail aria-label="${escapeHtml(t("actions.close"))}" title="${escapeHtml(t("actions.close"))}"><span aria-hidden="true">&times;</span></button>`;
}

function renderInstrumentTable(items) {
  if (!items.length) return `<div class="empty">${t("empty.no_instruments")}</div>`;
  const caps = capabilities();
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>${t("table.name")}</th><th>${t("table.type")}</th><th>${t("table.serial")}</th><th>${t("table.condition")}</th><th>${t("table.last_service")}</th><th>${t("table.next_service")}</th><th>${t("table.status")}</th><th></th></tr></thead>
        <tbody>${items.map((item) => `
          <tr class="clickable-row ${state.detail?.id === item.id ? "is-selected" : ""}" data-open="instruments" data-id="${item.id}" tabindex="0">
            <td><strong>${escapeHtml(item.name)}</strong><div class="muted">${escapeHtml(item.brand)}</div></td>
            <td>${escapeHtml(item.type)}</td>
            <td>${escapeHtml(item.serial)}</td>
            <td>${conditionPill(item.service_condition || "good")}</td>
            <td>${formatDate(item.last_service_date)}</td>
            <td>${item.next_service_date ? `${formatDate(item.next_service_date)} ${serviceDuePill(item.service_due_status)}` : ""}</td>
            <td>${statusPill(item.status)}</td>
            <td><div class="row-actions">
              ${caps.write ? `<button class="ghost-button" data-edit="instruments" data-id="${item.id}">${t("actions.edit")}</button>` : ""}
              ${caps.admin ? `<button class="danger-button" data-delete="instruments" data-id="${item.id}">${t("actions.delete")}</button>` : ""}
            </div></td>
          </tr>
        `).join("")}</tbody>
      </table>
    </div>
  `;
}

function renderInstrumentDetail(item) {
  if (!item) return "";
  const caps = capabilities();
  const services = state.records.service_records
    .filter((record) => record.instrument_id === item.id)
    .sort((a, b) => String(b.service_date || "").localeCompare(String(a.service_date || "")));
  const rentals = state.records.rentals
    .filter((record) => record.instrument_id === item.id)
    .sort((a, b) => String(b.start_date || "").localeCompare(String(a.start_date || "")));
  return `
    <aside class="detail-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">${t("sections.instrument_details")}</p>
          <h2>${escapeHtml(item.name)}</h2>
        </div>
        <div class="panel-actions">
          ${caps.write ? `<button class="primary-button" data-service-add="${item.id}">${t("actions.add_service")}</button>` : ""}
          ${detailCloseButton()}
        </div>
      </div>
      <div class="detail-facts">
        <span>${conditionPill(item.service_condition || "good")}</span>
        ${item.next_service_date ? `<span>${serviceDuePill(item.service_due_status)}</span>` : ""}
        <span>${statusPill(item.status)}</span>
        <span>${escapeHtml(item.serial)}</span>
        <span>${item.value_chf ? `CHF ${Number(item.value_chf).toFixed(0)}` : ""}</span>
      </div>
      ${item.description ? `<p class="muted">${escapeHtml(item.description)}</p>` : ""}
      <h3>${t("sections.service_journey")}</h3>
      ${services.length ? renderServiceJourney(services, caps) : `<div class="empty compact">${t("empty.no_service_records")}</div>`}
      <h3>${t("sections.rental_journey")}</h3>
      ${rentals.length ? renderRentalJourney(rentals) : `<div class="empty compact">${t("empty.no_rentals")}</div>`}
    </aside>
  `;
}

function renderServiceJourney(items, caps, selectedId = null) {
  return `<div class="journey">${items.map((item) => `
    <article class="journey-stop condition-${escapeHtml(item.condition)} ${item.id === selectedId ? "is-selected" : ""}">
      <div class="journey-marker"></div>
      <div>
        <div class="journey-head">
          <strong>${formatDate(item.service_date)}</strong>
          ${conditionPill(item.condition)}
        </div>
        <div>${escapeHtml(item.job_type || t("entities.service_record"))}</div>
        <div class="muted">${[item.provider, item.cost_chf ? `CHF ${Number(item.cost_chf).toFixed(0)}` : ""].filter(Boolean).map(escapeHtml).join(" / ")}</div>
        ${item.next_service_date ? `<div class="muted">${escapeHtml(t("fields.next_service_date"))}: ${formatDate(item.next_service_date)} ${serviceDuePill(serviceDueStatus(item.next_service_date))}</div>` : ""}
        ${item.note ? `<p>${escapeHtml(item.note)}</p>` : ""}
        <div class="row-actions">
          ${caps.write ? `<button class="ghost-button" data-edit="service_records" data-id="${item.id}">${t("actions.edit")}</button>` : ""}
          ${caps.admin ? `<button class="danger-button" data-delete="service_records" data-id="${item.id}">${t("actions.delete")}</button>` : ""}
        </div>
      </div>
    </article>
  `).join("")}</div>`;
}

function renderServiceTable(items) {
  if (!items.length) return `<div class="empty">${t("empty.no_service_records")}</div>`;
  const caps = capabilities();
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>${t("table.instrument")}</th><th>${t("fields.service_date")}</th><th>${t("table.condition")}</th><th>${t("table.next_service")}</th><th>${t("fields.provider")}</th><th></th></tr></thead>
        <tbody>${items.map((item) => {
          const dueStatus = serviceDueStatus(item.next_service_date);
          return `
            <tr class="clickable-row ${state.detail?.id === item.id ? "is-selected" : ""}" data-open="service_records" data-id="${item.id}" tabindex="0">
              <td><strong>${escapeHtml(serviceInstrumentName(item))}</strong><div class="muted">${escapeHtml(item.job_type || "")}</div></td>
              <td>${formatDate(item.service_date)}</td>
              <td>${conditionPill(item.condition)}</td>
              <td>${item.next_service_date ? `${formatDate(item.next_service_date)} ${serviceDuePill(dueStatus)}` : ""}</td>
              <td>${escapeHtml(item.provider || "")}</td>
              <td><div class="row-actions">
                ${caps.write ? `<button class="ghost-button" data-edit="service_records" data-id="${item.id}">${t("actions.edit")}</button>` : ""}
                ${caps.admin ? `<button class="danger-button" data-delete="service_records" data-id="${item.id}">${t("actions.delete")}</button>` : ""}
              </div></td>
            </tr>
          `;
        }).join("")}</tbody>
      </table>
    </div>
  `;
}

function renderServiceDetail(item) {
  if (!item) return "";
  const caps = capabilities();
  const instrument = serviceInstrument(item);
  const services = state.records.service_records
    .filter((record) => record.instrument_id === item.instrument_id)
    .sort((a, b) => String(b.service_date || "").localeCompare(String(a.service_date || "")));
  return `
    <aside class="detail-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">${t("sections.service_details")}</p>
          <h2>${escapeHtml(item.job_type || serviceInstrumentName(item))}</h2>
        </div>
        ${detailCloseButton()}
      </div>
      <div class="detail-facts">
        <span>${conditionPill(item.condition)}</span>
        <span>${formatDate(item.service_date)}</span>
        ${item.next_service_date ? `<span>${serviceDuePill(serviceDueStatus(item.next_service_date))}</span>` : ""}
        <span>${escapeHtml(serviceInstrumentName(item))}</span>
        ${instrument?.serial ? `<span>${escapeHtml(instrument.serial)}</span>` : ""}
        ${item.cost_chf ? `<span>CHF ${Number(item.cost_chf).toFixed(0)}</span>` : ""}
      </div>
      <dl class="detail-list">
        <div><dt>${t("fields.provider")}</dt><dd>${escapeHtml(item.provider || "")}</dd></div>
        <div><dt>${t("fields.next_service_date")}</dt><dd>${formatDate(item.next_service_date)}</dd></div>
        <div><dt>${t("fields.instrument_id")}</dt><dd>${escapeHtml(item.instrument_id || "")}</dd></div>
      </dl>
      ${item.note ? `<p class="muted">${escapeHtml(item.note)}</p>` : ""}
      <h3>${t("sections.service_journey")}</h3>
      ${services.length ? renderServiceJourney(services, caps, item.id) : `<div class="empty compact">${t("empty.no_service_records")}</div>`}
    </aside>
  `;
}

function renderRentalJourney(items) {
  return `<div class="journey">${items.map((item) => `
    <article class="journey-stop ${escapeHtml(item.status)}">
      <div class="journey-marker"></div>
      <div>
        <div class="journey-head">
          <strong>${formatDate(item.start_date)}</strong>
          ${statusPill(item.status)}
        </div>
        <div>${escapeHtml(item.member_name)}</div>
        <div class="muted">${[item.due_date ? `${t("table.due")}: ${formatDate(item.due_date)}` : "", item.return_date ? `${t("actions.return")}: ${formatDate(item.return_date)}` : ""].filter(Boolean).map(escapeHtml).join(" / ")}</div>
        ${item.note ? `<p>${escapeHtml(item.note)}</p>` : ""}
      </div>
    </article>
  `).join("")}</div>`;
}

function renderMemberTable(items) {
  if (!items.length) return `<div class="empty">${t("empty.no_members")}</div>`;
  const caps = capabilities();
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>${t("table.name")}</th><th>${t("table.reference")}</th><th>${t("table.contact")}</th><th>${t("table.status")}</th><th></th></tr></thead>
        <tbody>${items.map((item) => `
          <tr class="clickable-row ${state.detail?.id === item.id ? "is-selected" : ""}" data-open="members" data-id="${item.id}" tabindex="0">
            <td><strong>${escapeHtml(item.display_name)}</strong></td>
            <td>${escapeHtml(item.member_ref)}</td>
            <td>${escapeHtml(item.contact_hint)}</td>
            <td>${item.is_active ? statusPill("active") : statusPill("inactive")}</td>
            <td><div class="row-actions">
              ${caps.write ? `<button class="ghost-button" data-edit="members" data-id="${item.id}">${t("actions.edit")}</button>` : ""}
              ${caps.admin ? `<button class="danger-button" data-delete="members" data-id="${item.id}">${t("actions.delete")}</button>` : ""}
            </div></td>
          </tr>
        `).join("")}</tbody>
      </table>
    </div>
  `;
}

function renderMemberDetail(item) {
  if (!item) return "";
  const rentals = state.records.rentals
    .filter((record) => record.member_id === item.id)
    .sort((a, b) => String(b.start_date || "").localeCompare(String(a.start_date || "")));
  return `
    <aside class="detail-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">${t("sections.member_details")}</p>
          <h2>${escapeHtml(item.display_name)}</h2>
        </div>
        ${detailCloseButton()}
      </div>
      <div class="detail-facts">
        <span>${item.is_active ? statusPill("active") : statusPill("inactive")}</span>
        <span>${escapeHtml(item.member_ref || "")}</span>
        <span>${escapeHtml(item.contact_hint || "")}</span>
      </div>
      <h3>${t("sections.rental_journey")}</h3>
      ${rentals.length ? renderRentalJourney(rentals) : `<div class="empty compact">${t("empty.no_rentals")}</div>`}
    </aside>
  `;
}

function renderRentalTable(items, compact = false) {
  if (!items.length) return `<div class="empty">${t("empty.no_rentals")}</div>`;
  const caps = capabilities();
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>${t("table.instrument")}</th><th>${t("table.member")}</th><th>${t("table.start")}</th><th>${t("table.due")}</th><th>${t("table.status")}</th><th></th></tr></thead>
        <tbody>${items.map((item) => `
          <tr class="clickable-row ${state.detail?.id === item.id ? "is-selected" : ""}" data-open="rentals" data-id="${item.id}" tabindex="0">
            <td><strong>${escapeHtml(item.instrument_name)}</strong><div class="muted">${escapeHtml(item.note)}</div></td>
            <td>${escapeHtml(item.member_name)}</td>
            <td>${formatDate(item.start_date)}</td>
            <td>${formatDate(item.due_date)}</td>
            <td>${statusPill(item.status)}</td>
            <td><div class="row-actions">
              ${caps.write && item.status !== "returned" ? `<button class="primary-button" data-return="${item.id}">${t("actions.return")}</button>` : ""}
              ${compact ? "" : `${caps.write ? `<button class="ghost-button" data-edit="rentals" data-id="${item.id}">${t("actions.edit")}</button>` : ""}
              ${caps.admin ? `<button class="danger-button" data-delete="rentals" data-id="${item.id}">${t("actions.delete")}</button>` : ""}`}
            </div></td>
          </tr>
        `).join("")}</tbody>
      </table>
    </div>
  `;
}

function renderRentalDetail(item) {
  if (!item) return "";
  return `
    <aside class="detail-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">${t("sections.rental_details")}</p>
          <h2>${escapeHtml(item.instrument_name)}</h2>
        </div>
        ${detailCloseButton()}
      </div>
      <div class="detail-facts">
        <span>${statusPill(item.status)}</span>
        <span>${escapeHtml(item.member_name)}</span>
        <span>${formatDate(item.start_date)}</span>
        <span>${item.due_date ? formatDate(item.due_date) : ""}</span>
      </div>
      <div class="journey">
        <article class="journey-stop active">
          <div class="journey-marker"></div>
          <div><strong>${t("table.start")}</strong><div>${formatDate(item.start_date)}</div></div>
        </article>
        ${item.due_date ? `<article class="journey-stop ${item.status === "overdue" ? "overdue" : "active"}"><div class="journey-marker"></div><div><strong>${t("table.due")}</strong><div>${formatDate(item.due_date)}</div></div></article>` : ""}
        ${item.return_date ? `<article class="journey-stop returned"><div class="journey-marker"></div><div><strong>${t("actions.return")}</strong><div>${formatDate(item.return_date)}</div></div></article>` : ""}
      </div>
      ${item.note ? `<p class="muted">${escapeHtml(item.note)}</p>` : ""}
    </aside>
  `;
}

function renderHistory() {
  const items = filterItems(state.records.history);
  const detail = state.detail?.entity === "history" ? renderHistoryDetail(state.records.history.find((item) => item.id === state.detail.id)) : "";
  if (!items.length) {
    view.innerHTML = `${renderToolbar("history")}<div class="empty">${t("empty.no_history")}</div>`;
    return;
  }
  view.innerHTML = `${renderToolbar("history")}
    <div class="${detail ? "split-view" : ""}">
      <div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>${t("table.when")}</th><th>${t("table.action")}</th><th>${t("table.instrument")}</th><th>${t("table.member")}</th><th>${t("table.service")}</th><th>${t("table.rental")}</th></tr></thead>
            <tbody>${items.map((item) => `
              <tr class="clickable-row ${state.detail?.id === item.id ? "is-selected" : ""}" data-open="history" data-id="${item.id}" tabindex="0">
                <td>${new Date(item.created_at).toLocaleString(locale())}</td>
                <td>${statusPill(item.action)}</td>
                <td>${escapeHtml(item.instrument_name)}</td>
                <td>${escapeHtml(item.member_name)}</td>
                <td>${renderHistoryServiceCell(item)}</td>
                <td>${escapeHtml(item.rental_id)}</td>
              </tr>
            `).join("")}</tbody>
          </table>
        </div>
      </div>
      ${detail}
    </div>
  `;
}

function renderHistoryServiceCell(item) {
  if (!item.service_record_id && !item.service_date && !item.service_condition) return "";
  const serviceDate = item.service_date ? `<span>${formatDate(item.service_date)}</span>` : "";
  const condition = item.service_condition ? conditionPill(item.service_condition) : "";
  return `<div class="history-service">${serviceDate}${condition}</div>`;
}

function renderHistoryDetail(item) {
  if (!item) return "";
  return `
    <aside class="detail-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">${t("sections.history_details")}</p>
          <h2>${escapeHtml(item.instrument_name || item.rental_id || item.service_record_id || t("entities.history"))}</h2>
        </div>
        ${detailCloseButton()}
      </div>
      <div class="detail-facts">
        <span>${statusPill(item.action)}</span>
        <span>${escapeHtml(item.actor || "")}</span>
        ${item.service_record_id ? `<span>${escapeHtml(item.service_record_id)}</span>` : ""}
        ${item.rental_id ? `<span>${escapeHtml(item.rental_id)}</span>` : ""}
      </div>
      <h3>${t("sections.event_journey")}</h3>
      <div class="journey">
        <article class="journey-stop active">
          <div class="journey-marker"></div>
          <div>
            <div class="journey-head">
              <strong>${new Date(item.created_at).toLocaleString(locale())}</strong>
              ${statusPill(item.action)}
            </div>
            <div>${escapeHtml(item.actor || t("table.actor"))}</div>
          </div>
        </article>
        ${renderHistoryRentalStop(item)}
        ${renderHistoryServiceStop(item)}
      </div>
      <dl class="detail-list">
        <div><dt>${t("table.instrument")}</dt><dd>${escapeHtml(item.instrument_name || item.instrument_id || "")}</dd></div>
        <div><dt>${t("table.member")}</dt><dd>${escapeHtml(item.member_name || item.member_id || "")}</dd></div>
        <div><dt>${t("table.service")}</dt><dd>${escapeHtml(item.service_record_id || "")}</dd></div>
        <div><dt>${t("table.rental")}</dt><dd>${escapeHtml(item.rental_id || "")}</dd></div>
      </dl>
      ${item.note ? `<p class="muted">${escapeHtml(item.note)}</p>` : ""}
    </aside>
  `;
}

function renderHistoryRentalStop(item) {
  if (!item.rental_id && !item.start_date && !item.due_date && !item.return_date) return "";
  const dates = [
    item.start_date ? `${t("table.start")}: ${formatDate(item.start_date)}` : "",
    item.due_date ? `${t("table.due")}: ${formatDate(item.due_date)}` : "",
    item.return_date ? `${t("actions.return")}: ${formatDate(item.return_date)}` : ""
  ].filter(Boolean).map(escapeHtml).join(" / ");
  const stopClass = item.return_date ? "returned" : item.due_date ? "active" : "rented";
  return `
    <article class="journey-stop ${stopClass}">
      <div class="journey-marker"></div>
      <div>
        <div class="journey-head">
          <strong>${t("table.rental")}</strong>
          ${item.rental_id ? `<span class="muted">${escapeHtml(item.rental_id)}</span>` : ""}
        </div>
        <div>${escapeHtml(item.member_name || "")}</div>
        ${dates ? `<div class="muted">${dates}</div>` : ""}
      </div>
    </article>
  `;
}

function renderHistoryServiceStop(item) {
  if (!item.service_record_id && !item.service_date && !item.service_condition && !item.next_service_date) return "";
  return `
    <article class="journey-stop condition-${escapeHtml(item.service_condition || "good")}">
      <div class="journey-marker"></div>
      <div>
        <div class="journey-head">
          <strong>${t("table.service")}</strong>
          ${item.service_condition ? conditionPill(item.service_condition) : ""}
        </div>
        <div>${item.service_date ? formatDate(item.service_date) : escapeHtml(item.service_record_id || "")}</div>
        ${item.next_service_date ? `<div class="muted">${escapeHtml(t("fields.next_service_date"))}: ${formatDate(item.next_service_date)} ${serviceDuePill(serviceDueStatus(item.next_service_date))}</div>` : ""}
      </div>
    </article>
  `;
}

function openDialog(entity, record = {}) {
  const hasId = Boolean(record.id || (entity === "associations" && record.tenant_id));
  dialogTitle.textContent = hasId ? t("dialog.edit", {entity: singular(entity)}) : t("dialog.new", {entity: singular(entity)});
  recordForm.dataset.entity = entity;
  recordForm.dataset.id = record.id || (entity === "associations" ? record.tenant_id : "") || "";
  formFields.innerHTML = schemas[entity].map(([name, label, type, required, span]) => renderField(name, label, type, required, span, record[name])).join("");
  dialog.showModal();
}

function renderField(name, label, type, required, span, value) {
  const requiredAttr = required ? "required" : "";
  const full = span === "full" ? " full" : "";
  if (type === "hidden") {
    return `<input id="${name}" name="${name}" type="hidden" value="${escapeHtml(value)}">`;
  }
  if (type === "textarea") {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><textarea id="${name}" name="${name}" ${requiredAttr}>${escapeHtml(value)}</textarea></div>`;
  }
  if (type === "json") {
    const jsonValue = value === undefined ? "[]" : JSON.stringify(value, null, 2);
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><textarea id="${name}" name="${name}" ${requiredAttr}>${escapeHtml(jsonValue)}</textarea></div>`;
  }
  if (type === "condition") {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><select id="${name}" name="${name}" ${requiredAttr}>
      ${["good", "watch", "needs_service", "in_service", "retired"].map((condition) => `<option value="${condition}" ${condition === (value || "good") ? "selected" : ""}>${t(`condition.${condition}`)}</option>`).join("")}
    </select></div>`;
  }
  if (type === "association_status") {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><select id="${name}" name="${name}" ${requiredAttr}>
      ${["active", "paused", "archived"].map((status) => `<option value="${status}" ${status === (value || "active") ? "selected" : ""}>${t(`status.${status}`)}</option>`).join("")}
    </select></div>`;
  }
  if (type === "user_status") {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><select id="${name}" name="${name}" ${requiredAttr}>
      ${["active", "disabled"].map((status) => `<option value="${status}" ${status === (value || "active") ? "selected" : ""}>${t(`status.${status}`)}</option>`).join("")}
    </select></div>`;
  }
  if (type === "global_role") {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><select id="${name}" name="${name}" ${requiredAttr}>
      ${["none", "reader", "operator", "admin", "platform_admin"].map((role) => `<option value="${role}" ${role === (value || "none") ? "selected" : ""}>${t(`global_role.${role}`)}</option>`).join("")}
    </select></div>`;
  }
  if (type === "access_profile") {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><select id="${name}" name="${name}" ${requiredAttr}>
      ${["full", "basic"].map((profile) => `<option value="${profile}" ${profile === (value || "full") ? "selected" : ""}>${t(`access_profile.${profile}`)}</option>`).join("")}
    </select></div>`;
  }
  if (type === "checkbox") {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><select id="${name}" name="${name}"><option value="true" ${value !== false ? "selected" : ""}>${t("actions.yes")}</option><option value="false" ${value === false ? "selected" : ""}>${t("actions.no")}</option></select></div>`;
  }
  if (type === "rental_instrument") {
    const options = state.records.instruments.filter((item) => item.status === "available" || item.id === value);
    return renderInstrumentSelect(name, label, requiredAttr, full, value, options);
  }
  if (type === "instrument") {
    return renderInstrumentSelect(name, label, requiredAttr, full, value, state.records.instruments);
  }
  if (type === "member") {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><select id="${name}" name="${name}" ${requiredAttr}>
      <option value="">${t("select.placeholder")}</option>
      ${state.records.members.filter((item) => item.is_active).map((item) => `<option value="${item.id}" ${item.id === value ? "selected" : ""}>${escapeHtml(item.display_name)}</option>`).join("")}
    </select></div>`;
  }
  return `<div class="field${full}"><label for="${name}">${t(label)}</label><input id="${name}" name="${name}" type="${type}" value="${escapeHtml(value)}" ${requiredAttr}></div>`;
}

function instrumentOptionLabel(item) {
  const parts = [
    item.name,
    item.serial,
    t(`status.${item.status}`),
    t(`condition.${item.service_condition || "good"}`)
  ].filter(Boolean);
  return parts.join(" / ");
}

function renderInstrumentSelect(name, label, requiredAttr, full, value, options) {
  return `<div class="field${full}"><label for="${name}">${t(label)}</label><select id="${name}" name="${name}" ${requiredAttr}>
    <option value="">${t("select.placeholder")}</option>
    ${options.map((item) => `<option value="${item.id}" ${item.id === value ? "selected" : ""}>${escapeHtml(instrumentOptionLabel(item))}</option>`).join("")}
  </select></div>`;
}

function singular(entity) {
  return entity === "members" ? t("entities.member") : entity === "rentals" ? t("entities.rental") : entity === "service_records" ? t("entities.service_record") : entity === "associations" ? t("entities.association") : entity === "user_access" ? t("entities.user_access") : t("entities.instrument");
}

function formPayload(form) {
  const payload = Object.fromEntries(new FormData(form).entries());
  Object.keys(payload).forEach((key) => {
    if (payload[key] === "") delete payload[key];
  });
  if ("is_active" in payload) payload.is_active = payload.is_active === "true";
  if ("value_chf" in payload) payload.value_chf = Number(payload.value_chf);
  if ("cost_chf" in payload) payload.cost_chf = Number(payload.cost_chf);
  if ("purchase_year" in payload) payload.purchase_year = Number(payload.purchase_year);
  ["tenant_roles", "member_links"].forEach((key) => {
    if (key in payload) payload[key] = JSON.parse(payload[key] || "[]");
  });
  return payload;
}

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    switchView(button.dataset.view);
    render();
  });
});

languageButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.lang = button.dataset.lang;
    localStorage.setItem("rentalLang", state.lang);
    render();
  });
});

view.addEventListener("input", (event) => {
  if (event.target.matches("[data-search]")) {
    const cursor = event.target.selectionStart;
    state.search = event.target.value;
    render();
    const nextSearch = view.querySelector("[data-search]");
    if (nextSearch) {
      nextSearch.focus();
      nextSearch.setSelectionRange(cursor, cursor);
    }
  }
  if (event.target.matches("[data-sort]")) {
    state.sort = event.target.value;
    render();
  }
});

view.addEventListener("click", async (event) => {
  const target = event.target.closest("button");
  if (target) {
    event.stopPropagation();
    if (target.dataset.closeDetail !== undefined) {
      state.detail = null;
      render();
      return;
    }
    if (target.dataset.status) {
      state.status = target.dataset.status;
      render();
      return;
    }
    if (target.dataset.sortDirection !== undefined) {
      state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
      render();
      return;
    }
    if (target.dataset.jump) {
      switchView(target.dataset.jump);
      render();
      return;
    }
    if (target.dataset.exportInstruments !== undefined) {
      await exportInstruments();
      return;
    }
    if (target.dataset.importInstruments !== undefined) {
      instrumentFile.value = "";
      instrumentFile.click();
      return;
    }
    if (target.dataset.exportTenantAccess !== undefined) {
      await exportTenantAccessUsers();
      return;
    }
    if (target.dataset.serviceAdd) {
      openDialog("service_records", {
        instrument_id: target.dataset.serviceAdd,
        service_date: new Date().toISOString().slice(0, 10),
        condition: "good"
      });
      return;
    }
    if (target.dataset.editAssociation) {
      const record = state.associations.find((item) => item.tenant_id === target.dataset.editAssociation);
      openDialog("associations", record);
      return;
    }
    if (target.dataset.newUser !== undefined) {
      openDialog("user_access", {status: "active", global_role: "none", access_profile: "full", tenant_roles: [], member_links: []});
      return;
    }
    if (target.dataset.editUser) {
      const record = state.users.find((item) => item.id === target.dataset.editUser);
      openDialog("user_access", record);
      return;
    }
    if (target.dataset.deleteUser) {
      await removeUser(target.dataset.deleteUser);
      return;
    }
    if (target.dataset.openAssociation) {
      openAssociation(target.dataset.openAssociation);
      return;
    }
    if (target.dataset.edit) {
      const entity = target.dataset.edit;
      const record = state.records[entity].find((item) => item.id === target.dataset.id);
      openDialog(entity, record);
      return;
    }
    if (target.dataset.delete) {
      await removeRecord(target.dataset.delete, target.dataset.id);
      return;
    }
    if (target.dataset.return) {
      await returnRecord(target.dataset.return);
      return;
    }
  }
  const row = event.target.closest("[data-open]");
  if (row) {
    state.detail = {entity: row.dataset.open, id: row.dataset.id};
    render();
    return;
  }
  const dashboardInstrument = event.target.closest("[data-open-dashboard-instrument]");
  if (dashboardInstrument) {
    switchView("instruments");
    state.detail = {entity: "instruments", id: dashboardInstrument.dataset.openDashboardInstrument};
    render();
  }
});

view.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && state.detail) {
    state.detail = null;
    render();
    return;
  }
  if (event.key !== "Enter") return;
  const row = event.target.closest("[data-open]");
  const dashboardInstrument = event.target.closest("[data-open-dashboard-instrument]");
  if (row) {
    state.detail = {entity: row.dataset.open, id: row.dataset.id};
  } else if (dashboardInstrument) {
    switchView("instruments");
    state.detail = {entity: "instruments", id: dashboardInstrument.dataset.openDashboardInstrument};
  } else {
    return;
  }
  render();
});

primaryAction.addEventListener("click", () => {
  if (state.view === "admin") {
    openDialog("associations", {status: "active", locale: "de-CH"});
    return;
  }
  const entity = state.view === "instruments" ? "instruments" : state.view === "members" ? "members" : state.view === "service_records" ? "service_records" : "rentals";
  const today = new Date().toISOString().slice(0, 10);
  const defaults = entity === "service_records"
    ? {service_date: today, condition: "good"}
    : {start_date: today, is_active: true};
  openDialog(entity, defaults);
});

recordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (event.submitter?.value === "cancel") {
    dialog.close();
    return;
  }
  const entity = recordForm.dataset.entity;
  const id = recordForm.dataset.id;
  const payload = formPayload(recordForm);
  try {
    assertLowPiiWrite(payload, entity);
    if (entity === "associations") {
      if (id) {
        await adminApi(`/associations/${id}`, {method: "PUT", body: JSON.stringify(payload)});
      } else {
        await adminApi("/associations", {method: "POST", body: JSON.stringify(payload)});
      }
    } else if (entity === "user_access") {
      if (id) {
        await adminApi(`/users/${id}`, {method: "PUT", body: JSON.stringify(payload)});
      } else {
        await adminApi("/users", {method: "POST", body: JSON.stringify(payload)});
      }
    } else if (id) {
      await api(`/${entity}/${id}`, {method: "PUT", body: JSON.stringify(payload)});
    } else {
      await api(`/${entity}`, {method: "POST", body: JSON.stringify(payload)});
    }
    dialog.close();
    await loadData();
    showMessage(t("messages.saved", {entity: singular(entity)}));
  } catch (error) {
    await handleMutationError(error);
  }
});

async function removeRecord(entity, id) {
  if (!window.confirm(t("confirm.delete"))) return;
  try {
    await api(`/${entity}/${id}`, {method: "DELETE"});
    await loadData();
    showMessage(t("messages.deleted", {entity: singular(entity)}));
  } catch (error) {
    await handleMutationError(error);
  }
}

async function removeUser(id) {
  if (!window.confirm(t("confirm.delete"))) return;
  try {
    await adminApi(`/users/${id}`, {method: "DELETE"});
    await loadData();
    showMessage(t("messages.deleted", {entity: singular("user_access")}));
  } catch (error) {
    await handleMutationError(error);
  }
}

async function returnRecord(id) {
  try {
    await api(`/rentals/${id}/return`, {method: "POST", body: JSON.stringify({return_date: new Date().toISOString().slice(0, 10)})});
    await loadData();
    showMessage(t("messages.returned"));
  } catch (error) {
    await handleMutationError(error);
  }
}

seedButton.addEventListener("click", async () => {
  try {
    await api("/bootstrap", {method: "POST", body: "{}"});
    await loadData();
    showMessage(t("messages.demo_loaded"));
  } catch (error) {
    await handleMutationError(error);
  }
});

exportButton.addEventListener("click", async () => {
  try {
    const data = await api("/export");
    const date = new Date().toISOString().slice(0, 10);
    downloadJson(`rental-${state.tenant}-${date}.json`, data);
    showMessage(t("messages.export_downloaded"));
  } catch (error) {
    await handleMutationError(error);
  }
});

importButton.addEventListener("click", () => {
  importFile.value = "";
  importFile.click();
});

importFile.addEventListener("change", async () => {
  const file = importFile.files?.[0];
  if (!file) return;
  if (!window.confirm(t("confirm.import", {tenant: state.tenant}))) return;
  try {
    const payload = await readJsonFile(file);
    assertLowPiiImport(payload);
    const result = await api("/import", {method: "PUT", body: JSON.stringify(payload)});
    await loadData();
    showMessage(t("messages.import_complete", {
      instruments: result.summary.instruments,
      members: result.summary.members
    }));
  } catch (error) {
    await handleMutationError(error);
  }
});

hitobitoImportButton.addEventListener("click", () => {
  hitobitoFile.value = "";
  hitobitoFile.click();
});

hitobitoFile.addEventListener("change", async () => {
  const file = hitobitoFile.files?.[0];
  if (!file) return;
  if (!window.confirm(t("confirm.import_hitobito", {tenant: state.tenant}))) return;
  try {
    const payload = await readJsonFile(file);
    const result = await api("/members/import/hitobito", {method: "PUT", body: JSON.stringify(payload)});
    await loadData();
    showMessage(t("messages.hitobito_import_complete", {
      created: result.report.created,
      updated: result.report.updated
    }));
  } catch (error) {
    await handleMutationError(error);
  }
});

async function exportInstruments() {
  try {
    const data = await api("/instruments/export");
    const date = new Date().toISOString().slice(0, 10);
    downloadJson(`rental-${state.tenant}-instruments-${date}.json`, data);
    showMessage(t("messages.instrument_export_downloaded"));
  } catch (error) {
    await handleMutationError(error);
  }
}

async function exportTenantAccessUsers() {
  try {
    const data = await adminApi("/users/export/tenant-access");
    const date = new Date().toISOString().slice(0, 10);
    downloadJson(`rental-tenant-access-${date}.json`, data.data || []);
    showMessage(t("messages.tenant_access_export_downloaded"));
  } catch (error) {
    await handleMutationError(error);
  }
}

instrumentFile.addEventListener("change", async () => {
  const file = instrumentFile.files?.[0];
  if (!file) return;
  if (!window.confirm(t("confirm.import_instruments", {tenant: state.tenant}))) return;
  try {
    const payload = await readJsonFile(file);
    assertLowPiiImport(payload);
    const result = await api("/instruments/import", {method: "PUT", body: JSON.stringify(payload)});
    await loadData();
    showMessage(t("messages.instrument_import_complete", {
      created: result.report.created,
      updated: result.report.updated
    }));
  } catch (error) {
    await handleMutationError(error);
  }
});

refreshButton.addEventListener("click", () => {
  loadData().catch((error) => showMessage(error.message, true));
});

saveTenant.addEventListener("click", () => {
  if (state.context?.tenant_locked) return;
  const tenant = tenantInput.value.trim() || "demo-association";
  if (!tenantPattern.test(tenant)) {
    showMessage(t("tenant.invalid"), true);
    return;
  }
  state.tenant = tenant;
  localStorage.setItem("rentalTenant", tenant);
  loadData().catch((error) => showMessage(error.message, true));
});

function openAssociation(tenant) {
  if (state.context?.tenant_locked) return;
  if (!tenantPattern.test(tenant)) {
    showMessage(t("tenant.invalid"), true);
    return;
  }
  state.tenant = tenant;
  switchView("dashboard");
  tenantInput.value = tenant;
  localStorage.setItem("rentalTenant", tenant);
  loadData().catch((error) => showMessage(error.message, true));
}

async function init() {
  applyLanguage();
  const context = await apiContext();
  applyContext(context);
  await loadData();
}

init().catch((error) => {
  render();
  showMessage(error.message, true);
});
