# Architecture And Operations

## Runtime

- `public/`: static frontend, Clerk browser session adapter, EN/DE UI.
- `frontdoor/access_context_worker.js`: authenticated API gateway. The filename
  is retained, but it no longer implements Cloudflare Access.
- `frontdoor/clerk_auth.js` and `clerk_roles.js`: token verification, verified
  primary email, organization memberships, and organization-role mapping.
- `worker/worker.py`: Python Worker entry point and static assets.
- `worker/api_core.py`: authorization, routing, CRUD, and administration.
- `worker/domain.py`: rental/service rules and validation.
- `worker/storage.py`: KV records and indexes.
- `worker/clerk_directory.py`: Clerk-backed access and invitation management.
- `scripts/local_dev_server.py`: local JSON-backed debug/mock server.

The browser sends Clerk bearer tokens to the same-origin API. The gateway
verifies identity, resolves authorization, removes untrusted identity headers,
and forwards HMAC-signed context to Python through `RENTAL_BACKEND`.
Hosted Python requests require signed context. Localhost in `auto` mode permits
admin debugging; the real Clerk dev command explicitly uses `signed` mode.
Manual debugging uses `scripts/sign_context.py` with the server's context secret.
Trusted header mode is an internal option, never suitable for direct browser use.

## Tenancy And Authorization

Tenant routes use `/api/tid-{tenant}/...`; stored IDs exclude `tid-` and match
`^[a-z0-9][a-z0-9_-]{1,62}$`. System names including `auth`, `admin`, `context`,
`health`, `access-requests`, and `platform-admin` are reserved. Route and signed
tenant must match. The frontend loads context before records; switching needs
a newly authorized context, not merely a browser-side tenant change.

Clerk organization IDs explicitly map to associations. Names/slugs alone do not
grant access. Current Clerk organization memberships control tool access; global app roles are retired;
old KV grants cannot restore revoked access. See [Clerk role mapping](clerk-migration.md).
Backend roles are `viewer`, `operator`, and `admin`; user-facing readers map to
`viewer`. Basic profiles are read-only and limited to linked members, rentals,
and rented instruments. Hosted matching uses the verified email hash. Association admins cannot
manage the cross-association registry; operators provision mappings.

## Storage And Consistency

`RENTAL_KV` stores tenant JSON and administrative indexes:

```text
tenant:{tenant_id}:index:{entity}
tenant:{tenant_id}:{entity}:{record_id}
tenant:{tenant_id}:meta
associations:index
associations:{tenant_id}
```

Entities include instruments, members, rentals, service_records, and history.
Records also contain `tenant_id`; saves delete keys no longer indexed.
`TENANT_ACCESS_KV` stores join requests and notification delivery state. Legacy
`user:{email}` keys may remain but are ignored and no longer written. Both Workers must share
the namespace IDs for each binding.

Writes increment `revision` and set `updated_at`. The frontend sends
`x-rental-expected-revision`; stale writes receive `409` plus current metadata.
This is an optimistic guard, not atomic compare-and-swap: KV is eventually
consistent and simultaneous read/modify/write operations can still race.
Clerk changes and KV saves are not transactional either. Provider errors remain
visible in the admissions view.

The Python runner's `.data/local-kv/` and Wrangler local KV are separate stores.
Mock invitations are local records, not emails.

## API Overview

| Route | Purpose |
| --- | --- |
| `/api/health`, `/api/auth/config` | Health and public authentication configuration |
| `/api/context` | Authenticated tenant and capabilities |
| `/api/access-requests` | Submit a signed-in user's join request |
| `/api/admin/access-requests` | Review requests; actions use individual request IDs |
| `/api/admin/associations[/{tenant}]` | Local operator registry management; forbidden in hosted mode |
| `/api/admin/users[/{id}]` | Retired in hosted mode (410) |
| `/api/admin/users/export/tenant-access` | Local legacy export only |
| `/api/admin/invitations/{tenant}[/{id}]` | Read-only hosted invitations; manage through Clerk |
| `/api/tid-{tenant}/bootstrap` | Load demo data |
| `/api/tid-{tenant}/meta` and `/api/tid-{tenant}/summary` | Revision and aggregates |
| `/api/tid-{tenant}/{entity}[/{id}]` | CRUD for instruments, members, rentals, service_records |
| `/api/tid-{tenant}/rentals/{id}/return` | Return a rental |
| `/api/tid-{tenant}/history` | Read history |

Collection reads accept `search` and `status`. Context failures include stable
`errorCode` values. Empty `/api` routes return JSON 404, not the SPA. API responses
use `no-store`, `nosniff`, and `no-referrer`; wildcard CORS is not enabled.
Unexpected errors do not expose internal exception details.

## Backup And Import

| Endpoint under `/api/tid-{tenant}` | Behavior |
| --- | --- |
| `GET /export` | Export instruments, members, rentals, services, history |
| `PUT /import` | Validate and replace tenant data |
| `GET /instruments/export` | Inventory-only export |
| `PUT /instruments/import` | Merge by serial number, preserving local IDs |
| `PUT /members/import/hitobito` | Merge by stable `hitobito:{id}` reference |

Back up before replacement imports. Backend validation is authoritative;
browser preflight is a usability aid. Hitobito accepts lists, people/members
wrappers, or JSON:API data and omits email, phone, address, and birthday fields.
Inventory imports accept lists, instruments/records wrappers, or JSON:API data.
Stable IDs preserve attached rentals and maintenance history.

Convert legacy Flask exports before import:

```bash
python3 scripts/migrate_legacy.py --tenant demo-association \
  --legacy-json tests/fixtures/legacy_export.json --output /tmp/rental-import.json
```

The converter also accepts `--instruments-csv`, `--members-json`, and
`--rentals-csv`. It reports omitted contact fields and contact-like descriptions.
Keep its fixture/tests: legacy conversion remains supported. Identity assignment
migration uses [the separate Clerk tool](clerk-migration.md#migrating-existing-assignments).

## Domain And Privacy

Active rentals make instruments unavailable and block deleting the instrument
or member. Returns release the instrument. Instrument deletion cascades service
records but preserves deletion events. Maintenance tracks condition, job/date,
next service, provider, cost, and notes. Conditions are `good`, `watch`,
`needs_service`, `in_service`, and `retired`; due dates also flag attention.

Members retain operational names, references, groups, roster notes, active
status, and optional `access_email_hash`. The `access_email` write input is
hashed and discarded. History actors are opaque IDs, not contacts. Descriptions
and notes reject contact-like content; source contacts belong in the roster or
Hitobito.

This is low-PII, not zero-PII: user profiles, requests, and invitations use
verified email. Association public contact is deliberately shown to users.
Treat exports and local debug stores as sensitive; do not commit them.

Hosted authorization never reads legacy KV user profiles, grants, status flags,
or member links. KV stores rental data, org-to-association mappings, and join
requests. Basic rental visibility matches verified Clerk email to rental-member
email hashes. Global metadata cannot bypass org membership. Hosted admissions
are scoped to the current association; registry provisioning is operator work.
Legacy user permission APIs are retired in signed mode. Local debugging and the
explicit one-time migration tool retain compatibility with old export schemas.

Member self-service is a separate authorization path: verified Clerk email plus
an active rental-member email-hash match grants `viewer` with the `basic` profile,
without org membership. Its association choices are carried in signed context;
the backend rechecks email matching and filters current rentals. The relationship
never grants inventory-wide read, write, or administration access. Clerk org
roles remain authoritative for those broader capabilities.
