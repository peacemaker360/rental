# Cloudflare Refactor Notes

## Current Slice

The new implementation keeps the app's main character: operational CRUD for
instruments, members, rentals, returns, and rental history.

The Flask app remains in place. The Cloudflare path is additive and lives in:

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
tenant:{tenant_id}:index:history
tenant:{tenant_id}:instruments:{instrument_id}
tenant:{tenant_id}:members:{member_id}
tenant:{tenant_id}:rentals:{rental_id}
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

## Backup And Import

Admin users can export and import tenant data:

```text
GET /api/{tenant}/export
PUT /api/{tenant}/import
```

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
    "history": []
  },
  "summary": {}
}
```

Import validates through the same domain normalizers used by CRUD writes,
rewrites records to the route tenant, and rejects blocked legacy PII fields such
as `email`, `phone`, `address`, and `birthdate`. Import currently replaces the
tenant dataset, which is simple and predictable for backups and migration dry
runs.

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
part of the importable records.

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
- Rental history is append-only from the UI/API perspective.

## PII Boundaries

The legacy `Customer` model stores email and phone. The Worker `member` model
does not. It stores:

- `display_name`
- `member_ref`
- `contact_hint`
- `groups`
- `is_active`

`contact_hint` is intentionally vague. For production, keep authoritative contact
details in the association's member system and store only an external reference
or short operational note here.

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
optionally `issued_at`. `x-rental-context-signature` is an HMAC-SHA256 signature
over that encoded context using the `RENTAL_CONTEXT_SECRET` Worker secret.
The API rejects requests when the signed tenant does not match the tenant in the
route, when the role is not `viewer`, `operator`, or `admin`, or when an
`issued_at` timestamp is older than one hour. Write operations require
`operator` or `admin`; demo bootstrap and delete operations require `admin`.

`frontdoor/access_context_worker.js` is a deployable Cloudflare Access front
door for this shape. It validates `Cf-Access-Jwt-Assertion` or the
`CF_Authorization` cookie against the Access JWKS, looks up
`principal:{access_jwt_sub}` in `TENANT_ACCESS_KV`, signs the tenant context,
and forwards to the Python Worker through a service binding. The details live in
`docs/cloudflare-access-frontdoor.md`.

For manual API debugging, `scripts/sign_context.py` prints matching signed
headers from a tenant, actor, role, and `RENTAL_CONTEXT_SECRET`.

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

## Local Debugging

Use Wrangler local development:

```bash
npm install
npm run dev
```

The configured script persists local KV state under `.wrangler/state`, which
makes local test data survive Worker restarts.

When Wrangler cannot run, use the stdlib Python debug server:

```bash
python3 scripts/local_dev_server.py
```

It serves `public/`, exposes the same `/api/...` routes through
`worker.api_core`, and persists local JSON files under `.data/local-kv/`. This
runner is only for development; production storage remains Cloudflare KV.

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

The smoke script starts the same Python HTTP handler on an ephemeral localhost
port with temporary JSON storage. It checks static assets, `/api/context`,
bootstrap, export/import, return/delete, PII rejection, and tenant-id validation.

## Next Refactor Steps

1. Add deployment environments after real KV namespace IDs, Access audience, and
   front-door routes are available.
2. Add automated seeding/import helpers for `TENANT_ACCESS_KV` assignments.
3. Add Worker integration tests once the local Wrangler runtime is installed.
4. Continue closing feature gaps against the legacy Flask screens.
