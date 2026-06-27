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
audience, expiry, and the Access JWKS signature, then loads a tenant assignment
from `TENANT_ACCESS_KV`.

It forwards only an opaque signed context to the backend:

```text
x-rental-context
x-rental-context-signature
```

It strips Access headers, cookies, authorization headers, and any incoming
`x-rental-*` headers before forwarding the request.

## Tenant Assignment KV

Use the Access JWT subject as the key so the assignment store does not need
email addresses:

```text
principal:{access_jwt_sub}
```

Value:

```json
{
  "tenant_id": "demo-association",
  "role": "operator",
  "actor_id": "member-system-user-42"
}
```

`actor_id` is optional. If it is absent, the front door derives an opaque
`access:{hash}` value from the Access subject. Roles must be `viewer`,
`operator`, or `admin`.

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
