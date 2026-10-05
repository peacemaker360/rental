# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Association staff operate Rental Desk to manage shared instrument inventory, members, rentals, returns, and service work. Association members use a read-only view to see their own current and past rentals.

## Product Purpose

Rental Desk gives associations one bilingual place to run instrument lending and keep an accurate operational record. Success means staff can quickly find an instrument or member, issue and return rentals, track maintenance, and understand the current state of the collection, while members can verify their own rentals without gaining access to other records.

## Positioning

The product combines association-scoped instrument operations with member-linked rental visibility. Clerk organization membership establishes association access, and verified member identity limits basic users to rentals connected to their own member record.

## Operating Context

Staff work across inventory, member rosters, rentals, returns, service records, history, imports, and exports. Associations can import roster data from Hitobito and operate in English or German. The same interface serves administrators, operators, read-only staff, and members, with available views and actions determined by role.

## Capabilities and Constraints

- Static bilingual English/German web frontend with no frontend build step.
- Tenant-scoped data and authorization for multiple associations.
- Roles are viewer, operator, and admin; members receive a restricted read-only experience.
- Active rentals make instruments unavailable and prevent deleting the linked instrument or member until return.
- Instrument condition and service records support maintenance planning.
- Import, export, revision checks, and history support operational continuity.
- Rental data is low-PII rather than zero-PII; contact-like content is excluded from freeform notes and verified email is used only for access matching.

## Brand Commitments

The product name is Rental Desk. User-facing product copy is maintained in both English and German.

## Evidence on Hand

The implemented application, domain rules, tests, and architecture documentation are the source of truth. No testimonials, customer claims, or marketing evidence are present and future interface work must not fabricate them.

## Product Principles

- Make the current lending state obvious and actions fast for association staff.
- Give members clear access to their own rentals while preserving tenant and record privacy.
- Preserve operational history and prevent changes that would break active rental relationships.
- Keep English and German experiences equivalent.
- Prefer dependable, legible workflows over ornamental complexity.

## Accessibility & Inclusion

The interface supports keyboard navigation, visible focus, semantic controls, live status messaging, responsive layouts, and equivalent English/German UI text. New work must preserve those behaviors.
