from __future__ import annotations

import json
import re
from urllib.parse import quote, urlencode

from domain import DomainError


def clerk_failure(method, path, status, body):
    # Never include query values, identity IDs, provider messages, or metadata.
    route = path.split("?", 1)[0]
    route = re.sub(r"^/users/[^/]+", "/users/{user}", route)
    route = re.sub(r"^/organizations/[^/]+", "/organizations/{organization}", route)
    route = re.sub(r"/(memberships|invitations)/[^/]+", r"/\1/{id}", route)
    known_codes = {
        "form_param_format_invalid", "form_param_value_invalid",
        "form_param_missing", "form_param_type_invalid", "form_param_nil",
        "resource_not_found", "api_key_invalid", "authentication_invalid",
        "authorization_invalid", "organization_role_not_found",
        "organization_membership_not_found", "rate_limit_exceeded",
    }
    codes = []
    try:
        errors = json.loads(body).get("errors", [])
        if isinstance(errors, list):
            codes = sorted({item["code"] for item in errors if isinstance(item, dict)
                            and isinstance(item.get("code"), str) and item["code"] in known_codes})
    except (ValueError, AttributeError, TypeError):
        pass
    detail = f"; code={','.join(codes)}" if codes else ""
    return (f"Clerk request failed: {method} {route} (HTTP {status}{detail}). "
            "Some changes may already have applied; review before retrying.")


