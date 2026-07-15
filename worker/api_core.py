from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import parse_qs

from domain import (
    DomainError,
    EMAIL_PATTERN,
    ENTITY_TYPES,
    PHONE_PATTERN,
    SERVICE_CONDITIONS,
    add_history,
    add_service_history,
    clean_text,
    create_record,
    delete_record,
    demo_records,
    email_hash,
    export_package,
    find_record,
    hydrate,
    import_package,
    reject_contact_reference_pii,
    return_rental,
    summary,
    update_record,
    utc_now,
)
from migration import instrument_export_package, merge_hitobito_members, merge_instruments


class TenantRepository(Protocol):
    async def load_tenant(self, tenant_id: str) -> dict[str, list[dict[str, Any]]]:
        ...

    async def save_tenant(self, tenant_id: str, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        ...

    async def load_metadata(self, tenant_id: str) -> dict[str, Any]:
        ...

    async def tenant_exists(self, tenant_id: str) -> bool:
        ...

    async def list_associations(self) -> list[dict[str, Any]]:
        ...

    async def load_association(self, tenant_id: str) -> dict[str, Any] | None:
        ...

    async def save_association(self, tenant_id: str, association: dict[str, Any]) -> dict[str, Any]:
        ...

    async def list_users(self) -> list[dict[str, Any]]:
        ...

    async def load_user(self, user_id: str) -> dict[str, Any] | None:
        ...

    async def save_user(self, user_id: str, user: dict[str, Any]) -> dict[str, Any]:
        ...

    async def delete_user(self, user_id: str) -> dict[str, Any] | None:
        ...

    async def list_access_requests(self) -> list[dict[str, Any]]:
        ...

    async def load_access_request(self, request_id: str) -> dict[str, Any] | None:
        ...

    async def delete_access_request(self, request_id: str) -> dict[str, Any] | None:
        ...


TENANT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}$")
TENANT_ID_MESSAGE = "tenant id must use 2-63 lowercase letters, numbers, hyphens, or underscores"
ALLOWED_ROLES = {"viewer", "operator", "admin"}
USER_GLOBAL_ROLES = {"none", "reader", "operator", "admin", "platform_admin"}
USER_TENANT_ROLES = {"reader", "operator", "admin"}
USER_ACCESS_PROFILES = {"full", "basic"}
USER_STATUSES = {"active", "disabled"}
SIGNED_CONTEXT_MAX_AGE_SECONDS = 60 * 60
EXPECTED_REVISION_HEADER = "x-rental-expected-revision"
ASSOCIATION_STATUSES = {"active", "paused", "archived"}
PLATFORM_TENANT_ID = "platform-admin"


@dataclass(frozen=True)
class RequestContext:
    tenant_id: str
    actor_id: str = "system"
    role: str = "operator"
    mode: str = "local"
    access_profile: str = "full"
    member_id: str | None = None
    user_email: str | None = None
    global_role: str = "none"
    tenant_count: int = 1
    tenant_switchable: bool = False


def parse_api_path(pathname: str) -> list[str]:
    parts = [part for part in pathname.split("/") if part]
    if not parts or parts[0] != "api":
        return []
    return parts[1:]


def is_api_request_path(pathname: str) -> bool:
    return pathname == "/api" or pathname.startswith("/api/")


def is_valid_tenant_id(tenant_id: str | None) -> bool:
    return bool(tenant_id and TENANT_ID_PATTERN.fullmatch(tenant_id))


def validate_tenant_id(tenant_id: str | None) -> str | None:
    if is_valid_tenant_id(tenant_id):
        return None
    return TENANT_ID_MESSAGE


def validate_actor_id(actor_id: Any) -> str | None:
    value = clean_text(actor_id)
    if not value:
        return "actor_id is required"
    if EMAIL_PATTERN.search(value):
        return "actor_id must be opaque, not an email address"
    if PHONE_PATTERN.search(value):
        return "actor_id must be opaque, not a phone number"
    return None


def validate_member_link_id(member_id: Any) -> str | None:
    value = clean_text(member_id)
    if not value:
        return "member_id is required for member links"
    if EMAIL_PATTERN.search(value):
        return "member_id must be opaque, not an email address"
    if PHONE_PATTERN.search(value):
        return "member_id must be opaque, not a phone number"
    return None


def optional_text(value: Any) -> str | None:
    text = clean_text(value)
    return text or None


def normalize_email(value: Any) -> str:
    email = clean_text(value).lower()
    if not email or not EMAIL_PATTERN.fullmatch(email):
        raise DomainError("email must be a valid email address")
    return email


def optional_context_email(value: Any, message: str) -> tuple[str | None, str | None]:
    email = clean_text(value)
    if not email:
        return None, None
    try:
        return normalize_email(email), None
    except DomainError:
        return None, message


def normalize_user_id(value: Any) -> str:
    user_id = clean_text(value)
    if not re.fullmatch(r"user_[a-f0-9]{16,64}", user_id):
        raise DomainError("user id is invalid", 404)
    return user_id


def normalize_access_request_id(value: Any) -> str:
    request_id = clean_text(value)
    if not re.fullmatch(r"access_request:[a-f0-9]{24}", request_id):
        raise DomainError("access request id is invalid", 404)
    return request_id


def user_id_for_email(email: str) -> str:
    return f"user_{hashlib.sha256(email.encode('utf-8')).hexdigest()[:24]}"


