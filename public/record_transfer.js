// Spreadsheet conversion stays in the browser. Only explicitly supported fields leave it.
export const transferFields = {
  instruments: ["name", "serial", "brand", "type", "description", "value_chf", "purchase_year"],
  members: ["id", "display_name", "given_name", "family_name", "member_ref", "contact_hint", "groups", "is_active"]
};
export const transferSamples = {
  instruments: {name: "Clarinet", serial: "CL-001", brand: "Yamaha", type: "Clarinet", description: "Association instrument", value_chf: "850", purchase_year: "2022"},
  members: {id: "", display_name: "Alex Example", given_name: "Alex", family_name: "Example", member_ref: "member-001", contact_hint: "Via association office", groups: "Woodwinds|Youth", is_active: "true"}
};
const aliases = {
  name: ["instrument", "instrument name", "instrumentenname", "bezeichnung"], serial: ["serial number", "seriennummer"],
  brand: ["marke", "hersteller"], type: ["typ", "instrument type"], description: ["beschreibung"],
  value_chf: ["value chf", "wert chf", "wert"], purchase_year: ["purchase year", "kaufjahr"],
  display_name: ["display name", "full name", "anzeigename", "name"], given_name: ["first name", "firstname", "first_name", "vorname"],
  family_name: ["last name", "lastname", "last_name", "nachname"], member_ref: ["member ref", "member reference", "mitgliedsreferenz", "mitgliedsnummer"],
  contact_hint: ["contact hint", "kontakthinweis"], groups: ["gruppen"], is_active: ["active", "aktiv"]
};
export function suggestMapping(headers, entity) {
  return Object.fromEntries(transferFields[entity].map(field => [field, headers.findIndex(header => {
    const normalized = header.trim().toLowerCase();
    return normalized === field || (aliases[field] || []).includes(normalized);
  })]));
}

export function parseCsv(text) {
  if (text.length > 5 * 1024 * 1024) throw new Error("large");
  text = text.replace(/^\uFEFF/, "");
  // Count separators outside quotes in the header; supports Excel's optional sep= line.
  let delimiter;
  const separator = text.match(/^sep=([,;\t])\r?\n/i);
  if (separator) { delimiter = separator[1]; text = text.slice(separator[0].length); }
  if (!delimiter) {
    const counts = {",": 0, ";": 0, "\t": 0};
    let quoted = false;
    for (let i = 0; i < text.length; i += 1) {
      if (text[i] === '"') quoted = !quoted;
      if (!quoted && /[\r\n]/.test(text[i])) break;
      if (!quoted && text[i] in counts) counts[text[i]] += 1;
    }
    delimiter = Object.keys(counts).sort((a, b) => counts[b] - counts[a])[0];
  }
  const rows = [];
  let row = [], cell = "", quoted = false, closed = false;
  const pushCell = () => { row.push(cell); cell = ""; closed = false; };
  const pushRow = () => {
    pushCell();
    if (row.some(value => value.trim())) rows.push(row);
    row = [];
    if (rows.length > 2001) throw new Error("rows");
  };
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') { cell += '"'; i += 1; }
      else if (char === '"') { quoted = false; closed = true; }
      else cell += char;
    } else if (char === delimiter) pushCell();
    else if (char === "\r" || char === "\n") { pushRow(); if (char === "\r" && text[i + 1] === "\n") i += 1; }
    else if (char === '"' && !cell && !closed) quoted = true;
    else if (closed || char === '"') throw new Error("csv");
    else cell += char;
  }
  if (quoted) throw new Error("csv");
  pushRow();
  if (rows.length < 2) throw new Error("empty");
  const headers = rows.shift().map(value => value.trim());
  if (headers.some(value => !value) || new Set(headers.map(value => value.toLowerCase())).size !== headers.length) throw new Error("headers");
  return {headers, rows};
}

