# Clerk Migration

## Current Implementation

Clerk handles hosted sign-in, sign-up, sessions, account settings, and sign-out.
The static frontend obtains a fresh session token through ClerkJS and sends it
as an Authorization bearer token. The JavaScript frontdoor verifies the token,
checks its issuer and requesting origin, and obtains the verified primary email
from Clerk's Backend API. The Python Worker still receives an HMAC-signed tenant
context. Rental data and association administration remain on Workers and KV.

Join requests require a signed-in account and use its verified email. An email
provided by the browser cannot override that identity.

Hosted authorization now reads Clerk organization memberships rather than legacy
KV role grants. Platform admins can save a `clerk_organization_id` on each
association in Admin Center. Tenant imports cannot change this mapping; duplicate
organization mappings are rejected. The frontdoor reads the registry using its
`RENTAL_KV` binding. Organization names/slugs do not establish tenant identity.

Organization role mapping:

| Clerk role | Rental role | Profile |
| --- | --- | --- |
| `org:member` | reader | basic, own rentals only |
| `org:reader` | reader | full |
| `org:operator` | operator | full |
| `org:admin` | admin | full |

Authorization uses current Clerk organization memberships only. Global app roles
are retired: private/unsafe user metadata and old KV profiles cannot grant access.
The gateway does not read KV user status, grants, profiles, or member links.
Clerk bans/locks still disable account access. Lookup failures deny access.
Basic users' own-rental visibility matches their verified primary Clerk email to
the email hash in rental-member records; this relationship does not grant membership.