def normalize_tenant_role_items(value: Any) -> list[dict[str, str]]:
    if value in (None, ""):
        return []
    if isinstance(value, dict):
        source = [{"tenant_id": tenant_id, "role": role} for tenant_id, role in value.items()]
    elif isinstance(value, list):
        source = value
    else:
        raise DomainError("tenant_roles must be a list or object")
    roles = []
    seen: set[str] = set()
    for item in source:
        if not isinstance(item, dict):
            raise DomainError("tenant_roles entries must be objects")
        tenant_id = clean_text(item.get("tenant_id"))
        error = validate_tenant_id(tenant_id)
        if error:
            raise DomainError(error)
        role = clean_text(item.get("role")).lower()
        if role not in USER_TENANT_ROLES:
            raise DomainError("tenant role must be reader, operator, or admin")
        if tenant_id not in seen:
            roles.append({"tenant_id": tenant_id, "role": role})
            seen.add(tenant_id)
    return roles


def normalize_member_link_items(value: Any) -> list[dict[str, str]]:
    if value in (None, ""):
        return []
    if isinstance(value, dict):
        source = [{"tenant_id": tenant_id, "member_id": member_id} for tenant_id, member_id in value.items()]
    elif isinstance(value, list):
        source = value
    else:
        raise DomainError("member_links must be a list or object")
    links = []
    seen: set[str] = set()
    for item in source:
        if not isinstance(item, dict):
            raise DomainError("member_links entries must be objects")
        tenant_id = clean_text(item.get("tenant_id"))
        error = validate_tenant_id(tenant_id)
        if error:
            raise DomainError(error)
        member_id = clean_text(item.get("member_id"))
        member_error = validate_member_link_id(member_id)
        if member_error:
            raise DomainError(member_error)
        if tenant_id not in seen:
            links.append({"tenant_id": tenant_id, "member_id": member_id})
            seen.add(tenant_id)
    return links


