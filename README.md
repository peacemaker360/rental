# Rental Desk

An association instrument-rental tool: instruments, members, rentals, returns,
maintenance records, and history. The static EN/DE frontend and Python API run
on Cloudflare Workers, with tenant-scoped JSON in KV. Clerk handles sign-in,
sessions, and organization roles. Cloudflare Access is no longer used.

## Documentation

- [Product scope, users, and priorities](PRODUCT.md)
- [Visual and interaction design contract](DESIGN.md)
- [Clerk setup, live local demo, deployment, and migration](docs/clerk-migration.md)
- [Architecture, privacy, and import/export](docs/architecture.md)

## Local Development

Use Python 3.12+, Node.js 22+, and uv for Worker development:

```bash
npm ci
uv sync --locked
```

### Offline Mock Sign-In

```bash
npm run dev:mock -- --port 8794
```

Open http://localhost:8794. Sign-in creates a tab-local simulated session;
sign-out clears it. No Clerk keys or network are needed. Invitations are local
records and send no email. Mock authentication is loopback-only and cannot be
used against the hosted gateway. Data lives in `.data/local-kv/`.

### Real Clerk Sign-In

Put matching development keys from your Clerk application's Development
instance in a local `.dev.vars` file:

```dotenv
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
```

The gateway also accepts `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`. Wrangler supports
`.env` too; `.dev.vars` takes precedence, so choose one source. Restart both
servers after changing keys. Run in separate terminals:

```bash
npm run dev:clerk:backend
```

```bash
npm run dev:clerk:frontdoor
```

Open http://localhost:8795, not backend port 8796. Rental data uses local Wrangler
KV, but authentication and user management use your real Clerk development
instance. Both commands share a deliberately local-only signing value; never
use it in production.

The frontdoor command pins `--local-upstream localhost:8795` so Wrangler does
not substitute the production route hostname during Clerk origin validation.
Use `localhost` consistently. If changing the port, change both `--port` and
`--local-upstream` together.
`npm run dev:frontdoor` is an alias for this same live Clerk development command.

Sign up, verify your email, then follow the
[first administrator setup](docs/clerk-migration.md#first-administrator).
Signing in alone does not grant association access.

### Direct CRUD Debugging

```bash
npm run dev:python
```

Open http://127.0.0.1:8787 for immediate local-admin access using JSON files.
VS Code's **Rental Desk: Local Mock** configuration supports Python breakpoints.
`npm run dev` instead runs the Python Worker/static assets through pywrangler
with local-admin context; it does not test Clerk. Stop servers with Ctrl+C in
each terminal.

Local JSON data and Wrangler KV are separate stores. Keep debug data and
credentials private. Ignore rules do not protect already tracked files:
check `git ls-files .env .dev.vars` before committing. Untrack secret files
without deleting local copies, and rotate credentials if exposed.

## Validation

```bash
npm run check:js
npm test
npm run smoke:signed
python3 scripts/deploy_preflight.py --allow-placeholders --include-frontdoor
```

Tests cover domain rules, auth and role mapping, tenant isolation, imports,
and local HTTP behavior. Restricted environments may skip socket tests; run
them with local sockets available before deploying. CI runs these checks
without deployment. Python-only checks:

```bash
PYTHONPATH=.:worker python3 -m unittest discover -s tests
```

Mock tests do not prove live sign-in, invitation acceptance, or migration.
The Clerk guide includes the remaining live validation checklist.

## Deployment

Configure both Workers, matching KV bindings, Clerk keys, the shared context
secret, and public API routing using the
[deployment guide](docs/clerk-migration.md#deployment). Repository domain and
namespace IDs are environment-specific, not reusable defaults.

```bash
npm run preflight:deploy
npm run preflight:frontdoor
npm run deploy
npm run deploy:frontdoor
```

Preflight does not inspect remote secrets or Clerk settings. Verify live
authentication and association permissions before deploying.

## Operational Features

- Admin Center manages associations, public contacts, access, member links,
  join requests, and invitations. New invitations default to basic access.
- Basic users see only their linked rentals and instruments. Member email
  matching stores a hash, not the raw email on the member record.
- Instruments track condition, servicing, planned service dates, and history.
- Tenant JSON backup/restore, instrument-only import/export, and Hitobito member
  imports remain supported.
- Mobile details expand inline; desktop uses a detail panel. EN/DE language
  preference is stored in the browser.

Legacy data conversion uses `scripts/migrate_legacy.py`. Identity migration
uses `scripts/migrate_clerk_access.py` and defaults to an offline dry run.
Neither runs automatically.
