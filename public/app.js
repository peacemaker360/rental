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
  accessRequests: [],
  accessRequestResult: null,
  summary: {},
  meta: {revision: 0, updated_at: null},
  context: null,
  authStatus: "checking",
  authReason: "checking",
  authEmail: "",
  isLoading: true,
  authError: ""
};

const viewTitle = document.querySelector("#viewTitle");
const view = document.querySelector("#view");
const adminNavItem = document.querySelector('[data-view="admin"]');
const message = document.querySelector("#message");
const messageText = document.querySelector("#messageText");
const messageClose = document.querySelector("#messageClose");
const primaryAction = document.querySelector("#primaryAction");
const seedButton = document.querySelector("#seedButton");
const exportButton = document.querySelector("#exportButton");
const importButton = document.querySelector("#importButton");
const importFile = document.querySelector("#importFile");
const hitobitoImportButton = document.querySelector("#hitobitoImportButton");
const hitobitoFile = document.querySelector("#hitobitoFile");
const instrumentFile = document.querySelector("#instrumentFile");
const refreshButton = document.querySelector("#refreshButton");
const userMenu = document.querySelector("#userMenu");
const userMenuEmail = document.querySelector("#userMenuEmail");
const userMenuTenant = document.querySelector("#userMenuTenant");
const userMenuRole = document.querySelector("#userMenuRole");
const userMenuAccess = document.querySelector("#userMenuAccess");
const mobileUserMenu = document.querySelector("#mobileUserMenu");
const mobileUserMenuEmail = document.querySelector("#mobileUserMenuEmail");
const mobileUserMenuTenant = document.querySelector("#mobileUserMenuTenant");
const mobileUserMenuRole = document.querySelector("#mobileUserMenuRole");
const mobileUserMenuAccess = document.querySelector("#mobileUserMenuAccess");
const tenantInput = document.querySelector("#tenantInput");
const tenantLabel = document.querySelector("#tenantLabel");
const mobileTenantLabel = document.querySelector("#mobileTenantLabel");
const tenantRevision = document.querySelector("#tenantRevision");
const tenantUpdatedAt = document.querySelector("#tenantUpdatedAt");
const tenantBox = document.querySelector(".tenant-box");
const tenantMeta = document.querySelector(".tenant-meta");
const associationHelp = document.querySelector("#associationHelp");
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
const accessRequestStorageKey = "rentalAccessRequest";

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
    "labels.need_help": "Need help?",
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
    "actions.retry_sign_in": "Retry sign-in",
    "actions.logout": "Log out",
    "actions.request_join": "Request to join",
    "actions.approve": "Approve",
    "actions.deny": "Deny",
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
    "actions.add_tenant_role": "Add tenant role",
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
    "fields.access_email": "Access email",
    "fields.access_email_configured": "Access email configured",
    "fields.access_email_help": "Leave empty to keep the configured email, or enter a new email to replace it.",
    "fields.forever": "Forever",
    "fields.is_active": "Active",
    "fields.instrument_id": "Instrument",
    "fields.member_id": "Member",
    "fields.start_date": "Start date",
    "fields.due_date": "Due date",
    "fields.return_date": "Return date",
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
    "fields.contact": "Contact",
    "fields.hitobito_group_ref": "Hitobito group ref",
    "fields.inventory_ref": "Inventory ref",
    "fields.tenant_role": "Tenant role",
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
    "sections.my_rentals": "My rentals",
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
    "sections.access_requests": "Join requests",
    "empty.no_overdue": "No overdue rentals",
    "empty.no_attention": "No rentals or service items need attention",
    "empty.no_service_records": "No service records",
    "empty.no_associations": "No associations",
    "empty.no_users": "No users",
    "empty.no_access_requests": "No join requests",
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
    "messages.join_request_sent": "Join request sent",
    "messages.join_request_pending": "Join request pending",
    "messages.access_request_approved": "Join request approved",
    "messages.access_request_denied": "Join request denied",
    "messages.instrument_import_complete": "Instrument import complete: {created} created, {updated} updated",
    "messages.import_blocked_pii": "Import blocked: remove contact fields before uploading ({fields})",
    "messages.import_invalid_json": "Import blocked: choose a valid JSON file",
    "messages.invalid_email": "Enter a valid email address",
    "messages.write_blocked_pii": "Remove contact details before saving ({fields})",
    "messages.revision_conflict": "This tenant changed in another session. The latest data is loaded; review and try again.",
    "auth.start_title": "Start with your association account",
    "auth.start_lead": "Rental Desk is available after your sign-in email and association permissions are confirmed.",
    "auth.sign_in": "Sign-in",
    "auth.signed_in": "Signed in",
    "auth.sign_in_needed": "Sign in to check whether your association access is ready.",
    "auth.registration_hint": "Need access? Ask your association administrator to register your sign-in email and assign you to the right association.",
    "auth.invalid_token": "Your sign-in could not be verified or is no longer valid.",
    "auth.no_profile": "You are signed in, but your app access is still missing or disabled.",
    "auth.access_denied": "Your sign-in worked, but this association is not available to your account.",
    "auth.pending_hint": "Your request is pending. You can retry sign-in or submit another request if the details changed.",
    "auth.email_help": "Use the same email you use to sign in.",
    "auth.request_submitted": "Your access request was submitted.",
    "auth.request_reference": "Reference",
    "auth.request_status": "Status",
    "auth.request_contact": "Association contact",
    "auth.association_code": "Association code",
    "auth.association_code_placeholder": "association code",
    "status.all": "all",
    "status.available": "available",
    "status.rented": "rented",
    "status.active": "active",
    "status.overdue": "overdue",
    "status.returned": "returned",
    "status.inactive": "inactive",
    "status.paused": "paused",
    "status.pending": "pending",
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
    "labels.need_help": "Brauchst du Hilfe?",
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
    "actions.retry_sign_in": "Anmeldung erneut versuchen",
    "actions.logout": "Abmelden",
    "actions.request_join": "Beitritt anfragen",
    "actions.approve": "Freigeben",
    "actions.deny": "Ablehnen",
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
    "actions.add_tenant_role": "Mandantenrolle hinzufügen",
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
    "fields.access_email": "Access-E-Mail",
    "fields.access_email_configured": "Access-E-Mail hinterlegt",
    "fields.access_email_help": "Leer lassen, um die hinterlegte E-Mail zu behalten, oder eine neue E-Mail zum Ersetzen eingeben.",
    "fields.forever": "Unbefristet",
    "fields.is_active": "Aktiv",
    "fields.instrument_id": "Instrument",
    "fields.member_id": "Mitglied",
    "fields.start_date": "Startdatum",
    "fields.due_date": "Fälligkeitsdatum",
    "fields.return_date": "Rückgabedatum",
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
    "fields.contact": "Kontakt",
    "fields.hitobito_group_ref": "Hitobito-Gruppenreferenz",
    "fields.inventory_ref": "Inventarreferenz",
    "fields.tenant_role": "Mandantenrolle",
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
    "sections.my_rentals": "Meine Ausleihen",
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
    "sections.access_requests": "Beitrittsanfragen",
    "empty.no_overdue": "Keine überfälligen Ausleihen",
    "empty.no_attention": "Keine Ausleihen oder Servicepunkte benötigen Aufmerksamkeit",
    "empty.no_service_records": "Keine Serviceeinträge",
    "empty.no_associations": "Keine Organisationen",
    "empty.no_users": "Keine Benutzer",
    "empty.no_access_requests": "Keine Beitrittsanfragen",
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
    "messages.join_request_sent": "Beitrittsanfrage gesendet",
    "messages.join_request_pending": "Beitrittsanfrage offen",
    "messages.access_request_approved": "Beitrittsanfrage freigegeben",
    "messages.access_request_denied": "Beitrittsanfrage abgelehnt",
    "messages.instrument_import_complete": "Instrumentenimport abgeschlossen: {created} erstellt, {updated} aktualisiert",
    "messages.import_blocked_pii": "Import blockiert: Kontaktfelder vor dem Hochladen entfernen ({fields})",
    "messages.import_invalid_json": "Import blockiert: Bitte eine gültige JSON-Datei auswählen",
    "messages.invalid_email": "Bitte eine gültige E-Mail-Adresse eingeben",
    "messages.write_blocked_pii": "Kontaktdaten vor dem Speichern entfernen ({fields})",
    "messages.revision_conflict": "Dieser Mandant wurde in einer anderen Sitzung geändert. Die aktuellen Daten sind geladen; bitte prüfen und erneut versuchen.",
    "auth.start_title": "Mit dem Vereinszugang starten",
    "auth.start_lead": "Die Verleihverwaltung ist verfügbar, sobald deine Anmelde-E-Mail und Vereinsrechte bestätigt sind.",
    "auth.sign_in": "Anmeldung",
    "auth.signed_in": "Angemeldet",
    "auth.sign_in_needed": "Melde dich an, um zu prüfen, ob dein Vereinszugriff bereit ist.",
    "auth.registration_hint": "Brauchst du Zugriff? Bitte deine Vereinsadministration, deine Anmelde-E-Mail zu registrieren und dem richtigen Verein zuzuweisen.",
    "auth.invalid_token": "Deine Anmeldung konnte nicht verifiziert werden oder ist nicht mehr gültig.",
    "auth.no_profile": "Du bist angemeldet, aber dein App-Zugriff fehlt noch oder ist deaktiviert.",
    "auth.access_denied": "Deine Anmeldung funktioniert, aber dieser Verein ist fuer dein Konto nicht freigegeben.",
    "auth.pending_hint": "Deine Anfrage ist offen. Du kannst die Anmeldung erneut versuchen oder eine neue Anfrage senden, falls sich Details geändert haben.",
    "auth.email_help": "Verwende dieselbe E-Mail, die du auch fuer die Anmeldung nutzt.",
    "auth.request_submitted": "Deine Beitrittsanfrage wurde gesendet.",
    "auth.request_reference": "Referenz",
    "auth.request_status": "Status",
    "auth.request_contact": "Kontakt der Organisation",
    "auth.association_code": "Vereinscode",
    "auth.association_code_placeholder": "Vereinscode",
    "status.all": "alle",
    "status.available": "verfügbar",
    "status.rented": "ausgeliehen",
    "status.active": "aktiv",
    "status.overdue": "überfällig",
    "status.returned": "zurückgegeben",
    "status.inactive": "inaktiv",
    "status.paused": "pausiert",
    "status.pending": "offen",
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
if (mobileTenantLabel) mobileTenantLabel.textContent = state.tenant;

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
    ["access_email", "fields.access_email", "email", false],
    ["contact_hint", "fields.contact_hint", "text", false, "full"],
    ["is_active", "fields.is_active", "checkbox", false]
  ],
  rentals: [
    ["instrument_id", "fields.instrument_id", "rental_instrument", true],
    ["member_id", "fields.member_id", "member", true],
    ["start_date", "fields.start_date", "date", true],
    ["due_date", "fields.due_date", "date", false],
    ["return_date", "fields.return_date", "date", false],
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
    ["contact", "fields.contact", "text", false],
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
    ["tenant_roles", "fields.tenant_roles", "tenant_roles", false, "full"],
    ["member_links", "fields.member_links", "member_links", false, "full"]
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
    const error = new Error(data.error || `Request failed (${response.status})`);
    error.status = response.status;
    error.data = data;
    throw error;
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

function accessRequestApi(payload) {
  return fetch("/api/access-requests", {
    method: "POST",
    headers: {"content-type": "application/json"},
    body: JSON.stringify(payload)
  }).then(async (response) => {
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

function loadStoredAccessRequest() {
  try {
    const raw = localStorage.getItem(accessRequestStorageKey);
    if (!raw) return null;
    const request = JSON.parse(raw);
    return request && typeof request === "object" ? request : null;
  } catch {
    return null;
  }
}

function saveStoredAccessRequest(request) {
  if (!request || typeof request !== "object") return;
  localStorage.setItem(accessRequestStorageKey, JSON.stringify(request));
}

function authReasonFromError(error) {
  const message = String(error?.message || "").toLowerCase();
  if (error?.status === 401 || message.includes("missing signed tenant context") || (message.includes("missing") && message.includes("token"))) return "missing_token";
  if (message.includes("no user access profile")) return "no_profile";
  if (message.includes("user is not allowed for this tenant") || message.includes("user access profile is disabled") || message.includes("user access profile has no tenant")) return "access_denied";
  return "auth_error";
}

function authEmailFromError(error) {
  const email = String(error?.data?.user_email || "").trim().toLowerCase();
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email) ? email : "";
}

function hasLikelySignInToken() {
  return state.authStatus === "signed_out" && ["no_profile", "access_denied"].includes(state.authReason);
}

function currentAuthStartState() {
  return state.accessRequestResult ? "pending_request" : state.authReason;
}

function authStartSteps() {
  const hasRequest = Boolean(state.accessRequestResult);
  const authState = currentAuthStartState();
  const hasToken = hasLikelySignInToken();
  return [
    {
      state: hasToken ? "done" : "current",
      title: t("auth.sign_in"),
      body: hasToken ? t("auth.signed_in") : t("auth.sign_in_needed")
    },
    {
      state: authState === "pending_request" || authState === "no_profile" || authState === "access_denied" ? "current" : "waiting",
      title: t("entities.user_access"),
      body: authState === "pending_request" ? t("auth.pending_hint") : authState === "missing_token" ? t("auth.invalid_token") : authState === "access_denied" ? t("auth.access_denied") : t("auth.no_profile")
    },
    {
      state: hasRequest ? "current" : "waiting",
      title: t("entities.association"),
      body: t("auth.registration_hint")
    }
  ];
}

function updateJoinRequestSubmit(form) {
  const tenant = form?.querySelector('[name="tenant_id"]')?.value.trim().toLowerCase() || "";
  const button = form?.querySelector("[data-join-submit]");
  if (button) button.disabled = !tenantPattern.test(tenant);
}

function applyContext(context) {
  state.context = context;
  state.authStatus = "signed_in";
  state.authReason = "signed_in";
  state.authEmail = context.user_email || "";
  state.authError = "";
  const switcherVisible = shouldShowTenantSwitcher();
  state.tenant = context.mode === "local" || context.mode === "open"
    ? localStorage.getItem("rentalTenant") || state.tenant || context.tenant_id
    : context.tenant_id;
  tenantInput.value = state.tenant;
  if (context.tenant_locked && !switcherVisible) {
    tenantInput.disabled = true;
    saveTenant.disabled = true;
    saveTenant.title = t("tenant.locked");
  } else {
    tenantInput.disabled = false;
    saveTenant.disabled = false;
  }
  tenantLabel.textContent = state.tenant;
  if (mobileTenantLabel) mobileTenantLabel.textContent = state.tenant;
  applyMeta(context.meta);
  applyAccessChrome();
}

function renderUserMenu() {
  const context = state.context;
  const caps = capabilities();
  const role = context?.global_role && context.global_role !== "none" ? context.global_role : context?.role || "viewer";
  const roleLabel = context?.global_role && context.global_role !== "none"
    ? t(`global_role.${role}`)
    : role === "admin" ? t("tenant_role.admin") : role === "operator" ? t("tenant_role.operator") : t("tenant_role.reader");
  const accessLabel = caps.admin ? t("tenant_role.admin") : caps.write ? t("tenant_role.operator") : t("tenant_role.reader");
  [
    [userMenu, userMenuEmail, userMenuTenant, userMenuRole, userMenuAccess],
    [mobileUserMenu, mobileUserMenuEmail, mobileUserMenuTenant, mobileUserMenuRole, mobileUserMenuAccess]
  ].forEach(([menu, emailNode, tenantNode, roleNode, accessNode]) => {
    if (!menu) return;
    menu.hidden = state.authStatus !== "signed_in";
    if (emailNode) emailNode.textContent = context?.user_email || context?.actor_id || "User";
    if (tenantNode) tenantNode.textContent = state.tenant;
    if (roleNode) roleNode.textContent = roleLabel;
    if (accessNode) accessNode.textContent = accessLabel;
  });
}

function applyMeta(meta = state.meta) {
  if (meta && typeof meta === "object") {
    state.meta = {...state.meta, ...meta};
  }
  applyAccessChrome();
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
  if (state.context?.tenant_locked && !shouldShowTenantSwitcher()) {
    saveTenant.title = t("tenant.locked");
  }
  applyMeta();
}

function hasGlobalRole() {
  const globalRole = state.context?.global_role || "none";
  return globalRole !== "none" || Boolean(state.context?.has_global_role);
}

function shouldShowTenantSwitcher() {
  const context = state.context;
  if (!context) return true;
  if (context.mode === "local" || context.mode === "open") return true;
  return Boolean(context.tenant_switchable || hasGlobalRole() || Number(context.tenant_count || 0) > 1);
}

function shouldShowOperationalMeta() {
  const caps = capabilities();
  return Boolean(caps.write || caps.admin);
}

function applyAccessChrome() {
  const switcherVisible = state.authStatus === "signed_in" && shouldShowTenantSwitcher();
  const metaVisible = state.authStatus === "signed_in" && shouldShowOperationalMeta();
  const userMenuVisible = state.authStatus === "signed_in";
  if (tenantBox) tenantBox.hidden = !switcherVisible && !metaVisible && !userMenuVisible;
  if (tenantInput) tenantInput.hidden = !switcherVisible;
  if (saveTenant) saveTenant.hidden = !switcherVisible;
  const tenantRow = tenantInput?.closest(".tenant-row");
  if (tenantRow) tenantRow.hidden = !switcherVisible && !userMenuVisible;
  const tenantLabelElement = tenantBox?.querySelector("label");
  if (tenantLabelElement) tenantLabelElement.hidden = !switcherVisible;
  if (tenantMeta) tenantMeta.hidden = !metaVisible;
}

function renderAssociationHelp() {
  if (!associationHelp) return;
  const association = state.summary?.association || {};
  const contact = association.contact || "";
  const visible = state.authStatus === "signed_in" && isBasicProfile() && Boolean(contact);
  associationHelp.hidden = !visible;
  if (!visible) {
    associationHelp.innerHTML = "";
    return;
  }
  const label = association.display_name || state.tenant;
  const contactHtml = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(contact)
    ? `<a href="mailto:${escapeHtml(contact)}">${escapeHtml(contact)}</a>`
    : `<span>${escapeHtml(contact)}</span>`;
  associationHelp.innerHTML = `
    <span>${t("labels.need_help")}</span>
    <strong>${escapeHtml(label)}</strong>
    ${contactHtml}
  `;
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
  const allowedFields = entity === "user_access" ? new Set(["email"]) : entity === "associations" ? new Set(["contact"]) : new Set();
  const blocked = blockedPiiPaths(payload, "payload", [], allowedFields);
  if (!blocked.length) return;
  const visible = blocked.slice(0, 3).join(", ");
  throw new Error(t("messages.write_blocked_pii", {fields: visible}));
}

function showMessage(text, isError = false) {
  if (messageText) messageText.textContent = text;
  else message.textContent = text;
  message.classList.toggle("is-error", isError);
  message.hidden = false;
  window.clearTimeout(showMessage.timer);
  showMessage.timer = window.setTimeout(() => {
    message.hidden = true;
  }, 60000);
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

function isBasicProfile() {
  return capabilities().access_profile === "basic";
}

function hasExistingTenantData() {
  return Object.values(state.records).some((records) => Array.isArray(records) && records.length > 1);
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
  const usersPromise = capabilities().admin ? adminApi("/users").catch(() => ({data: []})) : Promise.resolve({data: []});
  const requestsPromise = capabilities().admin ? adminApi("/access-requests").catch(() => ({data: []})) : Promise.resolve({data: []});
  const [summary, instruments, members, rentals, serviceRecords, history, associations, users, accessRequests] = await Promise.all([
    api("/summary"),
    api("/instruments"),
    api("/members"),
    api("/rentals"),
    api("/service_records"),
    api("/history"),
    associationsPromise,
    usersPromise,
    requestsPromise
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
  state.accessRequests = accessRequests.data || [];
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
  document.body.classList.toggle("is-loading", Boolean(state.isLoading));
  document.body.classList.toggle("is-auth-start", state.authStatus !== "signed_in");
  if (state.authStatus !== "signed_in") {
    renderAuthStart();
    return;
  }
  const caps = capabilities();
  const basic = isBasicProfile();
  if (basic && state.view !== "dashboard") {
    switchView("dashboard");
  }
  if (adminNavItem) adminNavItem.hidden = !caps.admin;
  if (state.view === "admin" && !caps.admin) {
    switchView("dashboard");
  }
  viewTitle.textContent = t(`views.${state.view}`);
  tenantLabel.textContent = state.tenant;
  if (mobileTenantLabel) mobileTenantLabel.textContent = state.tenant;
  primaryAction.hidden = basic || state.view === "history" || (state.view === "admin" && !caps.admin);
  primaryAction.textContent = state.view === "admin" ? t("actions.new_association") : state.view === "instruments" ? t("actions.new_instruments") : state.view === "members" ? t("actions.new_members") : state.view === "service_records" ? t("actions.new_service_records") : t("actions.new_rentals");
  primaryAction.disabled = state.view === "admin" ? !caps.platform_admin : !caps.write;
  seedButton.hidden = basic || hasExistingTenantData();
  seedButton.disabled = !caps.admin || seedButton.hidden;
  exportButton.hidden = basic;
  importButton.hidden = basic;
  refreshButton.hidden = basic;
  exportButton.disabled = !caps.admin || basic;
  importButton.disabled = !caps.admin || basic;
  hitobitoImportButton.hidden = basic || state.view !== "members";
  hitobitoImportButton.disabled = !caps.admin;
  renderUserMenu();
  renderAssociationHelp();

  document.querySelectorAll(".nav-item").forEach((button) => {
    if (basic) {
      button.hidden = button.dataset.view !== "dashboard";
    } else if (button.dataset.view === "admin") {
      button.hidden = !caps.admin;
    } else {
      button.hidden = false;
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

function renderAuthStart() {
  viewTitle.textContent = t("auth.start_title");
  tenantLabel.textContent = t("app.eyebrow");
  if (mobileTenantLabel) mobileTenantLabel.textContent = t("app.eyebrow");
  tenantInput.disabled = true;
  saveTenant.disabled = true;
  primaryAction.hidden = true;
  seedButton.hidden = false;
  seedButton.disabled = true;
  exportButton.disabled = true;
  importButton.disabled = true;
  hitobitoImportButton.disabled = true;
  if (userMenu) userMenu.hidden = true;
  if (mobileUserMenu) mobileUserMenu.hidden = true;
  if (associationHelp) associationHelp.hidden = true;
  refreshButton.disabled = false;
  tenantRevision.textContent = "0";
  tenantUpdatedAt.textContent = "";
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.remove("is-active");
  });
  const request = state.accessRequestResult;
  const associationContact = request?.association?.contact;
  const emailValue = state.authEmail || request?.email || "";
  const steps = authStartSteps();
  view.innerHTML = `
    <section class="auth-start" aria-labelledby="authStartTitle">
      <div class="auth-start-mark">RD</div>
      <div>
        <p class="eyebrow">${t("app.eyebrow")}</p>
        <h2 id="authStartTitle">${t("auth.start_title")}</h2>
        <p>${t("auth.start_lead")}</p>
      </div>
      <div class="auth-start-steps" aria-label="${escapeHtml(t("auth.start_title"))}">
        ${steps.map((step, index) => `
          <div class="auth-step auth-step-${step.state}">
            <span>${index + 1}</span>
            <strong>${escapeHtml(step.title)}</strong>
            <p>${escapeHtml(step.body)}</p>
          </div>
        `).join("")}
      </div>
      <div class="auth-start-actions">
        <form class="auth-request-form" data-join-request>
          <label for="joinEmail">${t("fields.email")}</label>
          <input id="joinEmail" name="email" type="email" autocomplete="email" required placeholder="name@example.org" value="${escapeHtml(emailValue)}" aria-describedby="joinEmailHelp">
          <p id="joinEmailHelp" class="muted">${t("auth.email_help")}</p>
          <label for="joinTenant">${t("auth.association_code")}</label>
          <div class="auth-request-row">
            <input id="joinTenant" name="tenant_id" autocomplete="off" spellcheck="false" autocapitalize="none" pattern="[a-z0-9][a-z0-9_-]{1,62}" required placeholder="${escapeHtml(t("auth.association_code_placeholder"))}">
            <button class="primary-button" data-join-submit disabled>${t("actions.request_join")}</button>
          </div>
        </form>
        <div class="auth-session-actions">
          <button type="button" class="primary-button" data-auth-retry>${t("actions.retry_sign_in")}</button>
          ${hasLikelySignInToken() ? `<button type="button" class="ghost-button" data-logout>${t("actions.logout")}</button>` : ""}
        </div>
      </div>
      ${request ? `
        <aside class="auth-request-result">
          <div class="journey-head">
            <strong>${t("auth.request_submitted")}</strong>
            ${statusPill(request.status || "pending")}
          </div>
          <dl>
            <div><dt>${t("auth.request_reference")}</dt><dd>${escapeHtml(request.id || "")}</dd></div>
            <div><dt>${t("labels.tenant")}</dt><dd>${escapeHtml(request.tenant_id || "")}</dd></div>
            <div><dt>${t("fields.email")}</dt><dd>${escapeHtml(request.email || "")}</dd></div>
            <div><dt>${t("auth.request_status")}</dt><dd>${escapeHtml(t(`status.${request.status || "pending"}`))}</dd></div>
            ${associationContact ? `<div><dt>${t("auth.request_contact")}</dt><dd>${escapeHtml(associationContact)}</dd></div>` : ""}
          </dl>
        </aside>
      ` : ""}
    </section>
  `;
}

function renderDashboard() {
  if (isBasicProfile()) {
    renderBasicDashboard();
    return;
  }
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

function renderBasicDashboard() {
  const rentals = state.records.rentals
    .filter((rental) => rental.status !== "returned")
    .sort((a, b) => String(a.due_date || "").localeCompare(String(b.due_date || ""), locale(), {numeric: true, sensitivity: "base"}));
  view.innerHTML = `
    <section class="customer-rental-board">
      <div class="panel-head">
        <div>
          <p class="eyebrow">${t("app.eyebrow")}</p>
          <h2>${t("sections.my_rentals")}</h2>
        </div>
      </div>
      ${rentals.length ? `<div class="rental-card-grid">${rentals.map((rental) => renderCustomerRentalCard(rental)).join("")}</div>` : `<div class="empty">${t("empty.no_rentals")}</div>`}
    </section>
  `;
}

function renderCustomerRentalCard(rental) {
  return `
    <article class="rental-card">
      <div class="journey-head">
        <strong>${escapeHtml(rental.instrument_name || rental.instrument_id || "")}</strong>
        ${statusPill(rental.status || "active")}
      </div>
      <div class="rental-card-meta">
        <span>${escapeHtml(rental.instrument_type || "")}</span>
      </div>
      ${rental.note ? `<p>${escapeHtml(rental.note)}</p>` : ""}
      ${renderCustomerRentalJourney(rental)}
    </article>
  `;
}

function renderCustomerRentalJourney(rental) {
  const due = dateOrdinal(rental.due_date);
  const today = todayOrdinal();
  const daysUntilDue = due === null ? null : due - today;
  const dueClass = rental.return_date
    ? "is-done"
    : daysUntilDue === null
      ? "is-forever"
      : daysUntilDue < 0
        ? "is-overdue"
        : daysUntilDue <= 31
          ? "is-soon"
          : "is-current";
  const dueLabel = rental.due_date ? formatDate(rental.due_date) : t("fields.forever");
  return `<div class="mini-journey">
    <span class="is-done"><strong>${t("status.active")}</strong><small>${rental.start_date ? formatDate(rental.start_date) : ""}</small></span>
    <span class="${dueClass}"><strong>${t("table.due")}</strong><small>${escapeHtml(dueLabel)}</small></span>
    <span class="${rental.return_date ? "is-done" : ""}"><strong>${t("status.returned")}</strong><small>${rental.return_date ? formatDate(rental.return_date) : ""}</small></span>
  </div>`;
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
  const caps = capabilities();
  if (!caps.admin) {
    view.innerHTML = `<div class="empty">${t("tenant.locked")}</div>`;
    return;
  }
  const associationItems = filterAssociationItems(state.associations);
  const userItems = filterUserItems(state.users);
  const requestItems = filterUserItems(state.accessRequests);
  const detail = state.detail?.entity === "associations"
    ? renderAssociationDetail(state.detail.id)
    : state.detail?.entity === "user_access"
      ? renderUserDetail(state.detail.id)
      : "";
  view.innerHTML = `${renderToolbar("associations")}<div class="${detail ? "split-view" : ""}">
    <div class="admin-stack">
      ${caps.platform_admin ? `
      <section class="panel">
        <div class="panel-head">
          <h2>${t("sections.associations")}</h2>
        </div>
        ${renderAssociationTable(associationItems)}
      </section>
      ` : ""}
      <section class="panel">
        <div class="panel-head">
          <h2>${t("sections.access_requests")}</h2>
        </div>
        ${renderAccessRequestTable(requestItems)}
      </section>
      <section class="panel">
        <div class="panel-head">
          <h2>${t("sections.users")}</h2>
          <div class="panel-actions">
            ${caps.platform_admin ? `<button class="ghost-button" data-export-tenant-access>${t("actions.export_tenant_access")}</button>` : ""}
            <button class="primary-button" data-new-user>${t("actions.new_user")}</button>
          </div>
        </div>
        ${renderUserTable(userItems)}
      </section>
    </div>
    ${detail}
  </div>`;
}

function renderAccessRequestTable(items) {
  if (!items.length) return `<div class="empty">${t("empty.no_access_requests")}</div>`;
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>${t("fields.email")}</th><th>${t("labels.tenant")}</th><th>${t("table.status")}</th><th>${t("table.updated")}</th><th></th></tr></thead>
        <tbody>${items.map((item) => `
          <tr>
            <td data-label="${t("fields.email")}"><strong>${escapeHtml(item.email)}</strong></td>
            <td data-label="${t("labels.tenant")}">${escapeHtml(item.tenant_id)}</td>
            <td data-label="${t("table.status")}">${statusPill(item.status || "pending")}</td>
            <td data-label="${t("table.updated")}">${item.requested_at ? new Date(item.requested_at).toLocaleString(locale()) : ""}</td>
            <td data-label="${t("table.action")}"><div class="row-actions">
              <button class="primary-button" data-approve-request="${escapeHtml(item.id)}">${t("actions.approve")}</button>
              <button class="danger-button" data-deny-request="${escapeHtml(item.id)}">${t("actions.deny")}</button>
            </div></td>
          </tr>
        `).join("")}</tbody>
      </table>
    </div>
  `;
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
            <td data-label="${t("table.tenant")}"><strong>${escapeHtml(item.tenant_id)}</strong><div class="muted">${escapeHtml(item.short_name || "")}</div></td>
            <td data-label="${t("table.name")}">${escapeHtml(item.display_name)}</td>
            <td data-label="${t("table.status")}">${statusPill(item.status || "active")}</td>
            <td data-label="${t("table.region")}">${escapeHtml(item.region || "")}</td>
            <td data-label="Hitobito">${escapeHtml(item.hitobito_group_ref || "")}</td>
            <td data-label="${t("table.updated")}">${item.meta?.updated_at ? new Date(item.meta.updated_at).toLocaleString(locale()) : ""}</td>
            <td data-label="${t("table.action")}"><div class="row-actions">
              <button class="ghost-button" data-edit-association="${item.tenant_id}">${t("actions.edit")}</button>
              ${shouldShowTenantSwitcher() ? `<button class="primary-button" data-open-association="${item.tenant_id}">${t("actions.open")}</button>` : ""}
            </div></td>
          </tr>
          ${renderInlineDetail("associations", item.tenant_id, 7)}
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
            <td data-label="${t("fields.email")}"><strong>${escapeHtml(item.email)}</strong><div class="muted">${escapeHtml(item.display_name || item.id)}</div></td>
            <td data-label="${t("fields.global_role")}">${globalRolePill(item.global_role || "none")}</td>
            <td data-label="${t("fields.access_profile")}">${accessProfilePill(item.access_profile || "full")}</td>
            <td data-label="${t("fields.tenant_roles")}">${escapeHtml((item.tenant_roles || []).map((role) => `${role.tenant_id}:${role.role}`).join(", "))}</td>
            <td data-label="${t("table.status")}">${statusPill(item.status || "active")}</td>
            <td data-label="${t("table.action")}"><div class="row-actions">
              <button class="ghost-button" data-edit-user="${item.id}">${t("actions.edit")}</button>
              <button class="danger-button" data-delete-user="${item.id}">${t("actions.delete")}</button>
            </div></td>
          </tr>
          ${renderInlineDetail("user_access", item.id, 6)}
        `).join("")}</tbody>
      </table>
    </div>
  `;
}

function renderAssociationDetail(tenantId) {
  const item = state.associations.find((association) => association.tenant_id === tenantId);
  if (!item) return "";
  const canOpen = shouldShowTenantSwitcher();
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
        <div><dt>${t("fields.contact")}</dt><dd>${escapeHtml(item.contact || "")}</dd></div>
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

function renderAnyDetail(entity, id) {
  if (entity === "associations") return renderAssociationDetail(id);
  if (entity === "user_access") return renderUserDetail(id);
  if (entity === "history") return renderHistoryDetail(state.records.history.find((item) => item.id === id));
  return renderDetail(entity, id);
}

function detailCloseButton() {
  return `<button class="icon-button detail-close" data-close-detail aria-label="${escapeHtml(t("actions.close"))}" title="${escapeHtml(t("actions.close"))}"><span aria-hidden="true">&times;</span></button>`;
}

function renderInlineDetail(entity, id, colspan) {
  if (state.detail?.entity !== entity || state.detail?.id !== id) return "";
  const detail = renderAnyDetail(entity, id);
  if (!detail) return "";
  return `<tr class="inline-detail-row"><td colspan="${colspan}">${detail}</td></tr>`;
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
            <td data-label="${t("table.name")}"><strong>${escapeHtml(item.name)}</strong><div class="muted">${escapeHtml(item.brand)}</div></td>
            <td data-label="${t("table.type")}">${escapeHtml(item.type)}</td>
            <td data-label="${t("table.serial")}">${escapeHtml(item.serial)}</td>
            <td data-label="${t("table.condition")}">${conditionPill(item.service_condition || "good")}</td>
            <td data-label="${t("table.last_service")}">${formatDate(item.last_service_date)}</td>
            <td data-label="${t("table.next_service")}">${item.next_service_date ? `${formatDate(item.next_service_date)} ${serviceDuePill(item.service_due_status)}` : ""}</td>
            <td data-label="${t("table.status")}">${statusPill(item.status)}</td>
            <td data-label="${t("table.action")}"><div class="row-actions">
              ${caps.write ? `<button class="ghost-button" data-edit="instruments" data-id="${item.id}">${t("actions.edit")}</button>` : ""}
              ${caps.admin ? `<button class="danger-button" data-delete="instruments" data-id="${item.id}">${t("actions.delete")}</button>` : ""}
            </div></td>
          </tr>
          ${renderInlineDetail("instruments", item.id, 8)}
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
              <td data-label="${t("table.instrument")}"><strong>${escapeHtml(serviceInstrumentName(item))}</strong><div class="muted">${escapeHtml(item.job_type || "")}</div></td>
              <td data-label="${t("fields.service_date")}">${formatDate(item.service_date)}</td>
              <td data-label="${t("table.condition")}">${conditionPill(item.condition)}</td>
              <td data-label="${t("table.next_service")}">${item.next_service_date ? `${formatDate(item.next_service_date)} ${serviceDuePill(dueStatus)}` : ""}</td>
              <td data-label="${t("fields.provider")}">${escapeHtml(item.provider || "")}</td>
              <td data-label="${t("table.action")}"><div class="row-actions">
                ${caps.write ? `<button class="ghost-button" data-edit="service_records" data-id="${item.id}">${t("actions.edit")}</button>` : ""}
                ${caps.admin ? `<button class="danger-button" data-delete="service_records" data-id="${item.id}">${t("actions.delete")}</button>` : ""}
              </div></td>
            </tr>
            ${renderInlineDetail("service_records", item.id, 6)}
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
            <td data-label="${t("table.name")}"><strong>${escapeHtml(item.display_name)}</strong></td>
            <td data-label="${t("table.reference")}">${escapeHtml(item.member_ref)}</td>
            <td data-label="${t("table.contact")}">${escapeHtml(item.contact_hint)}</td>
            <td data-label="${t("table.status")}">${item.is_active ? statusPill("active") : statusPill("inactive")}</td>
            <td data-label="${t("table.action")}"><div class="row-actions">
              ${caps.write ? `<button class="ghost-button" data-edit="members" data-id="${item.id}">${t("actions.edit")}</button>` : ""}
              ${caps.admin ? `<button class="danger-button" data-delete="members" data-id="${item.id}">${t("actions.delete")}</button>` : ""}
            </div></td>
          </tr>
          ${renderInlineDetail("members", item.id, 5)}
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
            <td data-label="${t("table.instrument")}"><strong>${escapeHtml(item.instrument_name)}</strong><div class="muted">${escapeHtml(item.note)}</div></td>
            <td data-label="${t("table.member")}">${escapeHtml(item.member_name)}</td>
            <td data-label="${t("table.start")}">${formatDate(item.start_date)}</td>
            <td data-label="${t("table.due")}">${formatDate(item.due_date)}</td>
            <td data-label="${t("table.status")}">${statusPill(item.status)}</td>
            <td data-label="${t("table.action")}"><div class="row-actions">
              ${caps.write && item.status !== "returned" ? `<button class="primary-button" data-return="${item.id}">${t("actions.return")}</button>` : ""}
              ${compact ? "" : `${caps.write ? `<button class="ghost-button" data-edit="rentals" data-id="${item.id}">${t("actions.edit")}</button>` : ""}
              ${caps.admin ? `<button class="danger-button" data-delete="rentals" data-id="${item.id}">${t("actions.delete")}</button>` : ""}`}
            </div></td>
          </tr>
          ${renderInlineDetail("rentals", item.id, 6)}
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
                <td data-label="${t("table.when")}">${new Date(item.created_at).toLocaleString(locale())}</td>
                <td data-label="${t("table.action")}">${statusPill(item.action)}</td>
                <td data-label="${t("table.instrument")}">${escapeHtml(item.instrument_name)}</td>
                <td data-label="${t("table.member")}">${escapeHtml(item.member_name)}</td>
                <td data-label="${t("table.service")}">${renderHistoryServiceCell(item)}</td>
                <td data-label="${t("table.rental")}">${escapeHtml(item.rental_id)}</td>
              </tr>
              ${renderInlineDetail("history", item.id, 6)}
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
  formFields.innerHTML = schemas[entity].map(([name, label, type, required, span]) => renderField(name, label, type, required, span, record[name], record)).join("");
  dialog.showModal();
}

function renderField(name, label, type, required, span, value, record = {}) {
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
  if (type === "tenant_roles") {
    const roles = Array.isArray(value) && value.length ? value : [{tenant_id: "", role: "reader"}];
    return `<div class="field${full} tenant-role-field" data-tenant-roles-field>
      <label>${t(label)}</label>
      <div class="tenant-role-list">
        ${roles.map((role) => renderTenantRoleRow(role)).join("")}
      </div>
      <button type="button" class="ghost-button" data-add-tenant-role>${t("actions.add_tenant_role")}</button>
    </div>`;
  }
  if (type === "member_links") {
    const links = Array.isArray(value) && value.length ? value : [{tenant_id: state.tenant, member_id: ""}];
    return `<div class="field${full} tenant-role-field" data-member-links-field>
      <label>${t(label)}</label>
      <div class="tenant-role-list">
        ${links.map((link) => renderMemberLinkRow(link)).join("")}
      </div>
      <button type="button" class="ghost-button" data-add-member-link>${t("fields.member_links")}</button>
    </div>`;
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
  if (type === "email" && name === "access_email" && record.access_email_hash && !value) {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><input id="${name}" name="${name}" type="email" value="" placeholder="${escapeHtml(t("fields.access_email_configured"))}" aria-describedby="${name}Help" ${requiredAttr}><p id="${name}Help" class="muted">${t("fields.access_email_help")}</p></div>`;
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

function renderTenantRoleRow(role = {}) {
  const tenantId = role.tenant_id || "";
  const selectedRole = role.role || "reader";
  return `<div class="tenant-role-row">
    ${renderTenantSelect("tenant_roles_tenant_id", tenantId)}
    <select name="tenant_roles_role">
      ${["reader", "operator", "admin"].map((item) => `<option value="${item}" ${item === selectedRole ? "selected" : ""}>${t(`tenant_role.${item}`)}</option>`).join("")}
    </select>
    <button type="button" class="icon-button" data-remove-tenant-role title="${t("actions.delete")}" aria-label="${t("actions.delete")}">×</button>
  </div>`;
}

function renderMemberLinkRow(link = {}) {
  const tenantId = link.tenant_id || state.tenant;
  const memberId = link.member_id || "";
  return `<div class="tenant-role-row member-link-row">
    ${renderTenantSelect("member_links_tenant_id", tenantId)}
    ${renderMemberLinkSelect(memberId)}
    <button type="button" class="icon-button" data-remove-member-link title="${t("actions.delete")}" aria-label="${t("actions.delete")}">×</button>
  </div>`;
}

function renderTenantSelect(name, value) {
  const tenantIds = new Set([state.tenant, value, ...state.associations.map((item) => item.tenant_id)].filter(Boolean));
  return `<select name="${name}">
    <option value="">${t("select.placeholder")}</option>
    ${[...tenantIds].sort((a, b) => a.localeCompare(b, locale(), {numeric: true, sensitivity: "base"})).map((tenantId) => `<option value="${escapeHtml(tenantId)}" ${tenantId === value ? "selected" : ""}>${escapeHtml(tenantId)}</option>`).join("")}
  </select>`;
}

function renderMemberLinkSelect(value) {
  const members = state.records.members.filter((item) => item.is_active !== false || item.id === value);
  const hasCurrentValue = value && !members.some((item) => item.id === value);
  return `<select name="member_links_member_id">
    <option value="">${t("select.placeholder")}</option>
    ${hasCurrentValue ? `<option value="${escapeHtml(value)}" selected>${escapeHtml(value)}</option>` : ""}
    ${members.map((item) => `<option value="${item.id}" ${item.id === value ? "selected" : ""}>${escapeHtml(item.display_name)} (${escapeHtml(item.id)})</option>`).join("")}
  </select>`;
}

function singular(entity) {
  return entity === "members" ? t("entities.member") : entity === "rentals" ? t("entities.rental") : entity === "service_records" ? t("entities.service_record") : entity === "associations" ? t("entities.association") : entity === "user_access" ? t("entities.user_access") : t("entities.instrument");
}

function formPayload(form) {
  const payload = Object.fromEntries(new FormData(form).entries());
  const entity = form.dataset.entity;
  Object.keys(payload).forEach((key) => {
    if (payload[key] === "" && !shouldKeepEmptyField(entity, key)) delete payload[key];
  });
  if ("is_active" in payload) payload.is_active = payload.is_active === "true";
  if ("value_chf" in payload) payload.value_chf = Number(payload.value_chf);
  if ("cost_chf" in payload) payload.cost_chf = Number(payload.cost_chf);
  if ("purchase_year" in payload) payload.purchase_year = Number(payload.purchase_year);
  if (form.querySelector("[data-tenant-roles-field]")) {
    const tenantIds = [...form.querySelectorAll('[name="tenant_roles_tenant_id"]')].map((input) => input.value.trim().toLowerCase());
    const roles = [...form.querySelectorAll('[name="tenant_roles_role"]')].map((select) => select.value);
    payload.tenant_roles = tenantIds
      .map((tenantId, index) => tenantId ? {tenant_id: tenantId, role: roles[index] || "reader"} : null)
      .filter(Boolean);
    delete payload.tenant_roles_tenant_id;
    delete payload.tenant_roles_role;
  }
  if (form.querySelector("[data-member-links-field]")) {
    const tenantIds = [...form.querySelectorAll('[name="member_links_tenant_id"]')].map((input) => input.value.trim().toLowerCase());
    const memberIds = [...form.querySelectorAll('[name="member_links_member_id"]')].map((select) => select.value.trim());
    payload.member_links = tenantIds
      .map((tenantId, index) => tenantId && memberIds[index] ? {tenant_id: tenantId, member_id: memberIds[index]} : null)
      .filter(Boolean);
    delete payload.member_links_tenant_id;
    delete payload.member_links_member_id;
  }
  ["tenant_roles", "member_links"].forEach((key) => {
    if (key in payload && typeof payload[key] === "string") payload[key] = JSON.parse(payload[key] || "[]");
  });
  return payload;
}

function shouldKeepEmptyField(entity, key) {
  const nullableDateFields = {
    rentals: new Set(["due_date", "return_date"]),
    service_records: new Set(["next_service_date"])
  };
  return nullableDateFields[entity]?.has(key) || false;
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

messageClose?.addEventListener("click", () => {
  window.clearTimeout(showMessage.timer);
  message.hidden = true;
});

document.addEventListener("click", (event) => {
  if (!event.target.closest("[data-logout]")) return;
  window.location.assign("/cdn-cgi/access/logout");
});

view.addEventListener("input", (event) => {
  if (event.target.matches('[data-join-request] [name="tenant_id"]')) {
    updateJoinRequestSubmit(event.target.closest("[data-join-request]"));
    return;
  }
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
    if (target.dataset.addTenantRole !== undefined) {
      const list = target.closest("[data-tenant-roles-field]")?.querySelector(".tenant-role-list");
      if (list) list.insertAdjacentHTML("beforeend", renderTenantRoleRow());
      return;
    }
    if (target.dataset.removeTenantRole !== undefined) {
      const list = target.closest(".tenant-role-list");
      target.closest(".tenant-role-row")?.remove();
      if (list && !list.querySelector(".tenant-role-row")) {
        list.insertAdjacentHTML("beforeend", renderTenantRoleRow());
      }
      return;
    }
    if (target.dataset.addMemberLink !== undefined) {
      const list = target.closest("[data-member-links-field]")?.querySelector(".tenant-role-list");
      if (list) list.insertAdjacentHTML("beforeend", renderMemberLinkRow());
      return;
    }
    if (target.dataset.removeMemberLink !== undefined) {
      const list = target.closest(".tenant-role-list");
      target.closest(".tenant-role-row")?.remove();
      if (list && !list.querySelector(".tenant-role-row")) {
        list.insertAdjacentHTML("beforeend", renderMemberLinkRow());
      }
      return;
    }
    if (target.dataset.closeDetail !== undefined) {
      state.detail = null;
      render();
      return;
    }
    if (target.dataset.logout !== undefined) {
      window.location.assign("/cdn-cgi/access/logout");
      return;
    }
    if (target.dataset.authRetry !== undefined) {
      window.location.assign("/auth/login");
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
    if (target.dataset.approveRequest) {
      await approveAccessRequest(target.dataset.approveRequest);
      return;
    }
    if (target.dataset.denyRequest) {
      await denyAccessRequest(target.dataset.denyRequest);
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

view.addEventListener("submit", async (event) => {
  if (!event.target.matches("[data-join-request]")) return;
  event.preventDefault();
  const formData = new FormData(event.target);
  const email = formData.get("email")?.toString().trim().toLowerCase();
  const tenant = formData.get("tenant_id")?.toString().trim().toLowerCase();
  if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    showMessage(t("messages.invalid_email"), true);
    return;
  }
  if (!tenantPattern.test(tenant)) {
    showMessage(t("tenant.invalid"), true);
    return;
  }
  try {
    const result = await accessRequestApi({email, tenant_id: tenant});
    state.accessRequestResult = result.data;
    saveStoredAccessRequest(result.data);
    render();
    showMessage(t("messages.join_request_pending"));
  } catch (error) {
    showMessage(error.message, true);
  }
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

recordForm.addEventListener("click", (event) => {
  const target = event.target.closest("button");
  if (!target) return;
  if (target.dataset.addTenantRole !== undefined) {
    const list = target.closest("[data-tenant-roles-field]")?.querySelector(".tenant-role-list");
    if (list) list.insertAdjacentHTML("beforeend", renderTenantRoleRow());
  }
  if (target.dataset.removeTenantRole !== undefined) {
    const list = target.closest(".tenant-role-list");
    target.closest(".tenant-role-row")?.remove();
    if (list && !list.querySelector(".tenant-role-row")) {
      list.insertAdjacentHTML("beforeend", renderTenantRoleRow());
    }
  }
  if (target.dataset.addMemberLink !== undefined) {
    const list = target.closest("[data-member-links-field]")?.querySelector(".tenant-role-list");
    if (list) list.insertAdjacentHTML("beforeend", renderMemberLinkRow());
  }
  if (target.dataset.removeMemberLink !== undefined) {
    const list = target.closest(".tenant-role-list");
    target.closest(".tenant-role-row")?.remove();
    if (list && !list.querySelector(".tenant-role-row")) {
      list.insertAdjacentHTML("beforeend", renderMemberLinkRow());
    }
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

async function approveAccessRequest(id) {
  try {
    await adminApi(`/access-requests/${id}/approve`, {method: "POST", body: JSON.stringify({tenant_role: "reader"})});
    await loadData();
    showMessage(t("messages.access_request_approved"));
  } catch (error) {
    await handleMutationError(error);
  }
}

async function denyAccessRequest(id) {
  try {
    await adminApi(`/access-requests/${id}/deny`, {method: "POST", body: "{}"});
    await loadData();
    showMessage(t("messages.access_request_denied"));
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
  if (state.authStatus !== "signed_in") {
    window.location.assign("/auth/login");
    return;
  }
  loadData().catch((error) => showMessage(error.message, true));
});

saveTenant.addEventListener("click", () => {
  if (state.context?.tenant_locked && !shouldShowTenantSwitcher()) return;
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
  if (state.context?.tenant_locked && !shouldShowTenantSwitcher()) return;
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
  state.accessRequestResult = loadStoredAccessRequest();
  applyLanguage();
  render();
  let context;
  try {
    context = await apiContext();
  } catch (error) {
    state.authStatus = "signed_out";
    state.authReason = authReasonFromError(error);
    state.authEmail = authEmailFromError(error);
    state.authError = error.message || "";
    state.context = null;
    state.isLoading = false;
    render();
    return;
  }
  applyContext(context);
  try {
    await loadData();
    state.isLoading = false;
    render();
  } catch (error) {
    state.isLoading = false;
    render();
    showMessage(error.message, true);
  }
}

init().catch((error) => {
  state.isLoading = false;
  render();
  showMessage(error.message, true);
});