def normalize_user_access(
    payload: dict[str, Any],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    reject_contact_reference_pii(payload, "display_name")
    email = normalize_email(payload.get("email", current.get("email")))
    if current.get("email") and email != current["email"]:
        raise DomainError("email cannot be changed for an existing user")
    global_role = clean_text(payload.get("global_role", current.get("global_role", "none")), "none").lower()
    if global_role not in USER_GLOBAL_ROLES:
        raise DomainError("global_role must be none, reader, operator, admin, or platform_admin")
    access_profile = clean_text(payload.get("access_profile", current.get("access_profile", "full")), "full").lower()
    if access_profile not in USER_ACCESS_PROFILES:
        raise DomainError("access_profile must be full or basic")
    status = clean_text(payload.get("status", current.get("status", "active")), "active").lower()
    if status not in USER_STATUSES:
        raise DomainError("status must be active or disabled")
    now = utc_now()
    return {
        "id": current.get("id") or user_id_for_email(email),
        "email": email,
        "display_name": optional_text(payload.get("display_name", current.get("display_name"))),
        "status": status,
        "global_role": global_role,
        "access_profile": access_profile,
        "tenant_roles": normalize_tenant_role_items(payload.get("tenant_roles", current.get("tenant_roles", []))),
        "member_links": normalize_member_link_items(payload.get("member_links", current.get("member_links", []))),
        "created_at": current.get("created_at") or now,
        "updated_at": now,
    }


def frontdoor_user_assignment(user: dict[str, Any]) -> dict[str, str]:
    value = {
        "access_profile": user.get("access_profile", "full"),
        "email": user["email"],
        "global_role": user.get("global_role", "none"),
        "member_links": user.get("member_links", []),
        "status": user.get("status", "active"),
        "tenant_roles": user.get("tenant_roles", []),
    }
    tenant_roles = value["tenant_roles"]
    if tenant_roles:
        value["default_tenant"] = tenant_roles[0]["tenant_id"]
    return {
        "key": f"user:{user['email']}",
        "value": json.dumps(value, separators=(",", ":"), sort_keys=True),
    }


def normalize_association(
    payload: dict[str, Any],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    low_pii_fields = ("display_name", "short_name", "contact_ref", "hitobito_group_ref", "inventory_ref", "note")
    reject_contact_reference_pii(
        {field: payload.get(field, current.get(field)) for field in low_pii_fields},
        *low_pii_fields,
    )
    tenant_id = clean_text(current.get("tenant_id") or payload.get("tenant_id"))
    error = validate_tenant_id(tenant_id)
    if error:
        raise DomainError(error, 400)

    status = clean_text(payload.get("status", current.get("status", "active")), "active")
    if status not in ASSOCIATION_STATUSES:
        raise DomainError("status must be active, paused, or archived")

    display_name = clean_text(payload.get("display_name", current.get("display_name")))
    if not display_name:
        display_name = tenant_id.replace("-", " ").replace("_", " ").title()

    now = utc_now()
    return {
        "tenant_id": tenant_id,
        "display_name": display_name,
        "short_name": optional_text(payload.get("short_name", current.get("short_name"))),
        "status": status,
        "region": optional_text(payload.get("region", current.get("region"))),
        "locale": clean_text(payload.get("locale", current.get("locale", "de-CH")), "de-CH"),
        "contact": optional_text(payload.get("contact", current.get("contact"))),
        "contact_ref": optional_text(payload.get("contact_ref", current.get("contact_ref"))),
        "hitobito_group_ref": optional_text(payload.get("hitobito_group_ref", current.get("hitobito_group_ref"))),
        "inventory_ref": optional_text(payload.get("inventory_ref", current.get("inventory_ref"))),
        "note": optional_text(payload.get("note", current.get("note"))),
        "created_at": current.get("created_at") or now,
        "updated_at": now,
    }


def encode_signed_context_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def sign_context_payload(encoded_payload: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).hexdigest()


def signed_context_headers(payload: dict[str, Any], secret: str) -> dict[str, str]:
    encoded = encode_signed_context_payload(payload)
    return {
        "x-rental-context": encoded,
        "x-rental-context-signature": sign_context_payload(encoded, secret),
    }


def _decode_signed_context(encoded_payload: str) -> dict[str, Any]:
    padding = "=" * (-len(encoded_payload) % 4)
    raw = base64.urlsafe_b64decode((encoded_payload + padding).encode("ascii"))
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("signed context must be a JSON object")
    return data


def context_from_signed_headers(
    path_tenant_id: str | None,
    normalized_headers: dict[str, str],
    secret: str | None,
) -> tuple[RequestContext | None, str | None]:
    if not secret:
        return None, "missing signed tenant context secret"
    encoded = normalized_headers.get("x-rental-context")
    signature = normalized_headers.get("x-rental-context-signature")
    if not encoded or not signature:
        return None, "missing signed tenant context"
    expected = sign_context_payload(encoded, secret)
    if not hmac.compare_digest(signature, expected):
        return None, "invalid signed tenant context"

    try:
        payload = _decode_signed_context(encoded)
    except Exception:
        return None, "invalid signed tenant context"

    tenant_id = str(payload.get("tenant_id") or "")
    error = validate_tenant_id(tenant_id)
    if error:
        return None, error
    if path_tenant_id and tenant_id != path_tenant_id:
        return None, "tenant context does not match route"

    role = str(payload.get("role") or "viewer")
    if role not in ALLOWED_ROLES:
        return None, "invalid role in signed tenant context"

    issued_at = payload.get("issued_at")
    if issued_at is not None:
        try:
            age = time.time() - float(issued_at)
        except (TypeError, ValueError):
            return None, "invalid signed tenant context timestamp"
        if age < -60 or age > SIGNED_CONTEXT_MAX_AGE_SECONDS:
            return None, "expired signed tenant context"

    actor_id = str(payload.get("actor_id") or "authenticated-user")
    actor_error = validate_actor_id(actor_id)
    if actor_error:
        return None, actor_error
    access_profile = str(payload.get("access_profile") or "full")
    if access_profile not in USER_ACCESS_PROFILES:
        return None, "invalid access profile in signed tenant context"
    member_id = clean_text(payload.get("member_id")) or None
    if member_id:
        member_error = validate_member_link_id(member_id)
        if member_error:
            return None, member_error
    user_email, email_error = optional_context_email(payload.get("user_email"), "invalid user email in signed tenant context")
    if email_error:
        return None, email_error
    global_role = str(payload.get("global_role") or "none")
    if global_role not in USER_GLOBAL_ROLES:
        return None, "invalid global role in signed tenant context"
    try:
        tenant_count = max(0, int(payload.get("tenant_count") or 0))
    except (TypeError, ValueError):
        return None, "invalid tenant count in signed tenant context"
    return RequestContext(
        tenant_id=tenant_id,
        actor_id=actor_id,
        role=role,
        mode="signed",
        access_profile=access_profile,
        member_id=member_id,
        user_email=user_email,
        global_role=global_role,
        tenant_count=tenant_count,
        tenant_switchable=bool(payload.get("tenant_switchable")),
    ), None


def context_from_headers(
    path_tenant_id: str | None,
    headers: dict[str, str],
    mode: str = "header",
    context_secret: str | None = None,
) -> tuple[RequestContext | None, str | None]:
    normalized = {key.lower(): value for key, value in headers.items()}
    mode = mode or "header"

    if mode in ("local", "open"):
        tenant_id = normalized.get("x-rental-tenant-id") or path_tenant_id or "demo-association"
        error = validate_tenant_id(tenant_id)
        if error:
            return None, error
        actor_id = normalized.get("x-rental-actor-id", "local-admin")
        actor_error = validate_actor_id(actor_id)
        if actor_error:
            return None, actor_error
        role = normalized.get("x-rental-role", "admin")
        if role not in ALLOWED_ROLES:
            return None, "invalid role in tenant context"
        access_profile = normalized.get("x-rental-access-profile", "full")
        if access_profile not in USER_ACCESS_PROFILES:
            return None, "invalid access profile in tenant context"
        member_id = normalized.get("x-rental-member-id")
        if member_id:
            member_error = validate_member_link_id(member_id)
            if member_error:
                return None, member_error
        user_email, email_error = optional_context_email(normalized.get("x-rental-user-email"), "invalid user email in tenant context")
        if email_error:
            return None, email_error
        return RequestContext(tenant_id=tenant_id, actor_id=actor_id, role=role, mode=mode, access_profile=access_profile, member_id=member_id, user_email=user_email), None

    if mode == "signed":
        return context_from_signed_headers(path_tenant_id, normalized, context_secret)

    tenant_id = normalized.get("x-rental-tenant-id")
    if not tenant_id:
        return None, "missing tenant context"
    error = validate_tenant_id(tenant_id)
    if error:
        return None, error
    if path_tenant_id and tenant_id != path_tenant_id:
        return None, "tenant context does not match route"

    actor_id = normalized.get("x-rental-actor-id")
    if not actor_id:
        actor_id = "authenticated-user"
    actor_error = validate_actor_id(actor_id)
    if actor_error:
        return None, actor_error
    role = normalized.get("x-rental-role", "viewer")
    if role not in ALLOWED_ROLES:
        return None, "invalid role in tenant context"
    access_profile = normalized.get("x-rental-access-profile", "full")
    if access_profile not in USER_ACCESS_PROFILES:
        return None, "invalid access profile in tenant context"
    member_id = normalized.get("x-rental-member-id")
    if member_id:
        member_error = validate_member_link_id(member_id)
        if member_error:
            return None, member_error
    user_email, email_error = optional_context_email(normalized.get("x-rental-user-email"), "invalid user email in tenant context")
    if email_error:
        return None, email_error
    return RequestContext(
        tenant_id=tenant_id,
        actor_id=actor_id,
        role=role,
        mode=mode,
        access_profile=access_profile,
        member_id=member_id,
        user_email=user_email,
    ), None


def can_write(context: RequestContext) -> bool:
    if context.access_profile == "basic":
        return False
    return context.role in ("admin", "operator")


def can_admin(context: RequestContext) -> bool:
    return context.access_profile != "basic" and context.role == "admin"


def can_manage_associations(context: RequestContext) -> bool:
    return can_admin(context) and (
        context.mode in ("local", "open")
        or context.tenant_id == PLATFORM_TENANT_ID
        or context.global_role == "platform_admin"
    )


def can_manage_users(context: RequestContext) -> bool:
    return can_admin(context)


def can_manage_all_users(context: RequestContext) -> bool:
    return can_manage_associations(context)


def user_has_tenant(user: dict[str, Any], tenant_id: str) -> bool:
    return any(item.get("tenant_id") == tenant_id for item in user.get("tenant_roles", [])) or any(
        item.get("tenant_id") == tenant_id for item in user.get("member_links", [])
    )


def tenant_scoped_user(user: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    return {
        **user,
        "global_role": "none",
        "tenant_roles": [item for item in user.get("tenant_roles", []) if item.get("tenant_id") == tenant_id],
        "member_links": [item for item in user.get("member_links", []) if item.get("tenant_id") == tenant_id],
    }


def normalize_tenant_admin_user_access(payload: dict[str, Any], context: RequestContext, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    scoped_existing = tenant_scoped_user(existing, context.tenant_id) if existing else None
    tenant_role = clean_text(payload.get("tenant_role", "reader")).lower()
    tenant_roles_payload = payload.get("tenant_roles")
    if tenant_roles_payload not in (None, ""):
        tenant_roles = normalize_tenant_role_items(tenant_roles_payload)
        if any(item["tenant_id"] != context.tenant_id for item in tenant_roles):
            raise DomainError("tenant admin can only manage users for their tenant")
        if len(tenant_roles) > 1:
            raise DomainError("tenant admin can set only one tenant role")
        if tenant_roles:
            tenant_role = tenant_roles[0]["role"]
    if tenant_role not in USER_TENANT_ROLES:
        raise DomainError("tenant role must be reader, operator, or admin")
    member_links_payload = payload.get("member_links", scoped_existing.get("member_links", []) if scoped_existing else [])
    member_links = normalize_member_link_items(member_links_payload)
    if any(item["tenant_id"] != context.tenant_id for item in member_links):
        raise DomainError("tenant admin can only manage member links for their tenant")
    user = normalize_user_access({
        **payload,
        "global_role": "none",
        "tenant_roles": [{"tenant_id": context.tenant_id, "role": tenant_role}],
        "member_links": member_links,
    }, scoped_existing)
    if existing:
        other_roles = [item for item in existing.get("tenant_roles", []) if item.get("tenant_id") != context.tenant_id]
        other_links = [item for item in existing.get("member_links", []) if item.get("tenant_id") != context.tenant_id]
        user["global_role"] = existing.get("global_role", "none")
        user["tenant_roles"] = other_roles + user["tenant_roles"]
        user["member_links"] = other_links + user["member_links"]
        user["created_at"] = existing.get("created_at", user["created_at"])
    return user


def context_payload(context: RequestContext) -> dict[str, Any]:
    return {
        "tenant_id": context.tenant_id,
        "actor_id": context.actor_id,
        "role": context.role,
        "mode": context.mode,
        "user_email": context.user_email,
        "tenant_locked": context.mode not in ("local", "open"),
        "capabilities": {
            "read": True,
            "write": can_write(context),
            "admin": can_admin(context),
            "platform_admin": can_manage_associations(context),
            "access_profile": context.access_profile,
        },
        "global_role": context.global_role,
        "has_global_role": context.global_role != "none",
        "tenant_count": context.tenant_count,
        "tenant_switchable": context.tenant_switchable or context.global_role != "none" or context.tenant_count > 1,
    }


async def tenant_metadata(repo: TenantRepository, tenant_id: str) -> dict[str, Any]:
    load_metadata = getattr(repo, "load_metadata", None)
    if load_metadata is None:
        return {"tenant_id": tenant_id, "revision": 0, "updated_at": None}
    metadata = await load_metadata(tenant_id)
    return {"tenant_id": tenant_id, "revision": metadata.get("revision", 0), "updated_at": metadata.get("updated_at")}


async def tenant_summary(repo: TenantRepository, tenant_id: str, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {**summary(records), "meta": await tenant_metadata(repo, tenant_id)}


async def scoped_tenant_summary(
    repo: TenantRepository,
    tenant_id: str,
    records: dict[str, list[dict[str, Any]]],
    context: RequestContext,
) -> dict[str, Any]:
    data = basic_customer_summary(records, context) if context.access_profile == "basic" else summary(records)
    return {**data, "meta": await tenant_metadata(repo, tenant_id)}


async def ensure_association(repo: TenantRepository, tenant_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
    load_association = getattr(repo, "load_association", None)
    save_association = getattr(repo, "save_association", None)
    if load_association is None or save_association is None:
        return None
    existing = await load_association(tenant_id)
    if existing is not None and not payload:
        return existing
    association = normalize_association({"tenant_id": tenant_id, **(payload or {})}, existing)
    return await save_association(tenant_id, association)


async def save_tenant_mutation(
    repo: TenantRepository,
    tenant_id: str,
    records: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    metadata = await repo.save_tenant(tenant_id, records)
    await ensure_association(repo, tenant_id)
    return metadata


async def association_with_meta(repo: TenantRepository, association: dict[str, Any]) -> dict[str, Any]:
    tenant_id = association["tenant_id"]
    return {**association, "meta": await tenant_metadata(repo, tenant_id)}


def object_payload(payload: Any, message: str = "request payload must be an object") -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise DomainError(message)
    return payload


def association_payload_from_import(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    display_name = clean_text(payload.get("display_name") or payload.get("association_name"))
    return {"display_name": display_name} if display_name else None


async def handle_admin_request(
    method: str,
    parts: list[str],
    payload: Any,
    repo: TenantRepository,
    context: RequestContext,
) -> tuple[int, Any]:
    if not can_admin(context):
        return 403, {"error": "admin role required"}
    if len(parts) < 2 or parts[1] not in ("associations", "users", "access-requests"):
        return 404, {"error": "route not found"}

    if parts[1] == "users":
        return await handle_admin_users_request(method, parts, payload, repo, context)

    if parts[1] == "access-requests":
        return await handle_admin_access_requests(method, parts, payload, repo, context)

    if not can_manage_associations(context):
        return 403, {"error": "platform admin required"}

    if len(parts) == 2:
        if method == "GET":
            associations = await repo.list_associations()
            data = [await association_with_meta(repo, association) for association in associations]
            return 200, {"data": data}
        if method == "POST":
            association = normalize_association(object_payload(payload))
            saved = await repo.save_association(association["tenant_id"], association)
            return 201, {"data": await association_with_meta(repo, saved)}
        return 405, {"error": "method not allowed"}

    if len(parts) != 3:
        return 404, {"error": "route not found"}
    tenant_id = parts[2]
    error = validate_tenant_id(tenant_id)
    if error:
        return 404, {"error": error}
    existing = await repo.load_association(tenant_id)
    if method == "GET":
        if not existing:
            return 404, {"error": "association not found"}
        return 200, {"data": await association_with_meta(repo, existing)}
    if method == "PUT":
        association = normalize_association({**object_payload(payload), "tenant_id": tenant_id}, existing)
        saved = await repo.save_association(tenant_id, association)
        return 200, {"data": await association_with_meta(repo, saved)}
    return 405, {"error": "method not allowed"}


async def handle_admin_access_requests(
    method: str,
    parts: list[str],
    payload: Any,
    repo: TenantRepository,
    context: RequestContext,
) -> tuple[int, Any]:
    if not can_manage_users(context):
        return 403, {"error": "admin role required"}
    if len(parts) == 2:
        if method != "GET":
            return 405, {"error": "method not allowed"}
        requests = await repo.list_access_requests()
        if not can_manage_all_users(context):
            requests = [item for item in requests if item.get("tenant_id") == context.tenant_id]
        return 200, {"data": requests}
    if len(parts) != 4 or parts[3] not in ("approve", "deny"):
        return 404, {"error": "route not found"}
    request_id = normalize_access_request_id(parts[2])
    request = await repo.load_access_request(request_id)
    if not request:
        return 404, {"error": "access request not found"}
    if not can_manage_all_users(context) and request.get("tenant_id") != context.tenant_id:
        return 404, {"error": "access request not found"}
    if method != "POST":
        return 405, {"error": "method not allowed"}
    if parts[3] == "deny":
        deleted = await repo.delete_access_request(request_id)
        return 200, {"denied": request_id, "data": deleted}

    body = object_payload(payload)
    tenant_role = clean_text(body.get("tenant_role", "reader")).lower()
    member_links = body.get("member_links", [])
    existing = await repo.load_user(user_id_for_email(request["email"]))
    default_access_profile = existing.get("access_profile", "basic") if existing else "basic"
    access_profile = clean_text(body.get("access_profile", default_access_profile), default_access_profile).lower()
    if can_manage_all_users(context):
        tenant_roles = body.get("tenant_roles")
        if tenant_roles is None:
            tenant_roles = [item for item in (existing or {}).get("tenant_roles", []) if item.get("tenant_id") != request["tenant_id"]]
            tenant_roles.append({"tenant_id": request["tenant_id"], "role": tenant_role})
        user = normalize_user_access({
            "email": request["email"],
            "status": "active",
            "global_role": clean_text(body.get("global_role", "none"), "none").lower(),
            "access_profile": access_profile,
            "tenant_roles": tenant_roles,
            "member_links": member_links,
        }, existing)
    else:
        user = normalize_tenant_admin_user_access({
            "email": request["email"],
            "status": "active",
            "access_profile": access_profile,
            "tenant_role": tenant_role,
            "member_links": member_links,
        }, context, existing)
    saved = await repo.save_user(user["id"], user)
    await repo.delete_access_request(request_id)
    return 200, {"approved": request_id, "data": saved if can_manage_all_users(context) else tenant_scoped_user(saved, context.tenant_id)}


async def handle_admin_users_request(
    method: str,
    parts: list[str],
    payload: Any,
    repo: TenantRepository,
    context: RequestContext,
) -> tuple[int, Any]:
    if not can_manage_users(context):
        return 403, {"error": "admin role required"}
    if len(parts) == 4 and parts[2] == "export" and parts[3] == "tenant-access":
        if not can_manage_all_users(context):
            return 403, {"error": "platform admin required"}
        if method != "GET":
            return 405, {"error": "method not allowed"}
        users = await repo.list_users()
        return 200, {
            "schema": "tenant-access-kv-bulk",
            "data": [frontdoor_user_assignment(user) for user in users],
            "summary": {"users": len(users)},
        }

    if len(parts) == 2:
        if method == "GET":
            users = await repo.list_users()
            if not can_manage_all_users(context):
                users = [tenant_scoped_user(user, context.tenant_id) for user in users if user_has_tenant(user, context.tenant_id)]
            return 200, {"data": users}
        if method == "POST":
            user = normalize_user_access(object_payload(payload)) if can_manage_all_users(context) else normalize_tenant_admin_user_access(object_payload(payload), context)
            saved = await repo.save_user(user["id"], user)
            return 201, {"data": saved}
        return 405, {"error": "method not allowed"}

    if len(parts) != 3:
        return 404, {"error": "route not found"}
    user_id = normalize_user_id(parts[2])
    existing = await repo.load_user(user_id)
    if method == "GET":
        if not existing:
            return 404, {"error": "user not found"}
        if not can_manage_all_users(context):
            if not user_has_tenant(existing, context.tenant_id):
                return 404, {"error": "user not found"}
            return 200, {"data": tenant_scoped_user(existing, context.tenant_id)}
        return 200, {"data": existing}
    if method == "PUT":
        if not existing:
            return 404, {"error": "user not found"}
        if not can_manage_all_users(context) and not user_has_tenant(existing, context.tenant_id):
            return 404, {"error": "user not found"}
        user = normalize_user_access({**object_payload(payload), "id": user_id}, existing) if can_manage_all_users(context) else normalize_tenant_admin_user_access({**object_payload(payload), "id": user_id}, context, existing)
        if user["id"] != user_id:
            raise DomainError("email cannot be changed for an existing user")
        saved = await repo.save_user(user_id, user)
        return 200, {"data": saved if can_manage_all_users(context) else tenant_scoped_user(saved, context.tenant_id)}
    if method == "DELETE":
        if not can_manage_all_users(context):
            if not existing or not user_has_tenant(existing, context.tenant_id):
                return 404, {"error": "user not found"}
            updated = {
                **existing,
                "tenant_roles": [item for item in existing.get("tenant_roles", []) if item.get("tenant_id") != context.tenant_id],
                "member_links": [item for item in existing.get("member_links", []) if item.get("tenant_id") != context.tenant_id],
                "updated_at": utc_now(),
            }
            if updated.get("tenant_roles") or updated.get("member_links") or updated.get("global_role", "none") != "none":
                saved = await repo.save_user(user_id, updated)
                return 200, {"deleted": user_id, "data": tenant_scoped_user(saved, context.tenant_id)}
        deleted = await repo.delete_user(user_id)
        if not deleted:
            return 404, {"error": "user not found"}
        return 200, {"deleted": user_id, "data": deleted}
    return 405, {"error": "method not allowed"}


async def revision_conflict_response(
    repo: TenantRepository,
    tenant_id: str,
    headers: dict[str, str] | None,
) -> tuple[int, dict[str, Any]] | None:
    if not headers:
        return None
    normalized = {key.lower(): value for key, value in headers.items()}
    expected = normalized.get(EXPECTED_REVISION_HEADER)
    if expected is None or expected == "":
        return None
    try:
        expected_revision = int(expected)
    except ValueError:
        return 400, {"error": "expected revision must be an integer"}

    metadata = await tenant_metadata(repo, tenant_id)
    current_revision = int(metadata.get("revision", 0))
    if expected_revision != current_revision:
        return 409, {
            "error": f"tenant revision conflict: expected {expected_revision}, current {current_revision}",
            "meta": metadata,
        }
    return None


def basic_instrument_ids(records: dict[str, list[dict[str, Any]]], member_id: str) -> set[str]:
    return {
        rental.get("instrument_id")
        for rental in records["rentals"]
        if rental.get("member_id") == member_id and rental.get("instrument_id")
    }


def basic_member_id(records: dict[str, list[dict[str, Any]]], context: RequestContext) -> str | None:
    if context.member_id:
        return context.member_id
    if not context.user_email:
        return None
    user_hash = email_hash(context.user_email)
    match = next(
        (
            item for item in records["members"]
            if item.get("is_active") is not False and item.get("access_email_hash") == user_hash
        ),
        None,
    )
    return match.get("id") if match else None


def basic_customer_summary(records: dict[str, list[dict[str, Any]]], context: RequestContext) -> dict[str, Any]:
    member_id = basic_member_id(records, context)
    if not member_id:
        return {
            "instruments": 0,
            "available_instruments": 0,
            "members": 0,
            "active_rentals": 0,
            "overdue_rentals": 0,
            "service_attention": 0,
        }
    instrument_ids = basic_instrument_ids(records, member_id)
    hydrated = hydrate(records)
    active_rentals = [
        item for item in hydrated["rentals"]
        if item.get("member_id") == member_id and item.get("status") != "returned"
    ]
    return {
        "instruments": len(instrument_ids),
        "available_instruments": 0,
        "members": 1,
        "active_rentals": len(active_rentals),
        "overdue_rentals": len([item for item in active_rentals if item.get("status") == "overdue"]),
        "service_attention": len([
            item for item in hydrated["instruments"]
            if item.get("id") in instrument_ids and item.get("service_condition") in ("watch", "needs_service", "in_service")
        ]),
    }


def basic_access_matches(entity: str, item: dict[str, Any], records: dict[str, list[dict[str, Any]]], context: RequestContext) -> bool:
    if context.access_profile != "basic":
        return True
    member_id = basic_member_id(records, context)
    if not member_id:
        return False
    instrument_ids = basic_instrument_ids(records, member_id)
    if entity == "members":
        return item.get("id") == member_id
    if entity == "rentals":
        return item.get("member_id") == member_id
    if entity == "instruments":
        return item.get("id") in instrument_ids
    if entity == "service_records":
        return item.get("instrument_id") in instrument_ids
    if entity == "history":
        return item.get("member_id") == member_id or item.get("instrument_id") in instrument_ids
    return False


def filtered_collection(entity: str, records: dict[str, list[dict[str, Any]]], query: str, context: RequestContext) -> list[dict[str, Any]]:
    hydrated = hydrate(records)
    items = [item for item in hydrated[entity] if basic_access_matches(entity, item, records, context)]
    params = parse_qs(query)
    search = (params.get("search") or [""])[0].lower().strip()
    status = (params.get("status") or [""])[0].lower().strip()

    if search:
        items = [item for item in items if search in json.dumps(item, default=str).lower()]
    if status:
        items = [item for item in items if collection_status_matches(entity, item, status)]
    return items


def scoped_record(entity: str, records: dict[str, list[dict[str, Any]]], record_id: str, context: RequestContext) -> dict[str, Any]:
    hydrated = hydrate(records)
    record = find_record(hydrated, entity, record_id)
    if not basic_access_matches(entity, record, records, context):
        raise DomainError("record not found", 404)
    return record


def collection_status_matches(entity: str, item: dict[str, Any], status: str) -> bool:
    if entity == "instruments":
        if status in SERVICE_CONDITIONS:
            return item.get("service_condition") == status
        if status == "service_due_soon":
            return item.get("service_due_status") == "due_soon"
        if status == "service_overdue":
            return item.get("service_due_status") == "overdue"
    if entity == "service_records":
        if status in SERVICE_CONDITIONS:
            return item.get("condition") == status
        if status == "service_due_soon":
            return item.get("service_due_status") == "due_soon"
        if status == "service_overdue":
            return item.get("service_due_status") == "overdue"
    if entity == "members":
        if status == "active":
            return item.get("is_active", True) is not False
        if status == "inactive":
            return item.get("is_active") is False
    return item.get("status") == status


async def handle_api_request(
    method: str,
    pathname: str,
    query: str,
    payload: Any,
    repo: TenantRepository,
    context: RequestContext | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    parts = parse_api_path(pathname)
    if not parts:
        return 404, {"error": "route not found"}

    if parts == ["health"]:
        return 200, {"ok": True, "service": "rental-worker"}

    if parts == ["context"] and method == "GET":
        context = context or RequestContext(tenant_id="demo-association", role="admin", mode="local")
        error = validate_tenant_id(context.tenant_id)
        if error:
            return 403, {"error": error}
        return 200, {**context_payload(context), "meta": await tenant_metadata(repo, context.tenant_id)}

    if parts[0] == "admin":
        context = context or RequestContext(tenant_id="demo-association", role="admin", mode="local")
        try:
            return await handle_admin_request(method, parts, payload, repo, context)
        except DomainError as exc:
            return exc.status, {"error": str(exc)}

    tenant_id = parts[0]
    error = validate_tenant_id(tenant_id)
    if error:
        return 404, {"error": error}
    context = context or RequestContext(tenant_id=tenant_id)
    if context.tenant_id != tenant_id:
        return 403, {"error": "tenant context does not match route"}

    try:
        if len(parts) == 2 and parts[1] == "bootstrap" and method == "POST":
            if not can_admin(context):
                return 403, {"error": "admin role required"}
            conflict = await revision_conflict_response(repo, tenant_id, headers)
            if conflict:
                return conflict
            records = demo_records(tenant_id)
            metadata = await save_tenant_mutation(repo, tenant_id, records)
            return 201, {"tenant_id": tenant_id, "records": hydrate(records), "summary": summary(records), "meta": metadata}

        records = await repo.load_tenant(tenant_id)

        if len(parts) == 2 and parts[1] == "summary" and method == "GET":
            return 200, await scoped_tenant_summary(repo, tenant_id, records, context)

        if len(parts) == 2 and parts[1] == "export" and method == "GET":
            if not can_admin(context):
                return 403, {"error": "admin role required"}
            package = export_package(records, tenant_id)
            package["meta"] = await tenant_metadata(repo, tenant_id)
            return 200, package

        if len(parts) == 2 and parts[1] == "import" and method in ("POST", "PUT"):
            if not can_admin(context):
                return 403, {"error": "admin role required"}
            conflict = await revision_conflict_response(repo, tenant_id, headers)
            if conflict:
                return conflict
            imported = import_package(payload, tenant_id)
            metadata = await repo.save_tenant(tenant_id, imported)
            await ensure_association(repo, tenant_id, association_payload_from_import(payload))
            return 200, {"tenant_id": tenant_id, "summary": summary(imported), "meta": metadata}

        if len(parts) < 2:
            return 404, {"error": "route not found"}

        if len(parts) == 4 and parts[1] == "members" and parts[2] == "import" and parts[3] == "hitobito" and method in ("POST", "PUT"):
            if not can_admin(context):
                return 403, {"error": "admin role required"}
            conflict = await revision_conflict_response(repo, tenant_id, headers)
            if conflict:
                return conflict
            report = merge_hitobito_members(records, tenant_id, payload)
            metadata = await save_tenant_mutation(repo, tenant_id, records)
            return 200, {"tenant_id": tenant_id, "summary": summary(records), "report": report, "meta": metadata}

        if len(parts) == 3 and parts[1] == "instruments" and parts[2] == "export" and method == "GET":
            if not can_admin(context):
                return 403, {"error": "admin role required"}
            package = instrument_export_package(records, tenant_id)
            package["meta"] = await tenant_metadata(repo, tenant_id)
            return 200, package

        if len(parts) == 3 and parts[1] == "instruments" and parts[2] == "import" and method in ("POST", "PUT"):
            if not can_admin(context):
                return 403, {"error": "admin role required"}
            conflict = await revision_conflict_response(repo, tenant_id, headers)
            if conflict:
                return conflict
            report = merge_instruments(records, tenant_id, payload)
            metadata = await save_tenant_mutation(repo, tenant_id, records)
            return 200, {"tenant_id": tenant_id, "summary": summary(records), "report": report, "meta": metadata}

        entity = parts[1]
        if entity not in ENTITY_TYPES:
            return 404, {"error": "route not found"}

        if len(parts) == 2:
            if method == "GET":
                return 200, {"data": filtered_collection(entity, records, query, context), "meta": await tenant_metadata(repo, tenant_id)}
            if method == "POST":
                if not can_write(context):
                    return 403, {"error": "operator role required"}
                conflict = await revision_conflict_response(repo, tenant_id, headers)
                if conflict:
                    return conflict
                payload = {**object_payload(payload), "actor": context.actor_id}
                record = create_record(records, tenant_id, entity, payload)
                metadata = await save_tenant_mutation(repo, tenant_id, records)
                return 201, {"data": record, "meta": metadata}
            return 405, {"error": "method not allowed"}

        record_id = parts[2]
        if len(parts) == 4 and entity == "rentals" and parts[3] == "return" and method == "POST":
            if not can_write(context):
                return 403, {"error": "operator role required"}
            conflict = await revision_conflict_response(repo, tenant_id, headers)
            if conflict:
                return conflict
            payload = {**object_payload(payload), "actor": context.actor_id}
            rental = return_rental(records, tenant_id, record_id, payload)
            metadata = await save_tenant_mutation(repo, tenant_id, records)
            return 200, {"data": rental, "meta": metadata}

        if len(parts) != 3:
            return 404, {"error": "route not found"}

        if method == "GET":
            return 200, {"data": scoped_record(entity, records, record_id, context), "meta": await tenant_metadata(repo, tenant_id)}
        if method == "PUT":
            if not can_write(context):
                return 403, {"error": "operator role required"}
            conflict = await revision_conflict_response(repo, tenant_id, headers)
            if conflict:
                return conflict
            payload = {**object_payload(payload), "actor": context.actor_id}
            record = update_record(records, tenant_id, entity, record_id, payload)
            metadata = await save_tenant_mutation(repo, tenant_id, records)
            return 200, {"data": record, "meta": metadata}
        if method == "DELETE":
            if not can_admin(context):
                return 403, {"error": "admin role required"}
            conflict = await revision_conflict_response(repo, tenant_id, headers)
            if conflict:
                return conflict
            cascaded_service_records: list[dict[str, Any]] = []
            if entity == "instruments":
                instrument = find_record(records, "instruments", record_id)
                cascaded_service_records = [
                    {**service_record, "instrument_name": instrument.get("name")}
                    for service_record in records["service_records"]
                    if service_record.get("instrument_id") == record_id
                ]
            record = delete_record(records, entity, record_id)
            response: dict[str, Any] = {"deleted": record_id, "data": record}
            if entity == "instruments":
                for service_record in cascaded_service_records:
                    add_service_history(records, tenant_id, service_record, "deleted", context.actor_id)
                if cascaded_service_records:
                    response["cascaded"] = {"service_records": cascaded_service_records}
            if entity == "rentals":
                add_history(records, tenant_id, record, "deleted", context.actor_id)
            if entity == "service_records":
                add_service_history(records, tenant_id, record, "deleted", context.actor_id)
            metadata = await save_tenant_mutation(repo, tenant_id, records)
            return 200, {**response, "meta": metadata}
        return 405, {"error": "method not allowed"}
    except DomainError as exc:
        return exc.status, {"error": str(exc)}
    except Exception:
        return 500, {"error": "unexpected error"}
