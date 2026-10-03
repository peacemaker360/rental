# Rental Desk

Established 2026-10-03 from the current repository and owner interview. This file
defines intent, not a claim of completed implementation. [DESIGN.md](DESIGN.md)
defines presentation; [architecture](docs/architecture.md) documents the runtime.

## Platform

web

Responsive browser application for desktop and mobile. No native app required.

## Users

- Operators manage instruments, members, loans, returns, and maintenance.
- Association administrators oversee association-scoped access and admissions.
- Readers inspect association records without changing them.
- Members/borrowers see their own rentals, related instruments, and contact.
- The platform administrator/app operator provisions associations and connects
  them to Clerk organizations. This is an operational responsibility, not an
  existing global hosted role or permission to bypass organization membership.

**Owner-confirmed audience:** music associations and their members, not general
equipment rental businesses.

## Product Purpose

Answer: what do we own, who has it, when is it due, what condition is it in,
and what needs attention next? Preserve operational CRUD while improving usability,
privacy, and maintainability.

**Owner-confirmed next milestone:** reliable daily operations for the owner's
association before expanding to additional associations or commercial services.

## Positioning

An association-focused instrument rental desk with member-linked loans and service
history. It complements Hitobito/the existing roster rather than becoming another
contact database. This is product focus, not a claim of market uniqueness.

## Operating Context

1. Find instruments with search/filter/sort and inspect availability/history.
2. Loan an available instrument to a member; record dates and eventual return.
   A missing due date means an open-ended loan.
3. Record servicing, condition, job notes, and next service date as a journey.
4. Import Hitobito members without unnecessary contact information.
5. Import/export inventory and back up/restore tenant JSON.
6. Sign in to the correct association or personal rental view; sign-out clears
   displayed tenant data. Failures provide an appropriate next step.
7. Review join requests, manage membership/invitations in Clerk, then refresh
   admissions. Resolving an app request does not itself grant access.

**Owner-confirmed onboarding:** a platform administrator creates associations.
No public self-service association creation in this milestone. Map the rental
tenant explicitly to a Clerk organization ID; names/slugs are not identity.
Current hosted registry provisioning is app-operator work. A future central UI
requires a separate security decision, not restoration of retired global grants.

## Capabilities and Constraints

### Required Surface

Inventory, members, rentals, returns, service records, and history remain core.
Preserve instrument import/export, Hitobito member import, tenant backup/restore,
and legacy conversion. They are not expendable migration leftovers.

Provide EN/DE, responsive details, meaningful loading/error/empty states, clear
account actions, association contact, and a simple personal rental portal.

### Access Ownership

| Clerk membership | Rental access |
| --- | --- |
| `org:member` | Basic read-only own rentals and related instruments |
| `org:reader` | Association-wide read access |
| `org:operator` | Association-scoped operational writes |
| `org:admin` | Association administration and privileged operations |

Clerk owns hosted identity, memberships, roles, invitations, and account settings.
Rental Desk owns rental/service data, association mappings, and join requests.
Current hosted basic access matches verified email to member email hashes.
Legacy KV grants/member links and global metadata do not authorize hosted access.
Local/mock admin tools are not production permissions.

### Boundaries

- Static frontend, Python Worker API, JS auth gateway, and Cloudflare KV JSON;
  Clerk is the deliberate exception to the Cloudflare-only stack.
- Enforce association and basic-user isolation in the backend, not only the UI.
- Minimize duplicated roster PII. Hashes and request/contact data still need care;
  low-PII does not mean anonymous. Never expose credentials in diagnostics.
- Preserve availability through edits/imports; prevent double active loans and
  deletion of instruments/members with active rentals.
- Nullable dates must stay clearable. Reopening a returned rental still requires
  normal availability validation; blank input must not silently retain old data.
- History uses opaque actors. Exports and debug stores are sensitive.
- KV revision guards are not atomic transactions; do not promise race-free booking.
- Support offline mock and real Clerk development. Mock tests cannot prove live
  sign-in/out, invitation acceptance, or membership revocation.

### Not Committed For This Milestone

Payments, subscriptions, invoicing, a public marketplace, native apps, and a CRM.
Reservations and automated return reminders need separate decisions. Admissions
notifications do not imply a general messaging product.

## Brand Commitments

Retain Rental Desk and RD identity. Copy is direct, respectful, and operational.
EN/DE have equal functional coverage. General sign-in copy is provider-neutral;
explicit Clerk management handoffs may name Clerk. Do not blame users for
configuration/provider failures without evidence.

## Evidence on Hand

Implementation: `public/`, `worker/`, `frontdoor/`. Regression tests: `tests/`.
Historical screenshots identify recurring overflow, mobile navigation, detail
placement, and auth-state problems, not approved visual goldens.
[Clerk setup](docs/clerk-migration.md) describes current hosted ownership.

No measured adoption baseline, usability study, accessibility certification, or
completed production rollout is asserted. Demo fixtures are not customer evidence.
Older global-admin descriptions must not override the current hosted model.

## Product Principles

1. Make daily operations dependable before expanding scope.
2. Give members least privilege and a complete experience within it.
3. Keep tenancy and permission ownership explicit.
4. Minimize duplicated personal data while retaining useful records.
5. Preserve portability and practical local debugging.

## Next-Milestone Acceptance

- Real sign-in reaches the intended association without loops; sign-out clears data.
- Pending, unmapped, denied, and provider-error states explain distinct next steps.
- Inventory, loan, return, and service workflows work on desktop/mobile without
  lost edits, hidden details, or inaccessible commands.
- Basic users cannot retrieve other users' or associations' records through APIs.
- Inventory/tenant exports round-trip; Hitobito imports preserve references and
  omit disallowed contact data. Verify restore behavior before rollout.
- Automated checks and a real-association walkthrough pass, including live Clerk
  flows. Numeric adoption/performance targets have not been agreed.

## Open Decisions

- Member instrument requests/reservations: read-only is the current baseline,
  pending the second interview round.
- Retention/deletion periods, notification consent, and additional legal needs
  require owner decisions; do not invent policies.
- Future central provisioning UI, rollout scale, and commercial model remain open.
