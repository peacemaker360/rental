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

from .domain import (
    DomainError,
    ENTITY_TYPES,
    add_history,
    create_record,
    delete_record,
    demo_records,
    export_package,
    find_record,
    hydrate,
    import_package,
    return_rental,
    summary,
    update_record,
)


class TenantRepository(Protocol):
    async def load_tenant(self, tenant_id: str) -> dict[str, list[dict[str, Any]]]:
        ...

    async def save_tenant(self, tenant_id: str, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        ...

    async def load_metadata(self, tenant_id: str) -> dict[str, Any]:
        ...


TENANT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}$")
TENANT_ID_MESSAGE = "tenant id must use 2-63 lowercase letters, numbers, hyphens, or underscores"
ALLOWED_ROLES = {"viewer", "operator", "admin"}
SIGNED_CONTEXT_MAX_AGE_SECONDS = 60 * 60
EXPECTED_REVISION_HEADER = "x-rental-expected-revision"


@dataclass(frozen=True)
class RequestContext:
    tenant_id: str
    actor_id: str = "system"
    role: str = "operator"
    mode: str = "local"


def parse_api_path(pathname: str) -> list[str]:
    parts = [part for part in pathname.split("/") if part]
    if not parts or parts[0] != "api":
        return []
    return parts[1:]


def is_valid_tenant_id(tenant_id: str | None) -> bool:
    return bool(tenant_id and TENANT_ID_PATTERN.fullmatch(tenant_id))


def validate_tenant_id(tenant_id: str | None) -> str | None:
    if is_valid_tenant_id(tenant_id):
        return None
    return TENANT_ID_MESSAGE


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
    return RequestContext(tenant_id=tenant_id, actor_id=actor_id, role=role, mode="signed"), None


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
        role = normalized.get("x-rental-role", "admin")
        return RequestContext(tenant_id=tenant_id, actor_id=actor_id, role=role, mode=mode), None

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
    role = normalized.get("x-rental-role", "viewer")
    if role not in ALLOWED_ROLES:
        return None, "invalid role in tenant context"
    return RequestContext(tenant_id=tenant_id, actor_id=actor_id, role=role, mode=mode), None


def can_write(context: RequestContext) -> bool:
    return context.role in ("admin", "operator")


def can_admin(context: RequestContext) -> bool:
    return context.role == "admin"


def context_payload(context: RequestContext) -> dict[str, Any]:
    return {
        "tenant_id": context.tenant_id,
        "actor_id": context.actor_id,
        "role": context.role,
        "mode": context.mode,
        "tenant_locked": context.mode not in ("local", "open"),
        "capabilities": {
            "read": True,
            "write": can_write(context),
            "admin": can_admin(context),
        },
    }


async def tenant_metadata(repo: TenantRepository, tenant_id: str) -> dict[str, Any]:
    load_metadata = getattr(repo, "load_metadata", None)
    if load_metadata is None:
        return {"tenant_id": tenant_id, "revision": 0, "updated_at": None}
    metadata = await load_metadata(tenant_id)
    return {"tenant_id": tenant_id, "revision": metadata.get("revision", 0), "updated_at": metadata.get("updated_at")}


async def tenant_summary(repo: TenantRepository, tenant_id: str, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {**summary(records), "meta": await tenant_metadata(repo, tenant_id)}


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


def filtered_collection(entity: str, records: dict[str, list[dict[str, Any]]], query: str) -> list[dict[str, Any]]:
    hydrated = hydrate(records)
    items = hydrated[entity]
    params = parse_qs(query)
    search = (params.get("search") or [""])[0].lower().strip()
    status = (params.get("status") or [""])[0].lower().strip()

    if search:
        items = [item for item in items if search in json.dumps(item, default=str).lower()]
    if status:
        items = [item for item in items if item.get("status") == status]
    return items


async def handle_api_request(
    method: str,
    pathname: str,
    query: str,
    payload: dict[str, Any],
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
            metadata = await repo.save_tenant(tenant_id, records)
            return 201, {"tenant_id": tenant_id, "records": hydrate(records), "summary": summary(records), "meta": metadata}

        records = await repo.load_tenant(tenant_id)

        if len(parts) == 2 and parts[1] == "summary" and method == "GET":
            return 200, await tenant_summary(repo, tenant_id, records)

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
            return 200, {"tenant_id": tenant_id, "summary": summary(imported), "meta": metadata}

        if len(parts) < 2:
            return 404, {"error": "route not found"}

        entity = parts[1]
        if entity not in ENTITY_TYPES:
            return 404, {"error": "route not found"}

        if len(parts) == 2:
            if method == "GET":
                return 200, {"data": filtered_collection(entity, records, query), "meta": await tenant_metadata(repo, tenant_id)}
            if method == "POST":
                if not can_write(context):
                    return 403, {"error": "operator role required"}
                conflict = await revision_conflict_response(repo, tenant_id, headers)
                if conflict:
                    return conflict
                payload = {**payload, "actor": context.actor_id}
                record = create_record(records, tenant_id, entity, payload)
                metadata = await repo.save_tenant(tenant_id, records)
                return 201, {"data": record, "meta": metadata}
            return 405, {"error": "method not allowed"}

        record_id = parts[2]
        if len(parts) == 4 and entity == "rentals" and parts[3] == "return" and method == "POST":
            if not can_write(context):
                return 403, {"error": "operator role required"}
            conflict = await revision_conflict_response(repo, tenant_id, headers)
            if conflict:
                return conflict
            payload = {**payload, "actor": context.actor_id}
            rental = return_rental(records, tenant_id, record_id, payload)
            metadata = await repo.save_tenant(tenant_id, records)
            return 200, {"data": rental, "meta": metadata}

        if len(parts) != 3:
            return 404, {"error": "route not found"}

        if method == "GET":
            hydrated = hydrate(records)
            return 200, {"data": find_record(hydrated, entity, record_id), "meta": await tenant_metadata(repo, tenant_id)}
        if method == "PUT":
            if not can_write(context):
                return 403, {"error": "operator role required"}
            conflict = await revision_conflict_response(repo, tenant_id, headers)
            if conflict:
                return conflict
            payload = {**payload, "actor": context.actor_id}
            record = update_record(records, tenant_id, entity, record_id, payload)
            metadata = await repo.save_tenant(tenant_id, records)
            return 200, {"data": record, "meta": metadata}
        if method == "DELETE":
            if not can_admin(context):
                return 403, {"error": "admin role required"}
            conflict = await revision_conflict_response(repo, tenant_id, headers)
            if conflict:
                return conflict
            record = delete_record(records, entity, record_id)
            if entity == "rentals":
                add_history(records, tenant_id, record, "deleted", context.actor_id)
            metadata = await repo.save_tenant(tenant_id, records)
            return 200, {"deleted": record_id, "meta": metadata}
        return 405, {"error": "method not allowed"}
    except DomainError as exc:
        return exc.status, {"error": str(exc)}
    except Exception as exc:
        return 500, {"error": f"unexpected error: {exc}"}
