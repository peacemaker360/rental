## Rental Desk

This repository is being refactored from a Flask/SQL app into a Cloudflare-only
serverless app:

- `public/` contains the static frontend.
- `worker/` contains the Python Worker API.
- Cloudflare KV stores JSON records instead of SQL tables.
- The existing Flask app is still present for behavior comparison while the new
  Worker version reaches feature parity.

### Local Cloudflare App

Install the Worker tooling:

```bash
npm install
```

Run the static frontend and Python Worker locally:

```bash
npm run dev
```

Open the local Wrangler URL, then use **Load Demo** once for the current tenant.
The default tenant is `demo-association`; switching the tenant changes the KV key
prefix used by the API.

If Node/Wrangler is not available, run the same static frontend and API contract
against local JSON files with:

```bash
python3 scripts/local_dev_server.py
```

That server opens on `http://127.0.0.1:8787` and persists local development data
under `.data/local-kv/`.

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

### Cloudflare Worker Shape

The Worker exposes tenant-scoped endpoints:

- `GET /api/health`
- `GET /api/context`
- `POST /api/{tenant}/bootstrap`
- `GET /api/{tenant}/summary`
- `GET /api/{tenant}/export`
- `PUT /api/{tenant}/import`
- `GET|POST /api/{tenant}/instruments`
- `GET|PUT|DELETE /api/{tenant}/instruments/{id}`
- `GET|POST /api/{tenant}/members`
- `GET|PUT|DELETE /api/{tenant}/members/{id}`
- `GET|POST /api/{tenant}/rentals`
- `GET|PUT|DELETE /api/{tenant}/rentals/{id}`
- `POST /api/{tenant}/rentals/{id}/return`
- `GET /api/{tenant}/history`

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
  and optionally `issued_at`
- `x-rental-context-signature`: HMAC-SHA256 of `x-rental-context` using
  `RENTAL_CONTEXT_SECRET`

Roles are `viewer`, `operator`, and `admin`. Signed contexts with an `issued_at`
older than one hour are rejected. This keeps tenant identity out of browser
storage and avoids storing member/user PII in the rental data.

`frontdoor/access_context_worker.js` is an optional Cloudflare Access front door
that validates the Access JWT, maps the authenticated principal to a tenant and
role through `TENANT_ACCESS_KV`, strips identity headers, and injects the signed
tenant context for the Python Worker. See
`docs/cloudflare-access-frontdoor.md`.

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

### Backup And Migration

The static UI has **Export** and **Import** controls in the top bar. Export
downloads one tenant as a JSON package. Import replaces the current tenant with a
validated JSON package.

The import path accepts only the new low-PII schema. It rejects common legacy PII
fields such as `email`, `phone`, `address`, and `birthdate`, so old Flask data
should be transformed before import instead of copied directly.

Transform a legacy Flask-style export into the new package format:

```bash
python3 scripts/migrate_legacy.py \
  --tenant demo-association \
  --legacy-json tests/fixtures/legacy_export.json \
  --output /tmp/rental-import.json
```

The transformer copies instruments and rentals, maps legacy customers to
low-PII members, and records which contact fields were intentionally omitted.

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

### PII Direction

The new member model avoids storing email and phone numbers by default. It keeps
only an operational display name, optional member reference, optional contact
hint, and active flag. If a future integration needs contact details, prefer a
reference to the association's source system over copying PII into KV.

## Legacy DB Migrations

### Init
flask db init
flask db revision --autogenerate -m "Initial migration"
flask db upgrade

### Updates
flask db revision --autogenerate -m "Made change XYZ"
flask db upgrade
