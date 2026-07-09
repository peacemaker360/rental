from __future__ import annotations

import json
from typing import Any

from domain import ENTITY_TYPES, empty_records, utc_now


def tenant_key(tenant_id: str, suffix: str) -> str:
    return f"tenant:{tenant_id}:{suffix}"


def entity_key(tenant_id: str, entity: str, record_id: str) -> str:
    return tenant_key(tenant_id, f"{entity}:{record_id}")


def index_key(tenant_id: str, entity: str) -> str:
    return tenant_key(tenant_id, f"index:{entity}")


def metadata_key(tenant_id: str) -> str:
    return tenant_key(tenant_id, "meta")


def associations_index_key() -> str:
    return "associations:index"


def association_key(tenant_id: str) -> str:
    return f"associations:{tenant_id}"


def users_index_key() -> str:
    return "users:index"


def user_key(user_id: str) -> str:
    return f"users:{user_id}"


def access_requests_index_key() -> str:
    return "access_requests:index"


def access_request_key(request_id: str) -> str:
    return f"access_request:{request_id}" if not request_id.startswith("access_request:") else request_id


def association_contact_key(tenant_id: str) -> str:
    return f"association_contact:{tenant_id}"


def empty_metadata(tenant_id: str) -> dict[str, Any]:
    return {"tenant_id": tenant_id, "revision": 0, "updated_at": None}


