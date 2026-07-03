## Rental Desk

This repository has been refactored from a Flask/SQL app into a Cloudflare-only
serverless app:

- `public/` contains the static frontend.
- `worker/` contains the Python Worker API.
- Cloudflare KV stores JSON records instead of SQL tables.
- Legacy Flask, SQL migration, Azure deployment files, and Azure GitHub Actions
  workflows have been removed from the active tree; migration helpers live under
  `scripts/`.

### Local Cloudflare App

Install the Worker tooling. The Python Worker runs through Cloudflare's
`pywrangler` package via `uv`; the JavaScript Wrangler package is still used for
KV namespace commands and the optional Access front door. Keep `uv.lock`
committed so `uv run pywrangler ...` uses the same Python Worker tooling in
local debug and deployment.

```bash
npm install
uv sync
```

Run the static frontend and Python Worker locally:

```bash
npm run dev
```

Open the local `pywrangler` URL, then use **Load Demo** once for the current tenant.
The default tenant is `demo-association`; switching the tenant changes the KV key
prefix used by the API.

If Node/Wrangler is not available, run the same static frontend and API contract
against local JSON files with:

```bash
python3 scripts/local_dev_server.py
```

That server opens on `http://127.0.0.1:8787` and persists local development data
under `.data/local-kv/`. Local debug state, Wrangler state, Python bytecode
caches, Python virtual environments, `node_modules/`, and `.env` stay ignored
and are checked by preflight so generated artifacts do not become part of the
Cloudflare source tree.
The local static fallback is constrained to `public/` with pathlib containment
checks, so deep links work without allowing path traversal during debugging.

The Python local server defaults to permissive local admin context. To debug the
deployed signed-context flow without Cloudflare in front of it, run:

```bash
RENTAL_CONTEXT_SECRET=dev-secret \
  python3 scripts/local_dev_server.py --auth-mode signed
```

Then generate matching request headers with:

```bash
RENTAL_CONTEXT_SECRET=dev-secret python3 scripts/sign_context.py \
  --tenant demo-association \
  --actor debug-operator \
  --role operator
```

Run backend domain tests:

```bash
npm test
```

Without Node, the equivalent test command is:

```bash
python3 -m unittest discover -s tests
```

Run the local static/API smoke test:

```bash
python3 scripts/smoke_local.py --verbose
```

It starts the Python local server on an ephemeral localhost port, uses temporary
JSON storage, and exercises the frontend assets plus core API flows.
Add `--signed` to also verify the local server in deployed-style signed tenant
context mode:

```bash
python3 scripts/smoke_local.py --signed --verbose
```

The same signed smoke path is available through `npm run smoke:signed`.

Run the local refactor/deployment-shape preflight:

```bash
npm run preflight
```

The `Cloudflare refactor CI` GitHub Actions workflow runs the same local
validation path on pushes and pull requests: Python unit tests, signed smoke,
Cloudflare preflight with frontdoor checks, and frontend/frontdoor JavaScript
syntax checks through `npm run check:js`.
Preflight also checks that the static shell declares a same-origin Content
Security Policy and `no-referrer` metadata, keeping browser-side tenant data
handling aligned with the low-PII model.

For production readiness, run the strict preflight after replacing placeholder
Cloudflare IDs and Access values:

```bash
npm run preflight:deploy
npm run preflight:frontdoor
```

### Language

The static UI includes an `EN` / `DE` switch in the sidebar. The selected
language is stored in the browser with `localStorage` and applies to navigation,
forms, tables, statuses, confirmations, and operational messages.

Create Cloudflare KV namespaces before deploying:

```bash
npm run kv:create
npm run kv:create-preview
```

Copy the generated IDs into `wrangler.toml`, replacing the placeholder
`id` and `preview_id` values.

