# Spreadsheet import and export

Association administrators can open **Spreadsheet import / export** from Members or Instruments. The existing JSON utilities remain available for technical administration; the full tenant JSON import still replaces tenant records.

1. Download the CSV sample template (headers and one illustrative row), or export all current records as CSV.
2. Fill in the template in Excel, LibreOffice or Google Sheets. Remove the sample row and save as **CSV UTF-8**. Native `.xlsx` workbooks are not accepted. Files may contain up to 2,000 data rows and be up to 5 MB.
3. Choose the CSV. Check the suggested column matches, particularly when using a file with different headings. Unmatched columns are named and excluded from upload. Changing column matches rebuilds the preview from the original file, discarding preview edits.
4. Review the preview. Edit cells as plain text. Invalid rows are excluded until corrected; select or deselect valid rows individually or together. The preview shows whether each row adds or updates a record. Review pages contain 25 rows; selection and submission cover all pages.
5. Submit the selected valid rows. The result reports confirmed saves. After a failed request, refresh and compare existing records before importing again. Member requests run sequentially, so an import can be partially saved; failed writes are never automatically replayed.

## Fields and matching

Instrument columns: `name`, `serial`, `brand`, `type`, `description`, `value_chf`, `purchase_year`. A serial number is required. Existing instruments match serial numbers without case sensitivity; updates preserve local IDs and rental links. When the name is empty, a name is derived from brand, type and serial, consistent with the API.

Member columns: `id`, `display_name`, `given_name`, `family_name`, `member_ref`, `contact_hint`, `groups`, `is_active`. New members require a unique member reference. Existing members match the exact member reference or the ID from a member export. An ID unknown to the current association must be cleared to create a member. An empty display name is derived from given/family names. Groups use `|` as the separator. Active accepts `true` / `false`, `yes` / `no`, `ja` / `nein`, `1` / `0`, and active/inactive values.

An included column replaces its previous value, including empty cells. Omitted optional columns keep the current value on updates. CSV exports intentionally exclude tenant metadata, contact email/phone/address columns and member access settings. CSV exports are not complete backups; use the JSON tools for backup and restore.

Duplicate matching references within the file, ambiguous existing matches, invalid numbers/years/booleans and contact information in restricted text fields are flagged before submission. A row with a different cell count from its header needs explicit confirmation of its displayed cells; surplus cells are discarded. Numeric values support decimal comma and Swiss thousands apostrophes. Column matching recognizes API field names and common English/German headings, with manual matching available.

## Implementation

`public/record_transfer.js` parses, converts, validates and serializes CSV. `public/transfer_ui.js` keeps the editable draft in memory for the dialog lifetime. No file is sent to a server. Only selected valid records become JSON requests through the application's normal authenticated API client and revision checks:

- Instruments: existing `PUT /api/tid-{tenant}/instruments/import` merge endpoint.
- Members: existing `POST /api/tid-{tenant}/members` and `PUT /api/tid-{tenant}/members/{id}` CRUD endpoints. The Hitobito endpoint is reserved for Hitobito data because its conversion would rewrite member references.

CSV accepts comma, semicolon and tab separators, UTF-8 BOM, quoted/multiline cells and Excel `sep=` declarations. Exports use a BOM and CRLF; German exports use semicolons. Formula-like exported values are prefixed with an apostrophe and restored by this importer. There are no CDN dependencies or new backend endpoints.