class KVRepository:
    def __init__(self, kv: Any, tenant_access_kv: Any = None):
        self.kv = kv
        self.tenant_access_kv = tenant_access_kv

    async def _get_json(self, key: str, default: Any = None) -> Any:
        value = await self.kv.get(key, type="json")
        return default if value is None else value

    async def _put_json(self, key: str, value: Any) -> None:
        await self.kv.put(key, json.dumps(value))

    async def _delete(self, key: str) -> None:
        delete = getattr(self.kv, "delete", None)
        if delete is not None:
            await delete(key)

    async def load_tenant(self, tenant_id: str) -> dict[str, list[dict[str, Any]]]:
        records = empty_records()
        for entity in ENTITY_TYPES:
            ids = await self._get_json(index_key(tenant_id, entity), [])
            for record_id in ids:
                record = await self._get_json(entity_key(tenant_id, entity, record_id))
                if record is not None:
                    records[entity].append(record)
        return records

    async def load_metadata(self, tenant_id: str) -> dict[str, Any]:
        metadata = await self._get_json(metadata_key(tenant_id), empty_metadata(tenant_id))
        return {**empty_metadata(tenant_id), **metadata, "tenant_id": tenant_id}

    async def save_tenant(self, tenant_id: str, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        for entity in ENTITY_TYPES:
            previous_ids = set(await self._get_json(index_key(tenant_id, entity), []))
            ids = []
            for record in records.get(entity, []):
                ids.append(record["id"])
                await self._put_json(entity_key(tenant_id, entity, record["id"]), record)
            for stale_id in previous_ids - set(ids):
                await self._delete(entity_key(tenant_id, entity, stale_id))
            await self._put_json(index_key(tenant_id, entity), ids)
        previous_metadata = await self.load_metadata(tenant_id)
        metadata = {
            "tenant_id": tenant_id,
            "revision": int(previous_metadata.get("revision", 0)) + 1,
            "updated_at": utc_now(),
        }
        await self._put_json(metadata_key(tenant_id), metadata)
        return metadata

    async def tenant_exists(self, tenant_id: str) -> bool:
        metadata = await self.kv.get(metadata_key(tenant_id))
        if metadata is not None:
            return True
        for entity in ENTITY_TYPES:
            value = await self.kv.get(index_key(tenant_id, entity))
            if value is not None:
                return True
        return False

    async def list_associations(self) -> list[dict[str, Any]]:
        tenant_ids = await self._get_json(associations_index_key(), [])
        associations = []
        for tenant_id in tenant_ids:
            association = await self.load_association(tenant_id)
            if association is not None:
                associations.append(association)
        return sorted(associations, key=lambda item: item.get("display_name", item.get("tenant_id", "")))

    async def load_association(self, tenant_id: str) -> dict[str, Any] | None:
        return await self._get_json(association_key(tenant_id))

    async def save_association(self, tenant_id: str, association: dict[str, Any]) -> dict[str, Any]:
        tenant_ids = await self._get_json(associations_index_key(), [])
        if tenant_id not in tenant_ids:
            tenant_ids.append(tenant_id)
            tenant_ids.sort()
            await self._put_json(associations_index_key(), tenant_ids)
        await self._put_json(association_key(tenant_id), association)
        await self.save_frontdoor_association_contact(tenant_id, association)
        return association

    async def save_frontdoor_association_contact(self, tenant_id: str, association: dict[str, Any]) -> None:
        if self.tenant_access_kv is None:
            return
        contact = association.get("contact")
        value = {
            "contact": contact,
            "display_name": association.get("display_name"),
            "tenant_id": tenant_id,
        }
        await self.tenant_access_kv.put(association_contact_key(tenant_id), json.dumps(value, separators=(",", ":"), sort_keys=True))

    async def list_users(self) -> list[dict[str, Any]]:
        user_ids = await self._get_json(users_index_key(), [])
        users = []
        for user_id in user_ids:
            user = await self.load_user(user_id)
            if user is not None:
                users.append(user)
        return sorted(users, key=lambda item: item.get("email", item.get("id", "")))

    async def load_user(self, user_id: str) -> dict[str, Any] | None:
        return await self._get_json(user_key(user_id))

    async def save_user(self, user_id: str, user: dict[str, Any]) -> dict[str, Any]:
        user_ids = await self._get_json(users_index_key(), [])
        if user_id not in user_ids:
            user_ids.append(user_id)
            user_ids.sort()
            await self._put_json(users_index_key(), user_ids)
        await self._put_json(user_key(user_id), user)
        await self.save_frontdoor_user_assignment(user)
        return user

    async def delete_user(self, user_id: str) -> dict[str, Any] | None:
        user = await self.load_user(user_id)
        if user is None:
            return None
        user_ids = [item for item in await self._get_json(users_index_key(), []) if item != user_id]
        await self._put_json(users_index_key(), user_ids)
        await self._delete(user_key(user_id))
        await self.delete_frontdoor_user_assignment(user)
        return user

    async def save_frontdoor_user_assignment(self, user: dict[str, Any]) -> None:
        if self.tenant_access_kv is None:
            return
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
        await self.tenant_access_kv.put(f"user:{user['email']}", json.dumps(value, separators=(",", ":"), sort_keys=True))

    async def delete_frontdoor_user_assignment(self, user: dict[str, Any]) -> None:
        if self.tenant_access_kv is None:
            return
        delete = getattr(self.tenant_access_kv, "delete", None)
        if delete is not None:
            await delete(f"user:{user['email']}")

    async def list_access_requests(self) -> list[dict[str, Any]]:
        if self.tenant_access_kv is None:
            return []
        ids = await self.tenant_access_kv.get(access_requests_index_key(), type="json") or []
        requests = []
        for request_id in ids:
            item = await self.tenant_access_kv.get(access_request_key(request_id), type="json")
            if item is not None:
                requests.append(item)
        return sorted(requests, key=lambda item: item.get("requested_at", ""))

    async def load_access_request(self, request_id: str) -> dict[str, Any] | None:
        if self.tenant_access_kv is None:
            return None
        return await self.tenant_access_kv.get(access_request_key(request_id), type="json")

    async def save_access_request(self, request_id: str, item: dict[str, Any]) -> dict[str, Any]:
        if self.tenant_access_kv is None:
            return item
        ids = await self.tenant_access_kv.get(access_requests_index_key(), type="json") or []
        key = access_request_key(request_id)
        if key not in ids:
            ids.append(key)
            ids.sort()
            await self.tenant_access_kv.put(access_requests_index_key(), json.dumps(ids))
        await self.tenant_access_kv.put(key, json.dumps(item))
        return item

    async def delete_access_request(self, request_id: str) -> dict[str, Any] | None:
        if self.tenant_access_kv is None:
            return None
        key = access_request_key(request_id)
        item = await self.tenant_access_kv.get(key, type="json")
        if item is None:
            return None
        ids = [item_id for item_id in await self.tenant_access_kv.get(access_requests_index_key(), type="json") or [] if item_id != key]
        await self.tenant_access_kv.put(access_requests_index_key(), json.dumps(ids))
        delete = getattr(self.tenant_access_kv, "delete", None)
        if delete is not None:
            await delete(key)
        return item