Before deploying, `npm run preflight:deploy` must pass. It catches placeholder
KV IDs, missing static assets, Python Worker tooling drift, accidentally
restored legacy Flask/SQL/Azure files or workflows, and legacy runtime imports
or dependency declarations in active Worker/static code.

Deploy the Python Worker with:

```bash
npm run deploy
```

### Cloudflare Worker Shape

The Worker exposes tenant-scoped endpoints:

- `GET /api/health`
- `GET /api/context`
- `GET|POST /api/admin/associations`
- `GET|PUT /api/admin/associations/{tenant}`
- `GET|POST /api/admin/users`
- `GET /api/admin/users/export/tenant-access`
- `GET|PUT|DELETE /api/admin/users/{user_id}`
- `POST /api/{tenant}/bootstrap`
- `GET /api/{tenant}/summary`
- `GET /api/{tenant}/export`
- `PUT /api/{tenant}/import`
- `PUT /api/{tenant}/members/import/hitobito`
- `GET /api/{tenant}/instruments/export`
- `PUT /api/{tenant}/instruments/import`
- `GET|POST /api/{tenant}/instruments`
- `GET|PUT|DELETE /api/{tenant}/instruments/{id}`
- `GET|POST /api/{tenant}/members`
- `GET|PUT|DELETE /api/{tenant}/members/{id}`
- `GET|POST /api/{tenant}/rentals`
- `GET|PUT|DELETE /api/{tenant}/rentals/{id}`
- `POST /api/{tenant}/rentals/{id}/return`
- `GET|POST /api/{tenant}/service_records`
- `GET|PUT|DELETE /api/{tenant}/service_records/{id}`
- `GET /api/{tenant}/history`

Collection reads accept `search=` and `status=` query parameters. Instrument and
service-record status filters also understand service conditions such as `watch`
or `needs_service`.
Delete responses keep the compatibility `deleted` id and also return the deleted
record as `data`; instrument deletes include cascaded service records when any
were removed with the instrument.

Empty API paths such as `/api` and `/api/` return JSON `404` responses in both
the Worker and local server, keeping API debugging separate from the static
frontend fallback.

KV keys are prefixed with `tenant:{tenant_id}:...`, so tenant isolation is part
of every storage operation from the first refactor slice.

### Tenant Context

`wrangler.toml` sets `RENTAL_AUTH_MODE=auto`.

- Localhost requests use local admin context for debugging.
- Deployed requests require a signed tenant context header by default.
- The route tenant and signed tenant id must match.
- The frontend calls `GET /api/context` at startup. In deployed mode the tenant
  is locked to that signed context; in local mode the tenant switcher remains
  available.

Set the signing secret before deploying:

```bash
npx wrangler secret put RENTAL_CONTEXT_SECRET
```

The signed context uses two edge-injected headers:

- `x-rental-context`: base64url JSON containing `tenant_id`, `actor_id`, `role`,
  and optionally `issued_at`, `user_email`, `member_id`, and `access_profile`
- `x-rental-context-signature`: HMAC-SHA256 of `x-rental-context` using
  `RENTAL_CONTEXT_SECRET`

Tenant roles are `viewer`, `operator`, and `admin`. Signed contexts with an
`issued_at` older than one hour are rejected. This keeps tenant identity out of
browser storage and avoids storing member/user PII in rental records. `actor_id`
must be an opaque identifier such as `access:abc123` or `roster-user-42`; email
addresses and phone-like values are rejected because actor ids are written to
history records. `access_profile=basic` is read-only and scopes reads to the
member's own linked members, rentals, and rented instruments.

`frontdoor/access_context_worker.js` is an optional Cloudflare Access front door
that validates the Access JWT, maps the authenticated email to a user access
profile through `TENANT_ACCESS_KV`, strips identity headers, and injects the
signed tenant context for the Python Worker. It still accepts legacy
`principal:{access_sub}` assignments as a migration fallback. See
`docs/cloudflare-access-frontdoor.md`.

Prepare low-PII `TENANT_ACCESS_KV` seed data with:

