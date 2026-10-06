import {transferFields, transferSamples, parseCsv, suggestMapping, makeDraft, validateDraft, serializeCsv} from "./record_transfer.js";

const copy = {
  en: {
    title: "Spreadsheet import & export", prepare: "Choose a file", review: "Review & submit", done: "Result",
    intro: "Use a CSV file from Excel, LibreOffice or Google Sheets. Your file stays in this browser until you submit selected rows.",
    template: "Download sample template", export: "Export all records as CSV", file: "Choose CSV file", help: "Fill in the template, remove the example row, then save as CSV (UTF-8). Excel workbooks (.xlsx) must first be saved as CSV. Maximum 2,000 rows / 5 MB.",
    rulesMembers: "Members match by member reference or exported ID. Use a unique member reference for new members. Groups use | between names; active uses true / false. Contact details and access settings are excluded.",
    rulesInstruments: "Instruments match by serial number. Matching records are updated; other records are added. Existing rentals stay linked. Leave out a column to keep its existing value; an empty cell clears that field.",
    rulesTitle: "How records are matched and updated",
    rules: "An included column replaces its current value, including empty cells. Rows needing attention are skipped until fixed. Nothing is deleted.",
    resetMapping: "Changing column matches rebuilds the preview from your file and discards cell edits and row selections. Reset the preview?",
    columns: "Match spreadsheet columns", columnHelp: "Check the suggested matches. Unmatched columns are ignored and never uploaded. Changing matches resets edits and row selections.", ignore: "Not in file", ignored: "Ignored columns", none: "None", preview: "Review these rows", back: "Choose another file", close: "Close", select: "Select all valid rows", deselect: "Deselect all", submit: "Submit {count} selected rows", busy: "Submitting… {count} saved", summary: "{selected} selected · {create} new · {update} updates · {invalid} need attention", row: "Row", include: "Include row {row}", status: "Review", create: "Add", update: "Update", saved: "Saved", valid: "Ready", fix: "Needs attention", selected: "Selected rows only will be uploaded.",
    required: "Required", number: "Enter a number, e.g. 850 or 850.50", year: "Enter a four-digit year", boolean: "Use true / false (or yes / no)", contact: "Remove email addresses or phone numbers", duplicate: "Repeated reference in this file; give each row its own reference", ambiguous: "Several existing records match; fix the reference or ID", unknownId: "Unknown ID; clear it to add a new member", shape: "Cell count differs from the header. Check displayed values; extra cells are excluded.", acceptShape: "Use displayed cells", csv: "This CSV has broken quotes. Save it again as CSV (UTF-8).", headers: "Each column needs a unique, non-empty header.", empty: "Include a header and at least one data row.", large: "Choose a file smaller than 5 MB.", rows: "Split the file into batches of at most 2,000 rows.", extension: "Choose a .csv file. In Excel, use Save As → CSV UTF-8.", mapping: "Assign each file column to only one field.",
    complete: "{count} rows saved. Unselected rows and rows needing attention were not uploaded.", stopped: "{count} rows confirmed saved. Submission stopped: {error}", recovery: "The remaining rows were not confirmed. Close this flow and refresh the records before importing again; a failed request may already have saved. Compare the records first.", refresh: "Records were saved, but the list could not be refreshed. Close and use Refresh.", previous: "Previous rows", next: "Next rows", page: "Rows {from}–{to} of {total}", stale: "Your association or access changed. Close this flow and reopen it from the current records."
  },
  de: {
    title: "Tabellen importieren & exportieren", prepare: "Datei auswählen", review: "Prüfen & übernehmen", done: "Ergebnis",
    intro: "Verwende eine CSV-Datei aus Excel, LibreOffice oder Google Sheets. Die Datei bleibt in diesem Browser, bis du die ausgewählten Zeilen übernimmst.",
    template: "Mustervorlage herunterladen", export: "Alle Einträge als CSV exportieren", file: "CSV-Datei auswählen", help: "Vorlage ausfüllen, Beispielzeile entfernen und als CSV (UTF-8) speichern. Excel-Dateien (.xlsx) zuerst als CSV speichern. Maximal 2.000 Zeilen / 5 MB.",
    rulesMembers: "Mitglieder werden über die Mitgliedsreferenz oder exportierte ID zugeordnet. Für neue Mitglieder eine eindeutige Referenz verwenden. Gruppen mit | trennen; aktiv mit true / false angeben. Kontaktdaten und Zugangseinstellungen werden ausgeschlossen.",
    rulesInstruments: "Instrumente werden über die Seriennummer zugeordnet. Treffer werden aktualisiert, andere Einträge hinzugefügt. Bestehende Ausleihen bleiben verknüpft. Eine fehlende Spalte behält den bisherigen Wert; eine leere Zelle löscht ihn.",
    rulesTitle: "So werden Einträge zugeordnet und aktualisiert",
    rules: "Eine enthaltene Spalte ersetzt den bisherigen Wert, auch bei leeren Zellen. Fehlerhafte Zeilen werden bis zur Korrektur übersprungen. Es wird nichts gelöscht.",
    resetMapping: "Eine neue Spaltenzuordnung erstellt die Vorschau erneut aus der Datei und verwirft Zellkorrekturen und Zeilenauswahl. Vorschau zurücksetzen?",
    columns: "Tabellenspalten zuordnen", columnHelp: "Prüfe die vorgeschlagenen Zuordnungen. Nicht zugeordnete Spalten werden ignoriert und niemals hochgeladen. Neue Zuordnungen setzen Korrekturen und Zeilenauswahl zurück.", ignore: "Nicht in Datei", ignored: "Ignorierte Spalten", none: "Keine", preview: "Zeilen prüfen", back: "Andere Datei auswählen", close: "Schliessen", select: "Alle gültigen Zeilen auswählen", deselect: "Alle abwählen", submit: "{count} ausgewählte Zeilen übernehmen", busy: "Übernahme läuft… {count} gespeichert", summary: "{selected} ausgewählt · {create} neu · {update} Aktualisierungen · {invalid} zu prüfen", row: "Zeile", include: "Zeile {row} auswählen", status: "Prüfung", create: "Hinzufügen", update: "Aktualisieren", saved: "Gespeichert", valid: "Bereit", fix: "Korrektur nötig", selected: "Nur ausgewählte Zeilen werden hochgeladen.",
    required: "Pflichtfeld", number: "Zahl eingeben, z. B. 850 oder 850,50", year: "Vierstelliges Jahr eingeben", boolean: "true / false (oder ja / nein) verwenden", contact: "E-Mail-Adressen oder Telefonnummern entfernen", duplicate: "Referenz mehrfach in Datei; jede Zeile braucht eine eigene Referenz", ambiguous: "Mehrere Einträge passen; Referenz oder ID korrigieren", unknownId: "Unbekannte ID; für ein neues Mitglied leeren", shape: "Zellenanzahl passt nicht zum Kopf. Angezeigte Werte prüfen; zusätzliche Zellen werden ausgeschlossen.", acceptShape: "Angezeigte Zellen verwenden", csv: "Die CSV enthält fehlerhafte Anführungszeichen. Erneut als CSV (UTF-8) speichern.", headers: "Jede Spalte braucht eine eindeutige, nicht leere Überschrift.", empty: "Eine Kopfzeile und mindestens eine Datenzeile sind nötig.", large: "Eine Datei kleiner als 5 MB auswählen.", rows: "Datei in höchstens 2.000 Zeilen pro Import aufteilen.", extension: "Eine .csv-Datei auswählen. In Excel: Speichern unter → CSV UTF-8.", mapping: "Jede Dateispalte nur einem Feld zuordnen.",
    complete: "{count} Zeilen gespeichert. Abgewählte und fehlerhafte Zeilen wurden nicht hochgeladen.", stopped: "{count} Zeilen bestätigt gespeichert. Übernahme angehalten: {error}", recovery: "Die übrigen Zeilen wurden nicht bestätigt. Diesen Ablauf schliessen und Einträge aktualisieren, bevor du erneut importierst; eine fehlgeschlagene Anfrage könnte bereits gespeichert sein. Zuerst die Einträge vergleichen.", refresh: "Einträge gespeichert, aber die Liste konnte nicht aktualisiert werden. Schliessen und Aktualisieren verwenden.", previous: "Vorherige Zeilen", next: "Nächste Zeilen", page: "Zeilen {from}–{to} von {total}", stale: "Verein oder Zugriff hat sich geändert. Diesen Ablauf schliessen und bei den aktuellen Einträgen erneut öffnen."
  }
};
const escape = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");

