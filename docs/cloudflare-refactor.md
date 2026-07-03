# Cloudflare Refactor Notes

## Current Slice

The new implementation keeps the app's main character: operational CRUD for
instruments, members, rentals, returns, and rental history.

The legacy Flask app, SQL migrations, Azure deployment files, and Azure GitHub
Actions workflows have been removed from the active tree. The Cloudflare path
lives in:

- `public/` for the static frontend
- `worker/` for the Python Worker backend
- `tests/` for domain behavior tests
- `wrangler.toml` for Cloudflare bindings and static assets

## Storage Model

Cloudflare KV is eventually consistent and key-value oriented, so the first data
model favors small JSON records and explicit per-tenant indexes:

```text
tenant:{tenant_id}:index:instruments
tenant:{tenant_id}:index:members
tenant:{tenant_id}:index:rentals
tenant:{tenant_id}:index:service_records
tenant:{tenant_id}:index:history
tenant:{tenant_id}:instruments:{instrument_id}
tenant:{tenant_id}:members:{member_id}
tenant:{tenant_id}:rentals:{rental_id}
tenant:{tenant_id}:service_records:{service_record_id}
tenant:{tenant_id}:history:{history_id}
```

Each record also contains `tenant_id`. That is redundant with the key prefix, but
it makes exports, audits, and future migrations easier.

When a tenant dataset is saved, the KV repository compares the previous per-entity
index with the new one and deletes record keys that are no longer indexed. This
keeps delete/import operations from leaving stale member or rental records behind
in KV.

Every tenant save also updates `tenant:{tenant_id}:meta` with a monotonically
increasing `revision` and `updated_at` timestamp. API responses include this
metadata as `meta` on context, summary, collection, write, import, and export
responses. This is not a full compare-and-swap conflict control for KV, but it
gives operators and future clients a concrete dataset version to display,
export, and reason about.

Mutating requests may send `x-rental-expected-revision`. When present, the API
compares it with the current tenant metadata before applying the write. A stale
revision returns `409` plus the current `meta`, and the static frontend refreshes
the tenant data before asking the operator to retry. This provides optimistic
write protection for common two-tab or two-operator conflicts while keeping the
storage model KV-native.

Collection reads accept `search=` and `status=` query parameters. Instrument and
service-record collections share the UI's service filter semantics, so direct
API callers can filter by conditions such as `watch` or `needs_service` as well
as normal rental/member statuses.
Delete responses return both the compatibility `deleted` id and the deleted
record as `data`. When deleting an instrument cascades service records, the
response includes those removed service records under `cascaded.service_records`.

## Backup And Import

Admin users can export and import tenant data:

```text
GET /api/{tenant}/export
PUT /api/{tenant}/import
GET /api/{tenant}/instruments/export
PUT /api/{tenant}/instruments/import
PUT /api/{tenant}/members/import/hitobito
```

The Worker and local JSON server keep `/api` and `/api/` inside the JSON API
boundary and return `404` instead of falling back to the static frontend.

Export returns a versioned package:

```json
{
  "schema": "association-rental",
  "version": 1,
  "tenant_id": "example-association",
  "exported_at": "2026-06-26T00:00:00+00:00",
  "records": {
    "instruments": [],
    "members": [],
    "rentals": [],
    "service_records": [],
    "history": []
  },
  "summary": {}
}
```

Import validates through the same domain normalizers used by CRUD writes,
rewrites records to the route tenant, and rejects blocked legacy PII fields such
as `email`, `phone`, `address`, and `birthdate`. Import currently replaces the
tenant dataset, which is simple and predictable for backups and migration dry
runs. Imported history actor labels also pass through the opaque actor check so
old exports cannot reintroduce email addresses or phone numbers through audit
metadata.
The static UI also preflights tenant and instrument import files for blocked
contact field names plus contact-like values in instrument descriptions, notes,
service providers, member references, member hints, names, and history actors.
CRUD forms use the same client-side check for obvious contact-like values before
saving. That is an operator aid; the Worker remains the authoritative validation
layer.

Instrument inventory import/export is a narrower handover workflow for
association inventory lists. Export returns only instrument records. Import
accepts a plain list, `{ "instruments": [] }`, `{ "records": { "instruments":
[] } }`, or JSON:API-style `{ "data": [] }` entries, then merges by serial
number. Existing local instrument ids are preserved so rentals, service records,
and history keep pointing at the same instrument.