class ClerkDirectory:
    """Reconcile rental access only; never delete or ban a Clerk account."""

    def __init__(self, secret: str | None, transport=None):
        self.secret = secret
        self.transport = transport

    async def request(self, method, path, payload=None, allow_missing=False):
        if not self.secret:
            raise DomainError("Clerk user management is not configured", 503)
        transport = self.transport
        if transport is None:
            from workers import fetch
            transport = fetch
        options = {
            "method": method,
            "headers": {"authorization": f"Bearer {self.secret}", "content-type": "application/json"},
        }
        if payload is not None:
            options["body"] = json.dumps(payload)
        try:
            response = await transport(f"https://api.clerk.com/v1{path}", **options)
            if allow_missing and response.status == 404:
                return None
            if not 200 <= response.status < 300:
                try:
                    body = await response.text()
                except Exception:
                    body = ""
                raise DomainError(clerk_failure(method, path, response.status, body), 502)
            text = await response.text()
            return json.loads(text) if text else None
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError("Clerk is unavailable. Retry the access update.", 503) from exc

    async def find_user(self, email, required=True):
        users = await self.request("GET", "/users?" + urlencode({"email_address[]": email, "limit": 100}))
        matches = []
        for user in users:
            primary = next((item for item in user.get("email_addresses", []) if item["id"] == user.get("primary_email_address_id")), None)
            if primary and primary.get("email_address", "").strip().lower() == email.lower() and primary.get("verification", {}).get("status") == "verified":
                matches.append(user)
        if len(matches) != 1:
            if not matches and not required:
                return None
            raise DomainError("No unique verified sign-in account found. Ask the user to sign in and verify this as their primary email first.", 409)
        return matches[0]

    @staticmethod
    def association_mappings(associations):
        mappings = {}
        used = set()
        for association in associations:
            organization = association.get("clerk_organization_id")
            if not organization:
                continue
            if organization in used or association["tenant_id"] in mappings:
                raise DomainError("Ambiguous Clerk association mapping", 409)
            used.add(organization)
            mappings[association["tenant_id"]] = organization
        return mappings

    async def read_access(self, user, associations):
        mappings = {org: tenant for tenant, org in self.association_mappings(associations).items()}
        account = await self.find_user(user["email"], required=False)
        result = {**user, "tenant_roles": [], "tenant_profiles": {}, "global_role": "none", "identity_status": "not_registered"}
        if account is None:
            return result
        if user.get("clerk_user_id") and user["clerk_user_id"] != account["id"]:
            return {**result, "identity_status": "account_changed"}
        result.update(clerk_user_id=account["id"], identity_status="registered")
        if account.get("banned") or account.get("locked"):
            result["status"] = "disabled"
        for membership in await self.memberships(account["id"]):
            tenant = mappings.get(membership["organization"]["id"])
            role = membership["role"]
            if tenant is None or role not in ("org:member", "org:reader", "org:operator", "org:admin"):
                continue
            result["tenant_roles"].append({"tenant_id": tenant, "role": "reader" if role == "org:member" else role.removeprefix("org:")})
            result["tenant_profiles"][tenant] = "basic" if role == "org:member" else "full"
        profiles = set(result["tenant_profiles"].values())
        result["access_profile"] = profiles.pop() if len(profiles) == 1 else "full"
        return result

    async def organization_memberships(self, organization_id):
        result = []
        offset = 0
        while True:
            page = await self.request("GET", f"/organizations/{quote(organization_id, safe='')}/memberships?limit=100&offset={offset}")
            result.extend(page["data"])
            if len(result) >= page["total_count"] or not page["data"]:
                return result
            offset += 100

    async def admissions(self, associations):
        mappings = self.association_mappings(associations)
        organizations, memberships, invitations = [], [], []
        for association in associations:
            tenant = association["tenant_id"]
            organization_id = mappings.get(tenant)
            if not organization_id:
                continue
            organization = await self.request("GET", f"/organizations/{quote(organization_id, safe='')}")
            organizations.append({
                "tenant_id": tenant, "id": organization_id,
                "name": organization.get("name") or association.get("display_name") or tenant,
                "image_url": organization.get("image_url") if organization.get("has_image") else None,
            })
            for membership in await self.organization_memberships(organization_id):
                user = membership.get("public_user_data") or {}
                role = membership.get("role", "")
                app_role = "reader" if role == "org:member" else role.removeprefix("org:")
                access = "basic" if role == "org:member" else "full" if role in ("org:reader", "org:operator", "org:admin") else "none"
                memberships.append({
                    "id": membership["id"], "organization_id": organization_id, "tenant_id": tenant,
                    "user_id": user.get("user_id"), "identifier": user.get("identifier", ""),
                    "display_name": " ".join(filter(None, [user.get("first_name"), user.get("last_name")])),
                    "clerk_role": role, "app_role": app_role if access != "none" else None,
                    "access_profile": access, "permissions": membership.get("permissions", []),
                    "created_at": membership.get("created_at"),
                })
            for invitation in await self.invitations(organization_id):
                invitations.append({
                    "id": invitation["id"], "organization_id": organization_id, "tenant_id": tenant,
                    "email": invitation.get("email_address", ""), "clerk_role": invitation.get("role", ""),
                    "status": invitation.get("status", "pending"),
                })
        return {"organizations": organizations, "memberships": memberships, "invitations": invitations}

    async def memberships(self, user_id):
        result = []
        offset = 0
        while True:
            page = await self.request("GET", f"/users/{quote(user_id, safe='')}/organization_memberships?limit=100&offset={offset}")
            result.extend(page["data"])
            if len(result) >= page["total_count"] or not page["data"]:
                return result
            offset += 100

    async def invitations(self, organization_id):
        result = []
        offset = 0
        while True:
            page = await self.request("GET", f"/organizations/{quote(organization_id, safe='')}/invitations?status=pending&limit=100&offset={offset}")
            result.extend(page["data"])
            if len(result) >= page["total_count"] or not page["data"]:
                return result
            offset += 100

    async def invite(self, organization_id, email, role):
        return await self.request("POST", f"/organizations/{quote(organization_id, safe='')}/invitations", {"email_address": email, "role": role})

    async def revoke_invitation(self, organization_id, invitation_id):
        return await self.request("POST", f"/organizations/{quote(organization_id, safe='')}/invitations/{quote(invitation_id, safe='')}/revoke", {})

    async def sync_access(self, user, associations, tenant_id=None, remove=False):
        # Resolve the complete plan before any write. Unmapped organizations are
        # outside this application's ownership and must never be modified.
        mappings = self.association_mappings(associations)
        targets = {key: value for key, value in mappings.items() if tenant_id is None or key == tenant_id}
        desired = {}
        for item in user.get("tenant_roles", []):
            tenant = item["tenant_id"]
            if tenant_id is not None and tenant != tenant_id:
                continue
            if remove or user.get("status") == "disabled" or user.get("tenant_statuses", {}).get(tenant) == "disabled":
                continue
            if tenant not in targets:
                raise DomainError(f"Association {tenant} has no Clerk organization mapping", 409)
            profile = user.get("tenant_profiles", {}).get(tenant, user.get("access_profile", "full"))
            desired[targets[tenant]] = "org:member" if profile == "basic" else f"org:{item['role']}"
        if remove and user.get("clerk_user_id"):
            account = await self.request("GET", f"/users/{quote(user['clerk_user_id'], safe='')}", allow_missing=True)
        else:
            account = await self.find_user(user["email"], required=not remove)
        if account is None:
            return None
        user_id = account["id"]
        if user.get("clerk_user_id") and user["clerk_user_id"] != user_id:
            raise DomainError("Sign-in account no longer matches this access profile", 409)
        current = {item["organization"]["id"]: item["role"] for item in await self.memberships(user_id)}
        managed = set(targets.values())
        # Revoke first. A retry reads current remote state and resumes safely.
        for organization in sorted((managed & current.keys()) - desired.keys()):
            await self.request("DELETE", f"/organizations/{quote(organization, safe='')}/memberships/{quote(user_id, safe='')}")
        for organization, role in desired.items():
            if current.get(organization) == role:
                continue
            path = f"/organizations/{quote(organization, safe='')}/memberships"
            if organization in current:
                await self.request("PATCH", f"{path}/{quote(user_id, safe='')}", {"role": role})
            else:
                await self.request("POST", path, {"user_id": user_id, "role": role})
        return user_id
