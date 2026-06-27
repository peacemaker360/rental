const state = {
  tenant: localStorage.getItem("rentalTenant") || "demo-association",
  lang: localStorage.getItem("rentalLang") || (navigator.language?.toLowerCase().startsWith("de") ? "de" : "en"),
  view: "dashboard",
  search: "",
  status: "all",
  records: {
    instruments: [],
    members: [],
    rentals: [],
    history: []
  },
  summary: {},
  meta: {revision: 0, updated_at: null},
  context: null
};

const viewTitle = document.querySelector("#viewTitle");
const view = document.querySelector("#view");
const message = document.querySelector("#message");
const primaryAction = document.querySelector("#primaryAction");
const seedButton = document.querySelector("#seedButton");
const exportButton = document.querySelector("#exportButton");
const importButton = document.querySelector("#importButton");
const importFile = document.querySelector("#importFile");
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
const languageButtons = document.querySelectorAll("[data-lang]");

const translations = {
  en: {
    "app.title": "Rental Desk",
    "app.eyebrow": "Instrument rental",
    "views.dashboard": "Dashboard",
    "views.instruments": "Instruments",
    "views.members": "Members",
    "views.rentals": "Rentals",
    "views.history": "History",
    "labels.tenant": "Tenant",
    "labels.language": "Language",
    "labels.revision": "Revision",
    "labels.updated_at": "Updated {date}",
    "tenant.title": "2-63 lowercase letters, numbers, hyphens, or underscores",
    "tenant.locked": "Tenant is provided by the signed-in context",
    "tenant.invalid": "Tenant id must use 2-63 lowercase letters, numbers, hyphens, or underscores",
    "actions.switch_tenant": "Switch tenant",
    "actions.load_demo": "Load Demo",
    "actions.export": "Export",
    "actions.import": "Import",
    "actions.refresh": "Refresh",
    "actions.cancel": "Cancel",
    "actions.close": "Close",
    "actions.save": "Save",
    "actions.edit": "Edit",
    "actions.delete": "Delete",
    "actions.return": "Return",
    "actions.view_all": "View All",
    "actions.history": "History",
    "actions.new_instruments": "New Instrument",
    "actions.new_members": "New Member",
    "actions.new_rentals": "New Rental",
    "actions.yes": "Yes",
    "actions.no": "No",
    "dialog.new": "New {entity}",
    "dialog.edit": "Edit {entity}",
    "entities.instrument": "Instrument",
    "entities.member": "Member",
    "entities.rental": "Rental",
    "entities.instruments": "instruments",
    "entities.members": "members",
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
    "fields.member_ref": "Member ref",
    "fields.contact_hint": "Contact hint",
    "fields.is_active": "Active",
    "fields.instrument_id": "Instrument",
    "fields.member_id": "Member",
    "fields.start_date": "Start date",
    "fields.due_date": "Due date",
    "fields.note": "Note",
    "table.name": "Name",
    "table.type": "Type",
    "table.serial": "Serial",
    "table.value": "Value",
    "table.status": "Status",
    "table.reference": "Reference",
    "table.contact": "Contact",
    "table.instrument": "Instrument",
    "table.member": "Member",
    "table.start": "Start",
    "table.due": "Due",
    "table.when": "When",
    "table.action": "Action",
    "table.rental": "Rental",
    "stats.instruments": "Instruments",
    "stats.available": "Available",
    "stats.members": "Members",
    "stats.active_rentals": "Active rentals",
    "stats.overdue": "Overdue",
    "sections.open_rentals": "Open rentals",
    "sections.attention": "Attention",
    "empty.no_overdue": "No overdue rentals",
    "empty.no_instruments": "No instruments",
    "empty.no_members": "No members",
    "empty.no_rentals": "No rentals",
    "empty.no_history": "No history",
    "search.placeholder": "Search {entity}",
    "select.placeholder": "Select...",
    "confirm.delete": "Delete this record?",
    "confirm.import": "Replace tenant \"{tenant}\" with records from this JSON file?",
    "messages.saved": "{entity} saved",
    "messages.deleted": "{entity} deleted",
    "messages.returned": "Rental returned",
    "messages.demo_loaded": "Demo data loaded",
    "messages.export_downloaded": "Tenant export downloaded",
    "messages.import_complete": "Import complete: {instruments} instruments, {members} members",
    "messages.revision_conflict": "This tenant changed in another session. The latest data is loaded; review and try again.",
    "status.all": "all",
    "status.available": "available",
    "status.rented": "rented",
    "status.active": "active",
    "status.overdue": "overdue",
    "status.returned": "returned",
    "status.inactive": "inactive",
    "status.created": "created",
    "status.updated": "updated",
    "status.deleted": "deleted",
    "status.imported": "imported"
  },
  de: {
    "app.title": "Verleihverwaltung",
    "app.eyebrow": "Instrumentenverleih",
    "views.dashboard": "Übersicht",
    "views.instruments": "Instrumente",
    "views.members": "Mitglieder",
    "views.rentals": "Ausleihen",
    "views.history": "Verlauf",
    "labels.tenant": "Mandant",
    "labels.language": "Sprache",
    "labels.revision": "Revision",
    "labels.updated_at": "Aktualisiert {date}",
    "tenant.title": "2-63 Kleinbuchstaben, Zahlen, Bindestriche oder Unterstriche",
    "tenant.locked": "Der Mandant wird durch die Anmeldung vorgegeben",
    "tenant.invalid": "Mandant muss aus 2-63 Kleinbuchstaben, Zahlen, Bindestrichen oder Unterstrichen bestehen",
    "actions.switch_tenant": "Mandant wechseln",
    "actions.load_demo": "Demo laden",
    "actions.export": "Export",
    "actions.import": "Import",
    "actions.refresh": "Aktualisieren",
    "actions.cancel": "Abbrechen",
    "actions.close": "Schliessen",
    "actions.save": "Speichern",
    "actions.edit": "Bearbeiten",
    "actions.delete": "Löschen",
    "actions.return": "Rückgabe",
    "actions.view_all": "Alle anzeigen",
    "actions.history": "Verlauf",
    "actions.new_instruments": "Neues Instrument",
    "actions.new_members": "Neues Mitglied",
    "actions.new_rentals": "Neue Ausleihe",
    "actions.yes": "Ja",
    "actions.no": "Nein",
    "dialog.new": "{entity} erstellen",
    "dialog.edit": "{entity} bearbeiten",
    "entities.instrument": "Instrument",
    "entities.member": "Mitglied",
    "entities.rental": "Ausleihe",
    "entities.instruments": "Instrumente",
    "entities.members": "Mitglieder",
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
    "fields.member_ref": "Mitgliedsreferenz",
    "fields.contact_hint": "Kontakthinweis",
    "fields.is_active": "Aktiv",
    "fields.instrument_id": "Instrument",
    "fields.member_id": "Mitglied",
    "fields.start_date": "Startdatum",
    "fields.due_date": "Fälligkeitsdatum",
    "fields.note": "Notiz",
    "table.name": "Name",
    "table.type": "Typ",
    "table.serial": "Seriennummer",
    "table.value": "Wert",
    "table.status": "Status",
    "table.reference": "Referenz",
    "table.contact": "Kontakt",
    "table.instrument": "Instrument",
    "table.member": "Mitglied",
    "table.start": "Start",
    "table.due": "Fällig",
    "table.when": "Zeitpunkt",
    "table.action": "Aktion",
    "table.rental": "Ausleihe",
    "stats.instruments": "Instrumente",
    "stats.available": "Verfügbar",
    "stats.members": "Mitglieder",
    "stats.active_rentals": "Aktive Ausleihen",
    "stats.overdue": "Überfällig",
    "sections.open_rentals": "Offene Ausleihen",
    "sections.attention": "Aufmerksamkeit",
    "empty.no_overdue": "Keine überfälligen Ausleihen",
    "empty.no_instruments": "Keine Instrumente",
    "empty.no_members": "Keine Mitglieder",
    "empty.no_rentals": "Keine Ausleihen",
    "empty.no_history": "Kein Verlauf",
    "search.placeholder": "{entity} suchen",
    "select.placeholder": "Auswählen...",
    "confirm.delete": "Diesen Eintrag löschen?",
    "confirm.import": "Mandant \"{tenant}\" durch die Einträge aus dieser JSON-Datei ersetzen?",
    "messages.saved": "{entity} gespeichert",
    "messages.deleted": "{entity} gelöscht",
    "messages.returned": "Ausleihe zurückgegeben",
    "messages.demo_loaded": "Demo-Daten geladen",
    "messages.export_downloaded": "Mandantenexport heruntergeladen",
    "messages.import_complete": "Import abgeschlossen: {instruments} Instrumente, {members} Mitglieder",
    "messages.revision_conflict": "Dieser Mandant wurde in einer anderen Sitzung geändert. Die aktuellen Daten sind geladen; bitte prüfen und erneut versuchen.",
    "status.all": "alle",
    "status.available": "verfügbar",
    "status.rented": "ausgeliehen",
    "status.active": "aktiv",
    "status.overdue": "überfällig",
    "status.returned": "zurückgegeben",
    "status.inactive": "inaktiv",
    "status.created": "erstellt",
    "status.updated": "aktualisiert",
    "status.deleted": "gelöscht",
    "status.imported": "importiert"
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
    ["instrument_id", "fields.instrument_id", "instrument", true],
    ["member_id", "fields.member_id", "member", true],
    ["start_date", "fields.start_date", "date", true],
    ["due_date", "fields.due_date", "date", false],
    ["note", "fields.note", "textarea", false, "full"]
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

function statusPill(status) {
  return `<span class="pill ${escapeHtml(status)}">${escapeHtml(t(`status.${status}`))}</span>`;
}

function capabilities() {
  return state.context?.capabilities || {read: true, write: true, admin: true};
}

async function loadData() {
  const [summary, instruments, members, rentals, history] = await Promise.all([
    api("/summary"),
    api("/instruments"),
    api("/members"),
    api("/rentals"),
    api("/history")
  ]);
  state.summary = summary;
  applyMeta(summary.meta);
  state.records = {
    instruments: instruments.data || [],
    members: members.data || [],
    rentals: rentals.data || [],
    history: history.data || []
  };
  render();
}

function render() {
  applyLanguage();
  viewTitle.textContent = t(`views.${state.view}`);
  tenantLabel.textContent = state.tenant;
  primaryAction.hidden = state.view === "history";
  primaryAction.textContent = state.view === "instruments" ? t("actions.new_instruments") : state.view === "members" ? t("actions.new_members") : t("actions.new_rentals");
  const capabilities = state.context?.capabilities || {write: true, admin: true};
  primaryAction.disabled = !capabilities.write;
  seedButton.disabled = !capabilities.admin;
  exportButton.disabled = !capabilities.admin;
  importButton.disabled = !capabilities.admin;

  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === state.view);
  });

  if (state.view === "dashboard") renderDashboard();
  if (state.view === "instruments") renderCollection("instruments");
  if (state.view === "members") renderCollection("members");
  if (state.view === "rentals") renderCollection("rentals");
  if (state.view === "history") renderHistory();
}