Hitobito member import is additive. It accepts a plain list, a `{ "people": [] }`
/ `{ "members": [] }` payload, or JSON:API-style `{ "data": [] }` entries. It
maps people into members using `member_ref = hitobito:{id}`, imports display
name, optional given/family names, group labels, and active state, and omits
email, phone, address, and birthday fields. Repeated imports update existing
members by `member_ref` while preserving the local member id.

## Legacy Migration

Use `scripts/migrate_legacy.py` to convert old Flask data into the same package
format accepted by `/api/{tenant}/import`:

```bash
python3 scripts/migrate_legacy.py \
  --tenant demo-association \
  --legacy-json tests/fixtures/legacy_export.json \
  --output /tmp/rental-import.json
```

The supported JSON shape is:

```json
{
  "instruments": [],
  "customers": [],
  "rentals": []
}
```

`customers` may also be named `members`. The transformer keeps display names,
member references, groups, instruments, rentals, and rental dates. It does not
copy legacy contact fields such as email or phone into the new package; instead
it adds a migration report that counts omitted fields without making those fields
part of the importable records. Legacy rental descriptions that contain email
addresses or phone-like values are omitted from rental notes and counted in the
same report, so generated packages remain importable under the new note rules.
Legacy instrument descriptions with contact-like values are omitted the same way.

The script also accepts the legacy instrument and rental CSV exports:

```bash
python3 scripts/migrate_legacy.py \
  --tenant demo-association \
  --instruments-csv legacy_instruments.csv \
  --members-json legacy_members.json \
  --rentals-csv legacy_rentals.csv \
  --output /tmp/rental-import.json
```

## Domain Rules Preserved

- Instrument availability is computed from active rentals.
- An instrument cannot be rented twice while an active rental exists.
- Returning a rental sets `return_date` and releases the instrument.
- Members and instruments with active rentals cannot be deleted.
- Rental and service history is append-only from the UI/API perspective.
- Instrument service records track condition, service jobs, next service dates,
  providers, costs, and notes without storing member PII, and service changes
  are visible in both the standalone Service list and the shared history view.
  Clickable service rows open a drilldown with the instrument's maintenance
  journey. Service collection and detail API reads hydrate instrument name,
  instrument serial, and next-service due status for direct debugging and future
  clients. Service provider and note fields reject email addresses and
  phone-like values because those values would be copied into service history.
- Instrument list filters include rental status, service condition, and due or
  overdue service dates; member filters include active and inactive states.
- Deleting an instrument removes its attached service records but writes service
  deletion events to history, preserving the maintenance audit journey.

## Special Workflows To Preserve

- Instrument import/export through `/api/{tenant}/instruments/export` and
  `/api/{tenant}/instruments/import` for inventory migration and association
  handover.
- Member import from Hitobito through `/api/{tenant}/members/import/hitobito`,
  mapped into low-PII members using `member_ref`, groups, and active state
  instead of copying email/phone/address/birthday data.
- Tenant JSON export/import for backup, dry-run migration, and support.
- Service record export/import so maintenance history and planned service dates
  follow instruments.

## PII Boundaries

The legacy `Customer` model stores email and phone. The Worker `member` model
does not. It stores:

- `display_name`
- `member_ref`
- `contact_hint`
- `groups`
- `is_active`

`contact_hint` is presented in the UI as a roster note. For production, keep
authoritative contact details in the association's member system and store only
an external reference or short operational note here. Member CRUD rejects
email/phone/address-style fields, email-looking member references, and
phone-looking roster notes instead of silently dropping them. Association
registry display names, short names, reference fields, and notes also reject
contact-like values so operators get immediate feedback before contact PII is
copied into KV.
Rental notes and service provider/notes reject email addresses and phone-like
values because they can be copied into tenant history.
Instrument descriptions also reject contact-like values.
The UI mirrors these checks for friendlier operator feedback, but the Worker
remains the enforcement point.

Worker and local JSON API responses set `Cache-Control: no-store`, `Pragma:
no-cache`, `Referrer-Policy: no-referrer`, and `X-Content-Type-Options:
nosniff`. Static frontend assets can still be cached normally, but tenant data,
exports, imports, and admin-center payloads are treated as non-cacheable API
traffic in both deployed and local-debug runtimes. API responses do not emit a
wildcard CORS origin; the static frontend and Worker are expected to be served
same-origin, with the Cloudflare Access front door providing deployed auth.

## Multi-Tenancy