const formula = /^[\s\u0000-\u001f]*[=+@-]/;
const cellText = value => String(value ?? "").replace(/^'(?=[\s\u0000-\u001f]*[=+@-])/, "");
export function makeDraft(parsed, mapping, entity) {
  const columns = transferFields[entity].filter(field => mapping[field] >= 0);
  // Keep the minimum matching/name fields editable even when absent in the file.
  for (const field of entity === "members" ? ["display_name", "member_ref"] : ["name", "serial"]) if (!columns.includes(field)) columns.push(field);
  const rows = parsed.rows.map((values, index) => ({
    number: index + 2, selected: true, touched: false, done: false,
    presentFields: new Set(transferFields[entity].filter(field => mapping[field] >= 0)),
    editedFields: new Set(),
    shapeError: values.length !== parsed.headers.length,
    values: Object.fromEntries(columns.map(field => [field, cellText(values[mapping[field]])]))
  }));
  return {columns, rows};
}

export function validateDraft(draft, entity, existing = []) {
  const keys = new Map();
  for (const row of draft.rows) {
    row.errors = [];
    row.record = {};
    if (row.done) continue;
    if (row.shapeError) row.errors.push({field: "", code: "shape"});
    for (const [field, raw] of Object.entries(row.values)) {
      const value = raw.trim();
      if (!value && !row.presentFields.has(field) && !row.editedFields.has(field)) continue;
      row.record[field] = value;
      if (["display_name", "given_name", "family_name", "member_ref", "contact_hint", "description"].includes(field) && /[^@\s]+@[^@\s]+\.[^@\s]+/.test(value)) row.errors.push({field, code: "contact"});
      if (["display_name", "contact_hint", "description"].includes(field) && /(?=(?:\D*\d){7,})\+?[\d][\d\s()./-]{6,}\d/.test(value)) row.errors.push({field, code: "contact"});
      if (["value_chf", "purchase_year"].includes(field)) {
        const number = value.replace(/[’']/g, "").replace(",", ".");
        if (value && (!/^-?\d+(\.\d+)?$/.test(number) || !Number.isFinite(Number(number)) || (field === "purchase_year" && !/^\d{4}$/.test(number)))) row.errors.push({field, code: field === "purchase_year" ? "year" : "number"});
        row.record[field] = value ? Number(number) : null;
      }
      if (field === "groups") row.record[field] = value ? value.split("|").map(part => part.trim()).filter(Boolean) : [];
      if (field === "is_active") {
        if (value && !/^(true|false|yes|no|ja|nein|1|0|active|inactive|aktiv|inaktiv)$/i.test(value)) row.errors.push({field, code: "boolean"});
        row.record[field] = !/^(false|no|nein|0|inactive|inaktiv)$/i.test(value);
      }
    }
    const keyField = entity === "instruments" ? "serial" : "member_ref";
    const key = String(row.record[keyField] || "");
    const matches = existing.filter(record => (key && (entity === "instruments" ? String(record.serial).toLowerCase() === key.toLowerCase() : record.member_ref === key)) || (entity === "members" && row.record.id && record.id === row.record.id));
    row.targetId = matches[0]?.id || "";
    row.action = row.targetId ? "update" : "create";
    if (matches.length > 1) row.errors.push({field: keyField, code: "ambiguous"});
    if (entity === "members" && row.record.id && !existing.some(record => record.id === row.record.id)) row.errors.push({field: "id", code: "unknownId"});
    if (!key && !(entity === "members" && row.targetId)) row.errors.push({field: keyField, code: "required"});
    const effective = {...matches[0], ...row.record};
    const name = entity === "members" ? effective.display_name || [effective.given_name, effective.family_name].filter(Boolean).join(" ") : effective.name || [effective.brand, effective.type, effective.serial].filter(Boolean).join(" ");
    if (!name) row.errors.push({field: entity === "members" ? "display_name" : "name", code: "required"});
    if (entity === "members") { if ("display_name" in row.record || !row.targetId) row.record.display_name = name; delete row.record.id; }
    const identity = row.targetId || (entity === "instruments" ? key.toLowerCase() : key);
    if (identity) { const group = keys.get(identity) || []; group.push(row); keys.set(identity, group); }
  }
  for (const rows of keys.values()) if (rows.length > 1) for (const row of rows) row.errors.push({field: entity === "instruments" ? "serial" : "member_ref", code: "duplicate"});
  for (const row of draft.rows) if (!row.done && !row.touched) row.selected = !row.errors.length;
  return draft;
}

export function serializeCsv(entity, records, delimiter = ",") {
  const encode = value => {
    let text = Array.isArray(value) ? value.join("|") : String(value ?? "");
    if (formula.test(text)) text = `'${text}`;
    return `"${text.replaceAll('"', '""')}"`;
  };
  return "\uFEFF" + [transferFields[entity], ...records.map(record => transferFields[entity].map(field => record[field]))].map(row => row.map(encode).join(delimiter)).join("\r\n") + "\r\n";
}