function renderDashboard() {
  const rentals = state.records.rentals.filter((rental) => rental.status !== "returned").slice(0, 6);
  const overdue = state.records.rentals.filter((rental) => rental.status === "overdue");
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
          <button class="ghost-button" data-jump="history">${t("actions.history")}</button>
        </div>
        ${overdue.length ? renderRentalTable(overdue, true) : `<div class="empty">${t("empty.no_overdue")}</div>`}
      </section>
    </div>
  `;
}

function renderStats() {
  const stats = [
    [t("stats.instruments"), state.summary.instruments || 0],
    [t("stats.available"), state.summary.available_instruments || 0],
    [t("stats.members"), state.summary.members || 0],
    [t("stats.active_rentals"), state.summary.active_rentals || 0],
    [t("stats.overdue"), state.summary.overdue_rentals || 0]
  ];
  return `<section class="stats-grid">${stats.map(([label, value]) => `
    <div class="stat"><span>${label}</span><strong>${value}</strong></div>
  `).join("")}</section>`;
}

function renderToolbar(entity) {
  const showStatus = entity === "instruments" || entity === "rentals";
  return `
    <div class="toolbar">
      <input data-search placeholder="${escapeHtml(t("search.placeholder", {entity: t(`entities.${entity}`)}))}" value="${escapeHtml(state.search)}">
      ${showStatus ? `<div class="segmented">
        ${["all", "available", "rented", "active", "overdue", "returned"].map((status) => `
          <button data-status="${status}" class="${state.status === status ? "is-active" : ""}">${t(`status.${status}`)}</button>
        `).join("")}
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
    filtered = filtered.filter((item) => item.status === state.status);
  }
  return filtered;
}

function renderCollection(entity) {
  const items = filterItems(state.records[entity]);
  const table = entity === "instruments"
    ? renderInstrumentTable(items)
    : entity === "members"
      ? renderMemberTable(items)
      : renderRentalTable(items);
  view.innerHTML = `${renderToolbar(entity)}${table}`;
}

function renderInstrumentTable(items) {
  if (!items.length) return `<div class="empty">${t("empty.no_instruments")}</div>`;
  const caps = capabilities();
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>${t("table.name")}</th><th>${t("table.type")}</th><th>${t("table.serial")}</th><th>${t("table.value")}</th><th>${t("table.status")}</th><th></th></tr></thead>
        <tbody>${items.map((item) => `
          <tr>
            <td><strong>${escapeHtml(item.name)}</strong><div class="muted">${escapeHtml(item.brand)}</div></td>
            <td>${escapeHtml(item.type)}</td>
            <td>${escapeHtml(item.serial)}</td>
            <td>${item.value_chf ? `CHF ${Number(item.value_chf).toFixed(0)}` : ""}</td>
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

function renderMemberTable(items) {
  if (!items.length) return `<div class="empty">${t("empty.no_members")}</div>`;
  const caps = capabilities();
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>${t("table.name")}</th><th>${t("table.reference")}</th><th>${t("table.contact")}</th><th>${t("table.status")}</th><th></th></tr></thead>
        <tbody>${items.map((item) => `
          <tr>
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

function renderRentalTable(items, compact = false) {
  if (!items.length) return `<div class="empty">${t("empty.no_rentals")}</div>`;
  const caps = capabilities();
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>${t("table.instrument")}</th><th>${t("table.member")}</th><th>${t("table.start")}</th><th>${t("table.due")}</th><th>${t("table.status")}</th><th></th></tr></thead>
        <tbody>${items.map((item) => `
          <tr>
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

function renderHistory() {
  const items = filterItems(state.records.history);
  if (!items.length) {
    view.innerHTML = `${renderToolbar("history")}<div class="empty">${t("empty.no_history")}</div>`;
    return;
  }
  view.innerHTML = `${renderToolbar("history")}
    <div class="table-wrap">
      <table>
        <thead><tr><th>${t("table.when")}</th><th>${t("table.action")}</th><th>${t("table.instrument")}</th><th>${t("table.member")}</th><th>${t("table.rental")}</th></tr></thead>
        <tbody>${items.map((item) => `
          <tr>
            <td>${new Date(item.created_at).toLocaleString(locale())}</td>
            <td>${statusPill(item.action)}</td>
            <td>${escapeHtml(item.instrument_name)}</td>
            <td>${escapeHtml(item.member_name)}</td>
            <td>${escapeHtml(item.rental_id)}</td>
          </tr>
        `).join("")}</tbody>
      </table>
    </div>
  `;
}

function openDialog(entity, record = {}) {
  dialogTitle.textContent = record.id ? t("dialog.edit", {entity: singular(entity)}) : t("dialog.new", {entity: singular(entity)});
  recordForm.dataset.entity = entity;
  recordForm.dataset.id = record.id || "";
  formFields.innerHTML = schemas[entity].map(([name, label, type, required, span]) => renderField(name, label, type, required, span, record[name])).join("");
  dialog.showModal();
}

function renderField(name, label, type, required, span, value) {
  const requiredAttr = required ? "required" : "";
  const full = span === "full" ? " full" : "";
  if (type === "textarea") {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><textarea id="${name}" name="${name}" ${requiredAttr}>${escapeHtml(value)}</textarea></div>`;
  }
  if (type === "checkbox") {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><select id="${name}" name="${name}"><option value="true" ${value !== false ? "selected" : ""}>${t("actions.yes")}</option><option value="false" ${value === false ? "selected" : ""}>${t("actions.no")}</option></select></div>`;
  }
  if (type === "instrument") {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><select id="${name}" name="${name}" ${requiredAttr}>
      <option value="">${t("select.placeholder")}</option>
      ${state.records.instruments.map((item) => `<option value="${item.id}" ${item.id === value ? "selected" : ""}>${escapeHtml(item.name)} (${t(`status.${item.status}`)})</option>`).join("")}
    </select></div>`;
  }
  if (type === "member") {
    return `<div class="field${full}"><label for="${name}">${t(label)}</label><select id="${name}" name="${name}" ${requiredAttr}>
      <option value="">${t("select.placeholder")}</option>
      ${state.records.members.filter((item) => item.is_active).map((item) => `<option value="${item.id}" ${item.id === value ? "selected" : ""}>${escapeHtml(item.display_name)}</option>`).join("")}
    </select></div>`;
  }
  return `<div class="field${full}"><label for="${name}">${t(label)}</label><input id="${name}" name="${name}" type="${type}" value="${escapeHtml(value)}" ${requiredAttr}></div>`;
}

function singular(entity) {
  return entity === "members" ? t("entities.member") : entity === "rentals" ? t("entities.rental") : t("entities.instrument");
}

function formPayload(form) {
  const payload = Object.fromEntries(new FormData(form).entries());
  Object.keys(payload).forEach((key) => {
    if (payload[key] === "") delete payload[key];
  });
  if ("is_active" in payload) payload.is_active = payload.is_active === "true";
  if ("value_chf" in payload) payload.value_chf = Number(payload.value_chf);
  if ("purchase_year" in payload) payload.purchase_year = Number(payload.purchase_year);
  return payload;
}

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    state.view = button.dataset.view;
    state.search = "";
    state.status = "all";
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
});

view.addEventListener("click", async (event) => {
  const target = event.target.closest("button");
  if (!target) return;
  if (target.dataset.status) {
    state.status = target.dataset.status;
    render();
  }
  if (target.dataset.jump) {
    state.view = target.dataset.jump;
    state.search = "";
    state.status = "all";
    render();
  }
  if (target.dataset.edit) {
    const entity = target.dataset.edit;
    const record = state.records[entity].find((item) => item.id === target.dataset.id);
    openDialog(entity, record);
  }
  if (target.dataset.delete) {
    await removeRecord(target.dataset.delete, target.dataset.id);
  }
  if (target.dataset.return) {
    await returnRecord(target.dataset.return);
  }
});

primaryAction.addEventListener("click", () => {
  const entity = state.view === "instruments" ? "instruments" : state.view === "members" ? "members" : "rentals";
  openDialog(entity, {start_date: new Date().toISOString().slice(0, 10), is_active: true});
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
    if (id) {
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
    const payload = JSON.parse(await file.text());
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
