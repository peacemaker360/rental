# Cloudflare Access Front Door

The Python Worker API accepts signed tenant context headers. In production,
those headers should be created by a trusted Cloudflare component, not by the
browser. `frontdoor/access_context_worker.js` is a small Worker that does that.

## Flow

```text
browser
  -> association-rental-frontdoor
  -> Cloudflare Access for protected URLs
  -> association-rental Python Worker service binding
  -> Cloudflare KV
```

The static frontend is intentionally reachable without a Cloudflare Access
challenge so a user without an access profile can see the landing screen and
request access. Protected API calls still require a Cloudflare Access JWT from
`Cf-Access-Jwt-Assertion` or the `CF_Authorization` cookie. For those calls, the
front door checks issuer, audience, expiry, and the Access JWKS signature, then
loads a user access profile from `TENANT_ACCESS_KV` using the JWT email claim.

It forwards only an opaque signed context to the backend:

```text
x-rental-context
x-rental-context-signature
```

It strips Access headers, cookies, authorization headers, and any incoming
`x-rental-*` headers before forwarding the request.

## Public and Protected Routes

Configure Cloudflare Access so the browser can load the public shell before the
user is known. The front door then enforces signed context for protected API
traffic.

Leave these routes public:

```text
GET /
GET /index.html
GET /styles.css
GET /app.js
GET /auth/logout
/api/access-requests
```

Protect these routes with Cloudflare Access:

```text
/api/*
```

Access policies and Worker routes are separate Cloudflare configuration. The
same protected paths must also be routed to `association-rental-frontdoor`.
`wrangler.frontdoor.toml` is the source of truth for these production routes:

```toml
workers_dev = false

routes = [
  { pattern = "rental.kittythecat.ch/api/*", zone_name = "kittythecat.ch" }
]
```

The Access application and frontdoor Worker both cover the same `/api/*`
surface. The backend Worker handles public `/auth/logout` before static assets,
so logout does not depend on a second frontdoor route.

Add an exception so `/api/access-requests` remains public even if `/api/*` is
protected. The front door only accepts unauthenticated `POST` requests on that
path; other methods still go through the normal protected API path. The public
join-request endpoint asks for an email and tenant id and stores only a pending
request in `TENANT_ACCESS_KV`; it does not grant app access.
`/api/auth/login` is a lightweight protected route: after Access succeeds, the
front door serves the static shell internally at that URL, and the frontend
replaces the visible URL with `/` without another network redirect. This gives
the UI a real sign-in target without sending users to a raw JSON API response
or introducing a second Access application path.

`/auth/logout` remains public and is handled by the primary Python Worker. It
redirects to the team-domain Access logout endpoint derived from
`CF_ACCESS_TEAM_DOMAIN`. It first expires the application-domain authorization
cookie, then the team endpoint revokes the global session. The response is
marked `no-store`; a response header of `x-rental-auth-handler: backend`
confirms that static SPA fallback did not handle the request.

The expected first-visit flow is:

```text
1. User opens / and sees the public sign-in screen.
2. Sign in navigates to /api/auth/login, where Cloudflare Access can
   challenge in a top-level browser navigation.
3. After Access succeeds, /api/auth/login serves the app shell and the frontend
   calls /api/context.
4. Users with an active profile enter the app. Authenticated users without a
   profile see the access-request form with their verified email prefilled.
5. A user may submit POST /api/access-requests with a tenant id, retry sign-in,
   or log out and start with a different identity.
```

## Avoid Authentication Redirect Loops

Configure one Access self-hosted application for the browser-visible hostname,
for example `rental.example.org`, covering `/api/*`. Its audience must match
`CF_ACCESS_AUD`. Add a more-specific bypass for `POST /api/access-requests` and
keep the shell plus `/auth/logout` public. Do not add a separate Access entry for
`/auth/login`; sign-in now uses `/api/auth/login` inside the API application.

After authentication, inspect the Network panel. The final
`/cdn-cgi/access/authorized` request must run on the browser-visible application
hostname and set its application cookie there. If `Cf-Access-Domain` or the
callback `Location` points to a `workers.dev` hostname while the browser returns
to a custom domain, the application is still attached to the Worker hostname or
configured as an unnecessary multi-domain application. Remove that Worker
hostname and re-save the application for the public custom hostname. Otherwise
the custom-domain `/api/auth/login` request immediately restarts authentication
because it did not receive the matching application cookie.

Leave the Cookie Path Attribute disabled, set SameSite to `None` or `Lax`, and
disable Binding Cookie when `Authenticate with Cloudflare One Client` is in use.
Cloudflare documents all three as possible redirect-loop causes. Test the
corrected setup in a normal browser window first; private-window tracking
protection can interfere with Access cookies and XHR redirects.

## User Access KV

Use the normalized Cloudflare Access email claim as the user-profile key:

```text
user:{email}
```

Value:

```json
{
  "email": "person@example.org",
  "status": "active",
  "global_role": "none",
  "access_profile": "basic",
  "tenant_roles": [
    {"tenant_id": "demo-association", "role": "reader"}
  ],
  "member_links": [
    {"tenant_id": "demo-association", "member_id": "mem_123"}
  ]
}
```

`global_role` can be `none`, `reader`, `operator`, `admin`, or
`platform_admin`. Per-tenant roles can be `reader`, `operator`, or `admin`; the
front door maps `reader` to the backend read-only role. `access_profile=basic`
is read-only. If a `member_links` entry exists for the signed tenant, the front
door includes that linked `member_id` in the signed context. If no member link
is present, the backend can still auto-match the Cloudflare Access email claim
to a member whose Admin Center Access email hash matches, and then returns only
that member's related rentals and instruments.
For `/api/admin/...` routes, `platform_admin` profiles are always signed with
the `platform-admin` tenant context even when the user also has a default tenant
or per-association roles. A pure `platform_admin` profile with no default tenant
or tenant roles can also sign in with the `platform-admin` context, which keeps
first-time setup possible before any association tenant exists.
Malformed profile rows fail closed before any tenant context is signed: the
front door validates status, global role, access profile, default tenant, and
that tenant roles and member links are lists. Member-link ids must be opaque
local member identifiers, not emails or phone numbers.

Legacy subject assignments are still accepted as a migration fallback:

```text
principal:{access_jwt_sub}
```

```json
{
  "tenant_id": "demo-association",
  "role": "operator",
  "actor_id": "member-system-user-42"
}
```

If `actor_id` is absent for a legacy assignment, the front door derives an
opaque `access:{hash}` value from the Access subject. Legacy roles must be
`viewer`, `operator`, or `admin`.

Prepare assignments from a low-PII JSON file:

```json
{
  "assignments": [
    {
      "email": "person@example.org",
      "global_role": "none",
      "access_profile": "basic",
      "tenant_roles": [
        {"tenant_id": "demo-association", "role": "reader"}
      ],
      "member_links": [
        {"tenant_id": "demo-association", "member_id": "mem_123"}
      ]
    }
  ]
}
```

Render a summary before importing:

```bash
npm run tenant-access -- assignments.json --format summary
```

Render a KV bulk file:

```bash
npm run tenant-access -- assignments.json \
  --format kv-bulk \
  --output /tmp/tenant-access-kv.json
```

Hosted deployments bind `TENANT_ACCESS_KV` to both Workers. Creating, editing,
approving, or deleting a user in the Admin Center writes the backend user
registry and mirrors the frontdoor `user:{email}` row automatically. Platform
admins can still export the same KV bulk shape directly from the app for audit
or migration:

```text
GET /api/admin/users/export/tenant-access
```

Users without a profile can load the static start screen and send a join request
for a tenant. The public request includes the email address the user plans to
use with Cloudflare Access. The front door stores pending requests in
`TENANT_ACCESS_KV`; platform admins see all requests, while tenant admins see
only requests for their signed tenant. Approving a request creates or updates
the user profile and removes the pending request; denying removes the pending
request without creating access. If the association has a public contact set in
the Admin Center, the pending response includes it so the user has a reference
for follow-up.

Or render explicit Wrangler commands:

```bash
npm run tenant-access -- assignments.json --format commands
```

For user-profile rows, the email is intentional auth metadata and is not copied
into tenant rental records. For legacy subject rows, the helper still rejects
email, name, phone, and address fields; use the opaque Cloudflare Access `sub`
claim as `access_sub`. Optional legacy `actor_id` values must also be opaque
because they can be written into rental and service history.

## Configure

Create the assignment KV namespace:

```bash
npm run kv:create-tenant-access
npm run kv:create-tenant-access-preview
```

Copy the generated IDs into `wrangler.frontdoor.toml`.

Set the same context signing secret on both Workers:

```bash
npx wrangler secret put RENTAL_CONTEXT_SECRET
npx wrangler secret put RENTAL_CONTEXT_SECRET --config wrangler.frontdoor.toml
```

Set the Access team domain in both Worker configurations; the backend uses it
for logout and the front door uses it for JWT validation. Set the audience in
`wrangler.frontdoor.toml`:

```toml
CF_ACCESS_TEAM_DOMAIN = "your-team.cloudflareaccess.com"
CF_ACCESS_AUD = "your-access-audience-tag"
```

Deploy the backend first, then the front door:

```bash
npm run deploy
npm run deploy:frontdoor
```

The frontdoor deploy publishes only `/api/*` from `wrangler.frontdoor.toml`.
Verify that route belongs to `association-rental-frontdoor`. The backend keeps
the custom domain, serves `/` and static assets, and runs first for
`/auth/logout`. A deployed logout request must return `302`, `Cache-Control:
no-store`, `x-rental-auth-handler: backend`, and a `Location` on the Access team
domain. A cached `200` HTML response means the backend deployment predates this
change. Local development can still use `npm run dev` or
`python3 scripts/local_dev_server.py`.