export function openRecordTransfer({entity, tenant, mode = "import", lang, records, label, isCurrent, submit, refresh}) {
  const words = copy[lang] || copy.en;
  const text = (key, values = {}) => Object.entries(values).reduce((value, [name, replacement]) => value.replaceAll(`{${name}}`, replacement), words[key] || key);
  const fieldLabel = field => field === "id" ? "ID" : label(field);
  let parsed, mapping, draft, busy = false, finished = false, page = 0, error = "", count = 0;
  const modal = document.createElement("dialog");
  modal.className = "record-dialog transfer-dialog";
  modal.setAttribute("aria-labelledby", "transferTitle");
  const download = (template) => {
    const csv = serializeCsv(entity, template ? [transferSamples[entity]] : records, lang === "de" ? ";" : ",");
    const url = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `rental-${tenant}-${entity}-${template ? "template" : new Date().toISOString().slice(0, 10)}.csv`;
    document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  if (mode === "export") {
    if (isCurrent()) download(false);
    return null;
  }
  document.body.append(modal);
  const button = (action, title, disabled = false, primary = false) => `<button type="button" data-transfer-action="${action}" class="${primary ? "primary-button" : "ghost-button"}" ${disabled ? "disabled" : ""}>${escape(title)}</button>`;
  function render() {
    const active = finished ? 2 : draft ? 1 : 0;
    modal.innerHTML = `<div class="dialog-head"><h2 id="transferTitle">${escape(text("title"))} · ${escape(label(entity))}</h2>${button("close", text("close"), busy)}</div>
      <ol class="transfer-steps">${["prepare", "review", "done"].map((step, index) => `<li ${index === active ? 'aria-current="step"' : ""}>${escape(text(step))}</li>`).join("")}</ol>
      <p class="transfer-context">${escape(tenant)}</p>
      <div class="transfer-error" role="alert" tabindex="-1" ${error ? "" : "hidden"}>${escape(error)}</div>
      ${draft ? reviewHtml() : `<p>${escape(text("intro"))}</p><div class="transfer-actions">${button("template", text("template"))}${button("export", text("export"))}</div><p>${escape(text("help"))}</p><details class="transfer-rules"><summary>${escape(text("rulesTitle"))}</summary><p>${escape(text(entity === "members" ? "rulesMembers" : "rulesInstruments"))}</p><p>${escape(text("rules"))}</p></details><label class="transfer-file">${escape(text("file"))}<input type="file" accept=".csv,text/csv" data-transfer-file aria-describedby="transferFileHelp"></label><p id="transferFileHelp" class="muted">CSV · UTF-8</p>`}`;
    modal.setAttribute("aria-busy", String(busy));
  }
  function reviewHtml() {
    validateDraft(draft, entity, records);
    const ready = draft.rows.filter(row => !row.done && !row.errors.length && row.selected);
    const invalid = draft.rows.filter(row => !row.done && row.errors.length).length;
    const summary = text("summary", {selected: ready.length, create: ready.filter(row => row.action === "create").length, update: ready.filter(row => row.action === "update").length, invalid});
    const assigned = new Set(Object.values(mapping).filter(index => index >= 0));
    const ignored = parsed.headers.filter((_, index) => !assigned.has(index));
    const slice = draft.rows.slice(page * 25, (page + 1) * 25);
    return `${!finished ? `<details class="transfer-mapping"><summary>${escape(text("columns"))}</summary><p>${escape(text("columnHelp"))}</p><div class="transfer-mapping-grid">${transferFields[entity].map(field => `<label>${escape(fieldLabel(field))}<select data-transfer-map="${field}" ${busy ? "disabled" : ""}><option value="-1">${escape(text("ignore"))}</option>${parsed.headers.map((header, index) => `<option value="${index}" ${mapping[field] === index ? "selected" : ""}>${escape(header)}</option>`).join("")}</select></label>`).join("")}</div></details><p class="muted">${escape(text("ignored"))}: ${escape(ignored.join(", ") || text("none"))}</p><details class="transfer-rules"><summary>${escape(text("rulesTitle"))}</summary><p>${escape(text(entity === "members" ? "rulesMembers" : "rulesInstruments"))}</p><p>${escape(text("rules"))}</p></details>` : ""}
      <h3>${escape(text(finished ? "done" : "preview"))}</h3><p data-transfer-summary role="status">${escape(finished ? text("complete", {count}) : busy ? text("busy", {count}) : summary)}</p>
      <div class="transfer-actions">${!finished ? button("select", text("select"), busy) + button("deselect", text("deselect"), busy) : ""}</div>
      <div class="table-wrap transfer-table"><table><thead><tr><th>${escape(text("row"))}</th><th>${escape(text("status"))}</th>${draft.columns.map(field => `<th scope="col">${escape(fieldLabel(field))}</th>`).join("")}</tr></thead><tbody>${slice.map(row => `<tr data-transfer-row="${row.number}"><td data-label="${escape(text("row"))}"><label><input type="checkbox" data-transfer-select="${row.number}" aria-label="${escape(text("include", {row: row.number}))}" ${row.selected && !row.done ? "checked" : ""} ${busy || finished || row.done || row.errors.length ? "disabled" : ""}> ${row.number}</label></td><td class="transfer-row-status" data-label="${escape(text("status"))}"><div>${row.done ? escape(text("saved")) : `<strong>${escape(text(row.errors.length ? "fix" : row.action))}</strong><div data-row-errors>${errorHtml(row)}</div>`}</div></td>${draft.columns.map(field => `<td data-label="${escape(fieldLabel(field))}"><input type="text" autocomplete="off" data-transfer-cell="${field}" data-row="${row.number}" aria-label="${escape(fieldLabel(field))} · ${escape(text("row"))} ${row.number}" value="${escape(row.values[field])}" ${row.errors.some(issue => issue.field === field) ? 'aria-invalid="true"' : ""} aria-describedby="transferErrors${row.number}" ${busy || finished || row.done ? "disabled" : ""}></td>`).join("")}</tr>`).join("")}</tbody></table></div>
      <div class="transfer-pagination">${button("previous", text("previous"), busy || page === 0)}<span>${escape(text("page", {from: page * 25 + 1, to: Math.min((page + 1) * 25, draft.rows.length), total: draft.rows.length}))}</span>${button("next", text("next"), busy || (page + 1) * 25 >= draft.rows.length)}</div>
      <div class="dialog-actions">${!finished ? button("back", text("back"), busy) + button("submit", busy ? text("busy", {count}) : text("submit", {count: ready.length}), busy || !ready.length, true) : button("close", text("close"), false, true)}</div>`;
  }
  function errorHtml(row) {
    return `<ul id="transferErrors${row.number}" class="transfer-issues">${row.errors.map(issue => `<li>${issue.field ? escape(fieldLabel(issue.field)) + ": " : ""}${escape(text(issue.code))}</li>`).join("")}</ul>${row.shapeError ? button(`shape:${row.number}`, text("acceptShape"), busy || finished) : ""}`;
  }
  function revalidate() {
    validateDraft(draft, entity, records);
    // Preserve the focused text input and caret while updating every dependent row.
    for (const row of draft.rows) {
      const tr = modal.querySelector(`[data-transfer-row="${row.number}"]`);
      if (!tr) continue;
      const checkbox = tr.querySelector("[data-transfer-select]");
      checkbox.checked = row.selected && !row.done;
      checkbox.disabled = busy || finished || row.done || row.errors.length > 0;
      tr.querySelector(".transfer-row-status").innerHTML = `<div><strong>${escape(text(row.errors.length ? "fix" : row.action))}</strong><div data-row-errors>${errorHtml(row)}</div></div>`;
      tr.querySelectorAll("[data-transfer-cell]").forEach(input => input.setAttribute("aria-invalid", String(row.errors.some(issue => issue.field === input.dataset.transferCell))));
    }
    const ready = draft.rows.filter(row => row.selected && !row.errors.length && !row.done);
    modal.querySelector("[data-transfer-summary]").textContent = text("summary", {selected: ready.length, create: ready.filter(row => row.action === "create").length, update: ready.filter(row => row.action === "update").length, invalid: draft.rows.filter(row => row.errors.length && !row.done).length});
    const submitButton = modal.querySelector('[data-transfer-action="submit"]');
    const assignments = Object.values(mapping).filter(index => index >= 0);
    submitButton.disabled = !ready.length || new Set(assignments).size !== assignments.length;
    submitButton.textContent = text("submit", {count: ready.length});
  }
  modal.addEventListener("input", event => {
    if (busy || finished || !event.target.dataset.transferCell) return;
    const row = draft.rows.find(item => item.number === Number(event.target.dataset.row));
    row.values[event.target.dataset.transferCell] = event.target.value;
    row.editedFields.add(event.target.dataset.transferCell);
    revalidate();
  });
  modal.addEventListener("change", async event => {
    if (busy || finished) return;
    if (event.target.matches("[data-transfer-file]")) {
      const file = event.target.files?.[0];
      if (!file) return;
      try {
        if (!/\.csv$/i.test(file.name)) throw new Error("extension");
        if (file.size > 5 * 1024 * 1024) throw new Error("large");
        parsed = parseCsv(await file.text());
        if (!modal.open) return;
        mapping = suggestMapping(parsed.headers, entity);
        draft = makeDraft(parsed, mapping, entity); error = ""; page = 0;
        render(); modal.querySelector("h3").setAttribute("tabindex", "-1"); modal.querySelector("h3").focus();
      } catch (problem) { error = text(problem.message in words ? problem.message : "csv"); render(); modal.querySelector("[role=alert]").focus(); }
    } else if (event.target.dataset.transferMap) {
      if (draft.rows.some(row => row.editedFields.size || row.touched) && !window.confirm(text("resetMapping"))) {
        event.target.value = String(mapping[event.target.dataset.transferMap]);
        return;
      }
      mapping[event.target.dataset.transferMap] = Number(event.target.value);
      const values = Object.values(mapping).filter(index => index >= 0);
      if (new Set(values).size !== values.length) { error = text("mapping"); render(); modal.querySelector('[data-transfer-action="submit"]').disabled = true; return; }
      error = ""; draft = makeDraft(parsed, mapping, entity); page = 0; render(); modal.querySelector("details").open = true;
    } else if (event.target.dataset.transferSelect) {
      const row = draft.rows.find(item => item.number === Number(event.target.dataset.transferSelect));
      row.selected = event.target.checked; row.touched = true; revalidate();
    }
  });
  modal.addEventListener("click", async event => {
    const action = event.target.closest("[data-transfer-action]")?.dataset.transferAction;
    if (!action || busy) return;
    if (action === "close") { modal.close(); return; }
    if (!isCurrent()) { error = text("stale"); finished = true; render(); return; }
    if (action === "template" || action === "export") { download(action === "template"); return; }
    if (action === "back") { draft = null; parsed = null; error = ""; render(); return; }
    if (action === "previous" || action === "next") { page += action === "next" ? 1 : -1; render(); return; }
    if (action.startsWith("shape:")) { draft.rows.find(row => row.number === Number(action.split(":")[1])).shapeError = false; revalidate(); return; }
    if (action === "select" || action === "deselect") { for (const row of draft.rows) { row.selected = action === "select" && !row.errors.length && !row.done; row.touched = true; } revalidate(); return; }
    if (action !== "submit" || finished) return;
    const assignments = Object.values(mapping).filter(index => index >= 0);
    if (new Set(assignments).size !== assignments.length) return;
    validateDraft(draft, entity, records);
    const selected = draft.rows.filter(row => row.selected && !row.errors.length && !row.done);
    if (!selected.length) return;
    busy = true; error = ""; render();
    try {
      await submit(selected, row => { row.done = true; row.selected = false; count += 1; const status = modal.querySelector("[data-transfer-summary]"); if (status) status.textContent = text("busy", {count}); });
      finished = true;
    } catch (problem) {
      finished = true;
      error = text("stopped", {count, error: problem.message}) + " " + text("recovery");
    } finally {
      busy = false;
      try { if (isCurrent()) await refresh(); } catch { error += " " + text("refresh"); }
      if (!modal.open) return;
      render();
      modal.querySelector(error ? "[role=alert]" : '[data-transfer-action="close"]').focus();
    }
  });
  modal.addEventListener("cancel", event => { if (busy) event.preventDefault(); });
  modal.addEventListener("close", () => { draft = null; parsed = null; modal.remove(); }, {once: true});
  render(); modal.showModal();
  return modal;
}