The SDK membership lookup follows [Clerk's paginated Backend API](https://clerk.com/docs/reference/backend/user/get-organization-membership-list).

## Configuration Before Hosted Testing

1. Set `CLERK_PUBLISHABLE_KEY` in `wrangler.frontdoor.toml`.
2. Store `CLERK_SECRET_KEY` as a secret on both Workers: the frontdoor verifies
   accounts and reads memberships; the Python backend reads admissions. Keep the existing
   shared `RENTAL_CONTEXT_SECRET` on both Workers.
3. Configure Clerk's allowed application origins and enable email verification.
   Enable Organizations. Optional membership lets new users sign in before
   requesting access. Required
   membership is supported too: users must finish Clerk’s organization-selection
   task before Rental Desk accepts their session. For an invitation-only setup,
   disable user-created organizations in Clerk and invite users to mapped organizations.
   Create custom `org:reader` and `org:operator` roles alongside the standard
   `org:member` and `org:admin` roles. This repository does not enable these
   settings in your Clerk instance automatically.
4. Match `public/index.html`'s CSP to the actual production Clerk frontend API
   hostname. It currently allows development `*.clerk.accounts.dev` and
   production `clerk.kittythecat.ch`, plus Clerk's documented bot-protection hosts.
5. Remove Cloudflare Access applications protecting the rental app routes when
   switching over. Clerk tokens are verified by the Worker itself. An Access
   challenge before the Worker would prevent Clerk requests reaching the app.
6. Deploy the frontend/backend and frontdoor together after verifying migration.

The old `CF_ACCESS_TEAM_DOMAIN`, `CF_ACCESS_AUD`, and team-domain logout are no
longer used. Users sign in again with Clerk. No passwords are held by Rental Desk.

## Sign-in, Invitations, and Pending Sessions

Rental Desk embeds Clerk’s prebuilt sign-in/sign-up UI. Clerk owns password,
email verification, invitation acceptance, and session tasks. The app checks
association access only after the session is active. Existing pending sessions
resume the relevant Clerk task at `/?authTask=choose-organization`,
`/?authTask=reset-password`, or `/?authTask=setup-mfa`.

`ACCESS_SESSION_PENDING` (403, `authReason: session-pending`) means account setup
is unfinished, not that the token has expired. Pending tokens still cannot access
rental data. The frontend also recognizes the older `ACCESS_TOKEN_INVALID` plus
`session-pending` response during a staggered deployment. Do not bypass this gate.

The former session-created redirect interrupted setup; it has been replaced by
state-change handling that detects task completion even within the same session.
Sign-in errors stay visible with retry/sign-out actions. Provider loading and app
API calls time out rather than leaving an indefinite loading screen.

Invite users to the association’s mapped Clerk organization with the appropriate
role. The existing invitation API uses Clerk’s hosted acceptance destination;
keep its account-portal flow configured. Invitation links landing on the app keep
`__clerk_ticket` and select the prebuilt sign-up component when
`__clerk_status=sign_up`. An already signed-in user missing access should accept
their invitation with that account, then choose **Check association access**.
In optional-membership mode, requesting access remains a secondary action.
In required-membership mode, administrators must invite/add users before they
can complete setup; an app access request cannot bypass a pending session.

The signed token’s active organization chooses the initial tenant only when it
has both a registered `clerk_organization_id` mapping and a current recognized
membership. Roles still come from fresh Clerk membership lookups. Selecting or
creating an unrelated organization never grants tenant access. Explicit tenant
routes still require a current recognized membership.

Validate in the Clerk development instance before deploying:

- New invitee: sign up, verify email, accept invitation, complete organization
  selection, and reach the mapped association without a sign-in loop.
- Existing user: accept an invitation and recheck access; use the invited email.
- Reload during a pending task; complete it without starting sign-in over.
- With required membership and no invitation, confirm Clerk keeps access pending.
- Test expired/revoked invitations and a different signed-in email; confirm Clerk
  shows its error and no rental data becomes accessible.
- Block the Clerk script/network, retry, and verify visible recovery feedback.
- Sign out, switch accounts/organizations, and verify tenant data and permissions.

References: [Clerk session tasks](https://clerk.com/docs/guides/configure/session-tasks)
and [JavaScript organization selection](https://clerk.com/docs/js-frontend/reference/components/authentication/task-choose-organization).

## Local Development

Install dependencies with `npm ci` and `uv sync --locked`. Use matching
development keys from the same Clerk instance, not production keys for localhost.

Run `npm run dev:mock -- --port 8794` for an
offline session simulation. It starts signed out, the sign-in action creates a
tab-local mock session, API requests carry a mock bearer token, and sign-out
clears it. The server restricts mock mode to loopback. No Clerk keys are required.
This exercises the app auth adapter, not Clerk's hosted verification screens.

The default `--auth-mode local` retains immediate admin access for CRUD debugging.
The frontdoor also accepts `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` from a local `.env`
file, matching Clerk's standard setup snippets; `CLERK_PUBLISHABLE_KEY` takes
precedence when set. Keep the secret key in the ignored local environment file.
If `.dev.vars` exists, Wrangler does not also load `.env`; keep both keys in
one chosen file. See [Cloudflare local secrets](https://developers.cloudflare.com/workers/local-development/environment-variables/).
Real Clerk testing uses the frontdoor with development keys and the backend
service binding; the mock token is never accepted by the hosted frontdoor.

For real Clerk development, put the development publishable/secret keys in
`.env` or `.dev.vars`, then start these commands in separate terminals:

```bash
npm run dev:clerk:backend
npm run dev:clerk:frontdoor
```

Open `http://localhost:8795`. Port 8796 is the private local Python backend;
direct API calls there require signed context. These scripts use a public,
local-only context signing value, local KV storage, and separate inspector ports.
Never use that signing value in a hosted environment. Wrangler loads the local
environment file without copying its contents into tracked configuration.

The live Clerk frontdoor command includes `--local-upstream localhost:8795`.
Without this override, Wrangler can infer the internal request hostname from
the production route. A localhost-issued token then fails with
`token-invalid-authorized-parties`, even when browser and token origins match.
Restart the frontdoor after updating the command. Use `http://localhost:8795`
consistently; if choosing another port, change both the listen port and upstream.
`npm run dev:frontdoor` is an alias for the same corrected Clerk development command.
Do not disable `authorizedParties` or trust arbitrary Origin headers to bypass
the mismatch; production requests must still satisfy strict origin validation.

Before adding keys, check `git ls-files .env .dev.vars`. An already tracked file
is not protected by `.gitignore`; untrack it while retaining the local file
before committing. Never commit a secret key.

## First Association Administrator

Create the organization and add your account with `org:admin` in Clerk Dashboard.
Map its `org_...` ID to the association registry through operator configuration.
New mappings are infrastructure configuration; hosted users cannot create or
remap associations. The local debug administration API remains available for
preparing registry records. Existing deployed mappings keep working.
Sign in, select the mapped organization, and open Admin Center.
There is no platform/global administrator or private-metadata bootstrap.
Remove obsolete `privateMetadata.rental.global_role` values at your convenience;
the app ignores them. Give administrators membership in each org they administer.

## Deployment

Complete the configuration checklist above. Existing namespace IDs and route
domain are environment-specific; replace them for another installation. Create
namespaces if needed using `npm run kv:create`, `npm run kv:create-preview`,
`npm run kv:create-tenant-access`, and `npm run kv:create-tenant-access-preview`.
Copy each namespace's IDs into both Worker configurations.

Set secrets interactively on both Workers, using the same context secret:

```bash
npx wrangler secret put CLERK_SECRET_KEY --config wrangler.toml
npx wrangler secret put CLERK_SECRET_KEY --config wrangler.frontdoor.toml
npx wrangler secret put RENTAL_CONTEXT_SECRET --config wrangler.toml
npx wrangler secret put RENTAL_CONTEXT_SECRET --config wrangler.frontdoor.toml
```

Serve the backend's static assets on the public hostname and route `/api/*` to
the frontdoor on that hostname. `RENTAL_BACKEND` must target the Python Worker's
service name. Remove Cloudflare Access protection. Preflight currently checks
the repository's hostname; change that validation alongside the route when
adopting a different domain.

```bash
npm run preflight:deploy
npm run preflight:frontdoor
npm run deploy
npm run deploy:frontdoor
```

Deploy both components in a coordinated maintenance window; do not mix the old
gateway with the Clerk frontend. Preflight does not inspect remote secrets,
DNS, or Clerk settings. Local environment files do not configure Worker secrets.
Production has separate Clerk keys, users, and organization mappings; bootstrap
its administrator separately.

## Migrating Existing Assignments

Keep an export of the old access profiles before switching the hosted role
source. `scripts/migrate_clerk_access.py` accepts a JSON user array, an API
`{"data":[...]}` response, or the old Tenant Access KV bulk export. Supply a
separate association array (or API data response) containing the reviewed
`clerk_organization_id` mappings. Existing users must sign in with Clerk and
verify their primary email first.

```bash
python3 scripts/migrate_clerk_access.py --users access-export.json --associations associations.json
```

This is offline validation only. After reviewing the source files and selecting
the intended Clerk instance through `CLERK_SECRET_KEY` in your environment:

```bash
python3 scripts/migrate_clerk_access.py --users access-export.json --associations associations.json --apply
```

Apply reconciles memberships in mapped rental organizations only; it may remove mapped memberships absent from the export. It leaves
unrelated organizations, Clerk accounts, rental data, and KV member links alone.
Do not run it against stale exports after subsequent permission changes. Failed
users are reported by opaque local ID, and the command exits nonzero. A retry
reconciles from current remote state. Keep input exports private; they contain
email addresses even though command output does not print them.

The Python migration sends an explicit `RentalDesk/0.1` User-Agent. Without it,
Clerk's edge was observed returning HTTP 403 with plain-text error 1010 for
urllib's default agent, while the same key/request with the app agent returned
200. This is not a tenant mapping or organization-role error. Use the updated
script rather than changing KV permissions to work around such a rejection.

## Invitations and Verification

Use the Clerk organization profile from Admin Center to invite members and change
roles. Admissions and invitations are read-only in the hosted rental API.
The legacy `/api/admin/users` API returns 410; legacy request approval and invitation
mutation endpoints reject writes. Resolve a request only after membership acceptance.

The explicit migration script is a one-time operator tool, never an authorization
source. It can reconcile old exports into Clerk memberships but does not write
or grant global roles. Do not apply stale exports after changing roles in Clerk.

Verify real sign-in/sign-out, invitation acceptance/revocation, organization
switching, basic own-rental isolation, and role removal before rollout. Offline
tests cannot verify Clerk's hosted screens. Deploy both Workers together; old
signed contexts containing global roles are intentionally rejected.

## Organization Settings for This Flow

In Clerk Dashboard → Organizations, set **Membership optional**, turn **Allow
user-created Organizations** off, and turn **Create first organization automatically** off. Review existing users' organization-creation permission
overrides too. These settings let a verified user reach the app's request-access
screen without being forced to create an organization. The app cannot enforce
Clerk's hosted creation policy by hiding a button. No remote settings were changed.
See [Clerk organization settings](https://clerk.com/docs/guides/organizations/configure).

Keep each association mapped to its actual `org_...` ID. The app uses Clerk's
organization switcher and shows the selected organization's name and image.
An unmapped selection displays an actionable error instead of silently entering
another association. Organization metadata is display-only; names never grant access.

## Admissions and Join Requests

Admin Center reads current Clerk members, roles, permissions, and pending
invitations, including accounts never entered in the legacy app user registry.
Association admins see their current association only.
Use **Manage in Clerk** to open the organization profile. Administrators need membership in each organization they manage.
Refresh admissions after changes. Local/mock mode retains its debugging forms.

Signed-in users can request access using an association code. Admins see pending
requests in the dashboard and navigation. Invite the requester through Clerk;
after acceptance, refresh and mark the request resolved. Resolution checks for a
recognized membership before removing the request. Denying a request does not
revoke an existing Clerk membership. These app requests are distinct from
Clerk's verified-domain membership requests.

Email delivery requires Cloudflare Email Sending onboarding for your sender
domain. Set `ACCESS_REQUEST_FROM` in `wrangler.frontdoor.toml` to an authorized
sender address; the `ACCESS_REQUEST_EMAIL` binding is already declared. See
[Email Sending setup](https://developers.cloudflare.com/email-service/get-started/send-emails/).
Requests remain available in-app if email is unconfigured or delivery fails;
admins can retry delivery. Emails go to verified primary addresses of current
organization admins. Successful recipients are recorded so a sequential retry
skips them. KV does not provide exactly-once delivery under concurrent retries.
No live emails or deployment were performed during implementation.

## Fixing a Missing Organization Mapping

`ACCESS_ORGANIZATION_UNMAPPED` means the selected Clerk organization ID is absent
from the running `RENTAL_KV` association registry. It is not a KV permission
failure. A missing membership returns `ACCESS_ORGANIZATION_ACCESS_DENIED`; an
unrecognized role returns `ACCESS_ORGANIZATION_ROLE_UNSUPPORTED`.

Updating Clerk settings, creating a Clerk org, or editing `associations.json`
does not populate the registry. The gateway reads `associations:index` and each
`associations:{tenant_id}` record from its configured KV namespace. Local and
remote KV are separate; both Workers must use the same registry namespace.

For an existing association, read its complete record, preserve the tenant ID
and other fields, and set `clerk_organization_id` to the ID shown on the app's
connection-error screen. For example, in local development:

```bash
npx wrangler kv key get associations:demo-association --binding RENTAL_KV --config wrangler.frontdoor.toml --local --preview
# Save the complete returned JSON as /tmp/association.json, then edit its clerk_organization_id.
npx wrangler kv key put associations:demo-association --path /tmp/association.json --binding RENTAL_KV --config wrangler.frontdoor.toml --local --preview
```

Local development uses the configured preview namespace ID, so include `--preview`
on local KV commands. For hosted production KV, explicitly use `--remote --preview false`
with the intended deployment's config.
Existing indexed associations need only the record updated. Provisioning a new
association also requires adding its tenant ID to `associations:index` without
removing other entries. Do not map a new organization to arbitrary existing
rental data; verify which association owns that organization first. Ensure each
org maps uniquely, then use **Check association access** in the app.

Observed local state during this review: only `demo-association` is indexed and
its organization ID is empty. The separate `associations.json` describes `mgw`;
it has not initialized this local registry. No registry mapping was changed,
since connecting those different tenant IDs would require deciding which rental
data the organization owns. Hosted registry state was not inspected.
