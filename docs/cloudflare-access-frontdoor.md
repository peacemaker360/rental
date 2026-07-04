# Cloudflare Access Front Door

The Python Worker API accepts signed tenant context headers. In production,
those headers should be created by a trusted Cloudflare component, not by the
browser. `frontdoor/access_context_worker.js` is a small Worker that does that.

## Flow

```text
browser
  -> Cloudflare Access
  -> association-rental-frontdoor
  -> association-rental Python Worker service binding
  -> Cloudflare KV
```

The front door validates the Cloudflare Access JWT from
`Cf-Access-Jwt-Assertion` or the `CF_Authorization` cookie, checks issuer,
audience, expiry, and the Access JWKS signature, then loads a user access
profile from `TENANT_ACCESS_KV` using the JWT email claim.

It forwards only an opaque signed context to the backend:

```text
x-rental-context
x-rental-context-signature
```

It strips Access headers, cookies, authorization headers, and any incoming
`x-rental-*` headers before forwarding the request.

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
is read-only and includes the linked `member_id` in the signed context so the
backend only returns that member's related rentals and instruments.
For `/api/admin/...` routes, `platform_admin` profiles are always signed with
the `platform-admin` tenant context even when the user also has a default tenant
or per-association roles.
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

Platform admins can also export the same KV bulk shape directly from the app
after editing users in the Admin Center:

```text
GET /api/admin/users/export/tenant-access
```

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

Set these front-door vars in `wrangler.frontdoor.toml`:

```toml
CF_ACCESS_TEAM_DOMAIN = "your-team.cloudflareaccess.com"
CF_ACCESS_AUD = "your-access-audience-tag"
```

Deploy the backend first, then the front door:

```bash
npm run deploy
npm run deploy:frontdoor
```

Bind the public route to the front door. The backend Worker can remain reachable
only as a service binding, while local development can still use `npm run dev`
or `python3 scripts/local_dev_server.py`.