The tenant is currently selected in the UI and included in every API path:

```text
/api/{tenant}/...
```

Before offering this to other associations, tenant identity should move from a
free text UI field to an authenticated context, for example a Cloudflare Access
claim, a Workers Auth provider claim, or a signed session. The storage prefix can
remain the same.

The Worker now has the first part of that shape. `RENTAL_AUTH_MODE=auto` uses
local admin context on localhost and requires a signed tenant context on
deployed hosts:

```text
x-rental-context
x-rental-context-signature
```

`x-rental-context` is base64url JSON with `tenant_id`, `actor_id`, `role`, and
optionally `issued_at`, `user_email`, `member_id`, and `access_profile`.
`x-rental-context-signature` is an HMAC-SHA256 signature over that encoded
context using the `RENTAL_CONTEXT_SECRET` Worker secret. The API rejects
requests when the signed tenant does not match the tenant in the route, when the
role is not `viewer`, `operator`, or `admin`, or when an `issued_at` timestamp
is older than one hour. `actor_id` is copied into rental and service history, so
it must be opaque and must not look like an email address or phone number. Write
operations require `operator` or `admin`; demo bootstrap and delete operations
require `admin`. `access_profile=basic` is always read-only and scopes list and
detail reads to the user's linked member record, rentals, and rented
instruments.

`frontdoor/access_context_worker.js` is a deployable Cloudflare Access front
door for this shape. It validates `Cf-Access-Jwt-Assertion` or the
`CF_Authorization` cookie against the Access JWKS, looks up `user:{email}` in
`TENANT_ACCESS_KV`, signs the tenant context, and forwards to the Python Worker
through a service binding. The legacy `principal:{access_jwt_sub}` mapping is
still accepted as a migration fallback. The details live in
`docs/cloudflare-access-frontdoor.md`.

For manual API debugging, `scripts/sign_context.py` prints matching signed
headers from a tenant, actor, role, and `RENTAL_CONTEXT_SECRET`.

The local Python runner can enforce the same signed context without Wrangler or
the Access front door:

```bash
RENTAL_CONTEXT_SECRET=dev-secret \
  python3 scripts/local_dev_server.py --auth-mode signed
```

Use `scripts/sign_context.py` with the same secret to generate request headers
for curl, HTTP clients, or focused frontend/API debugging. The default local
server mode remains `local`, which keeps fast admin debugging available.

For production access assignment seeding, `scripts/tenant_access_assignments.py`
validates a JSON assignment file and renders either Wrangler commands or a KV
bulk JSON file for `TENANT_ACCESS_KV`. User-profile rows are stored under
`user:{email}` because Cloudflare Access supplies email as the stable user
identifier for this app. They can carry global roles, per-tenant roles,
tenant/member links, and `full` or `basic` access profiles. Legacy rows stored
under `principal:{access_jwt_sub}` remain low-PII and reject
email/name/phone/address fields plus email or phone-like principal and actor
values.

The older `RENTAL_AUTH_MODE=header` path is still available for deliberately
trusted Cloudflare edge chains that overwrite:

```text
x-rental-tenant-id
x-rental-actor-id
x-rental-role
```

Do not expose raw header mode directly to browsers. Use it only behind a
Cloudflare component that authenticates the user and replaces those headers.

The frontend asks `GET /api/context` before loading tenant records. The response
includes `tenant_id`, `role`, `tenant_locked`, and capability flags. When
`tenant_locked` is true, the UI disables tenant switching and uses the trusted
tenant id from the response. Local development reports an unlocked admin context
so manual tenant switching remains easy.

Tenant ids are intentionally constrained to a safe slug format:

```text
^[a-z0-9][a-z0-9_-]{1,62}$
```

That keeps route tenants, trusted headers, KV key prefixes, and local JSON
filenames aligned.

## Association Registry

The admin center uses `/api/admin/associations` to list and edit association
details across tenants. In KV this is stored outside the tenant rental records:

```text
associations:index
associations:{tenant_id}
```

The local JSON runner mirrors this in `.data/local-kv/_associations.json` and
also discovers existing tenant JSON files so local debug data appears in the
admin overview. Registry fields are low-PII operational references:

- tenant id
- display name and short name
- status (`active`, `paused`, `archived`)
- region and locale
- contact reference
- Hitobito group reference
- inventory reference
- notes