```bash
npm run tenant-access -- assignments.json --format summary
npm run tenant-access -- assignments.json --format kv-bulk --output /tmp/tenant-access-kv.json
```

The assignment helper now accepts user-profile rows keyed by the Cloudflare
Access email claim. Profiles can set `global_role`, per-tenant `tenant_roles`,
`member_links`, and an `access_profile` of `full` or `basic`. Legacy opaque
subject assignments are still supported; those legacy rows reject
email/name/phone/address fields and block email or phone-like principal values.

For manual API debugging, generate matching headers with:

```bash
RENTAL_CONTEXT_SECRET=dev-secret python3 scripts/sign_context.py \
  --tenant demo-association \
  --actor debug-operator \
  --role operator
```

`RENTAL_AUTH_MODE=header` still exists for setups where another trusted
Cloudflare edge component overwrites `x-rental-tenant-id`, `x-rental-actor-id`,
and `x-rental-role`. Do not expose raw header mode directly to browsers.

Tenant ids must be stable slugs: 2-63 lowercase letters, numbers, hyphens, or
underscores, starting with a letter or number. The same format is enforced for
API routes, trusted headers, KV key prefixes, local JSON filenames, and the local
UI tenant switcher.

### Admin Center

Admins can use the `Admin Center` view to manage association records and user
access profiles across tenants. The association registry stores operational
details only: tenant slug, display name, short name, status, region, locale,
contact reference, Hitobito group reference, inventory reference, and notes. It
intentionally avoids email and phone fields; use references to the association
roster or Hitobito instead. Association and user rows open drilldowns with
operational state, tenant roles, and member links. In local/debug mode, admins
can open an association from that view to switch the current tenant.

User access profiles identify users by the email loaded from Cloudflare Access,
then configure global reader/operator/admin/platform-admin roles, per-tenant
reader/operator/admin roles, optional tenant/member links, and the read-only
`basic` profile for users who should only see their own related rentals and
instruments. Optional user labels are operational display text only and reject
contact-like values; the Access email is the only user identifier stored for
frontdoor authentication.
Tenant data mutations such as bootstrap, imports, and CRUD writes automatically
create a default registry entry when one is missing, so newly onboarded
associations appear in the Admin Center without a separate setup step. Existing
registry details are preserved unless edited through the Admin Center or an
import file explicitly includes `display_name` or `association_name` metadata.

In deployed signed/header modes, the Admin Center is platform-scoped: the
authenticated context must have role `admin` and tenant id `platform-admin`.
Tenant admins can still administer records inside their own association tenant,
but they cannot list or edit the cross-tenant association registry.

### Backup And Migration

The static UI has **Export** and **Import** controls in the top bar. Export
downloads one tenant as a JSON package. Import replaces the current tenant with a
validated JSON package. The **Hitobito** control imports members from a Hitobito
JSON/JSON:API export and merges them into the current tenant without replacing
instruments or rentals. In the **Instruments** view, **Export Inventory** and
**Import Inventory** handle instrument-only JSON handovers; imports merge by
serial number and preserve local instrument ids so rentals and service records
stay attached.

Exports include instruments, low-PII members, rentals, rental and service
history, and instrument service records. Keep these workflows as first-class
features during future cleanup:

- instrument import/export via `GET /api/{tenant}/instruments/export` and
  `PUT /api/{tenant}/instruments/import` for association inventory handover
- member import from Hitobito via `PUT /api/{tenant}/members/import/hitobito`,
  mapped to low-PII members with stable `member_ref` values like
  `hitobito:{id}`
- tenant JSON import/export for backup and migration dry runs

The tenant import path accepts only the new low-PII schema. It rejects common
legacy PII fields such as `email`, `phone`, `address`, and `birthdate`, so old
Flask data should be transformed before import instead of copied directly.
Hitobito import also omits email, phone, address, and birthday data; contact
details stay in Hitobito and the rental app stores only display names, groups,
active state, and the stable external reference. Imported history actor labels
must also be opaque and must not contain email addresses or phone numbers.
The static UI preflights tenant and instrument imports for blocked contact field
names plus contact-like values in instrument descriptions, notes, service
providers, member references, member hints, names, and history actors; the
Worker still performs the authoritative validation. The UI also catches invalid
JSON files before upload, so a broken import file does not trigger a tenant
write attempt. CRUD forms use the same client-side check for obvious
contact-like values before saving.

Transform a legacy Flask-style export into the new package format:

```bash
python3 scripts/migrate_legacy.py \
  --tenant demo-association \
  --legacy-json tests/fixtures/legacy_export.json \
  --output /tmp/rental-import.json
```

The transformer copies instruments and rentals, maps legacy customers to
low-PII members, and records which contact fields were intentionally omitted.
Legacy rental descriptions that contain email addresses or phone-like values are
omitted from rental notes and counted in the migration report, keeping the
generated package importable under the new PII rules. Legacy instrument
descriptions with contact-like values are omitted the same way.

### Tenant Revisions

Tenant write operations update lightweight metadata with a monotonically
increasing `revision` and `updated_at` timestamp. `GET /api/context`,
`GET /api/{tenant}/summary`, collection responses, write responses, and exports
include this metadata as `meta`. The local JSON runner stores the same metadata
next to tenant records.

The static frontend sends `x-rental-expected-revision` on write operations. If
the tenant changed after the UI loaded, the API returns `409` with the current
metadata instead of silently overwriting newer data. This is an optimistic guard
for operator workflows; KV still does not provide SQL-style transactions.

### Instrument Service Records

Instruments can have service records with service date, next service date,
condition, job type, provider, cost, and notes. The static UI opens drilldowns
from instrument rows and from the standalone Service list, visualizing rental
and service events as a journey.
`GET /api/{tenant}/service_records` and detail reads hydrate each service record
with the instrument name, serial number, and next-service due status for direct
API debugging and exports from client tools.
Upcoming or overdue service dates contribute to service attention alongside the
current condition. Current conditions are `good`, `watch`, `needs_service`,
`in_service`, and `retired`. Service provider and note fields reject email
addresses and phone-like values because service changes are copied into the
shared history journey.
The instrument toolbar can filter by rental status, service condition, and
upcoming or overdue service dates. Member lists can also filter active and
inactive members, keeping the top-bar controls useful for daily operations.
Rental forms offer available instruments by default while preserving the
currently selected instrument on edits; service forms allow any instrument so
maintenance can be tracked even when an item is rented, in service, or retired.
When an admin deletes an instrument, attached service records are removed with
it, but deletion events are still written to history so the maintenance journey
does not disappear silently.

### PII Direction

The new member model avoids storing email and phone numbers by default. It keeps
only an operational display name, optional roster reference, optional roster
note (`contact_hint` internally), and active flag. Member writes reject
email/phone/address-style fields, email-looking member references, and
phone-looking roster notes. Association registry names, references, and notes
also reject contact-like values. Rental notes and service provider/notes reject
email addresses and phone-like values because those fields can be copied into
history. Instrument descriptions also reject contact-like values. If a future
integration needs contact details, prefer a reference to the association's source
system over copying PII into KV. The UI mirrors these checks for friendlier
operator feedback, but the Worker remains the enforcement point.

API JSON responses from both the Worker and the Python local server are marked
`Cache-Control: no-store` with `X-Content-Type-Options: nosniff` and
`Referrer-Policy: no-referrer`, so tenant records and admin payloads are not
intentionally cached by the browser while operators work. The API does not emit
wildcard CORS origins; the static frontend and Worker are expected to run
same-origin, with the Access front door handling deployed authentication.
Unexpected server failures return a generic `unexpected error` response instead
of echoing internal exception details across tenant boundaries.