The Admin Center UI keeps association rows clickable like the rental CRUD lists.
The drilldown shows a compact operational state journey and low-PII references.
When tenant switching is unlocked in local/debug mode, the same view can open an
association's tenant data directly.
Tenant bootstrap, imports, and CRUD writes automatically create a default
association registry entry when none exists. Once platform admins curate display
names, status, or references, normal tenant record writes leave those registry
details untouched. Tenant import updates the registry display name only when the
import file explicitly includes `display_name` or `association_name` metadata.

The association registry is a platform operation. Local/open debug mode keeps it
available to local admins for fast testing, but signed/header deployments require
an `admin` role on the `platform-admin` tenant context. A tenant-level admin for
`band-one`, for example, can manage `/api/band-one/...` records but receives
`403 platform admin required` for `/api/admin/associations`.

The same platform boundary now covers `/api/admin/users`. User access records
are stored outside tenant data under a hashed backend id plus the normalized
Access email, role configuration, tenant/member links, status, and timestamps.
Optional display labels reject contact-like values, keeping the Access email as
the only intentional user identifier for the front door. Member links use opaque
local member ids and reject email or phone-like values.
The Admin Center renders these users beside associations and opens a drilldown
showing global role, access profile, tenant roles, and linked member ids.
`GET /api/admin/users/export/tenant-access` renders those profiles as Wrangler
KV bulk rows for `TENANT_ACCESS_KV`, bridging the backend registry to the
Cloudflare Access front door without manually reshaping JSON.

## Local Debugging

Use Wrangler local development:

```bash
uv sync
npm install
npm run dev
```

The backend `dev` and `deploy` scripts use Cloudflare's Python Worker tooling:
`uv run pywrangler dev` and `uv run pywrangler deploy`. Keep `uv.lock` committed
so that tooling is reproducible across local debug and deployment. JavaScript
Wrangler is still present for KV namespace management and the optional Access
front door.

When Wrangler cannot run, use the stdlib Python debug server:

```bash
python3 scripts/local_dev_server.py
```

It serves `public/`, exposes the same `/api/...` routes through
`worker.api_core`, and persists local JSON files under `.data/local-kv/`. This
runner is only for development; production storage remains Cloudflare KV.
Preflight also keeps generated debug artifacts out of source control, including
`.data/local-kv/`, `.wrangler/`, `.venv/`, `.venv-workers/`, Python bytecode
caches, `node_modules/`, and `.env`.

Run pure Python domain tests without starting Wrangler:

```bash
npm test
```

or, without Node:

```bash
python3 -m unittest discover -s tests
```

Run a local end-to-end smoke without Wrangler:

```bash
python3 scripts/smoke_local.py --verbose
```

Add `--signed` to also run the local server with signed tenant context headers,
matching the deployed auth shape without requiring Cloudflare Access:

```bash
python3 scripts/smoke_local.py --signed --verbose
```

The same signed smoke path is available through `npm run smoke:signed`.

The smoke script starts the same Python HTTP handler on an ephemeral localhost
port with temporary JSON storage. It checks static assets, the `/api` JSON
boundary, `/api/context`, bootstrap, admin associations and users,
export/import, instrument inventory import/export, Hitobito member import,
basic access-profile scoping, return/delete, PII rejection, and tenant-id
validation.

Run deployment-shape preflight checks:

```bash
npm run preflight
```

The `Cloudflare refactor CI` GitHub Actions workflow keeps the repository on the
Cloudflare path by running unit tests, signed local smoke, frontdoor-aware
preflight, and frontend/frontdoor JavaScript syntax checks through
`npm run check:js`. It intentionally does not deploy and does not use the
removed Azure App Service workflow actions.
Preflight also requires the static shell to declare a same-origin Content
Security Policy and `no-referrer` metadata.

`npm run preflight` allows placeholder Cloudflare IDs so the refactor remains
easy to validate locally. Before production deploy, replace placeholder KV IDs
and Access values, then run:

```bash
npm run preflight:deploy
npm run preflight:frontdoor
```

The strict checks fail on placeholder Cloudflare values, missing static assets,
Python Worker tooling drift, legacy Flask/SQL/Azure paths and workflows that
should stay removed, and legacy runtime imports or dependency declarations in
active Worker/static code.

## Next Refactor Steps

1. Add deployment environments after real KV namespace IDs, Access audience, and
   front-door routes are available.
2. Add Worker integration tests once the local Wrangler runtime is installed.
3. Continue closing feature gaps found during operator testing.
