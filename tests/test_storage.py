import json
import unittest
from unittest.mock import AsyncMock
from errors import DataIntegrityError, DataVisibilityPending

from worker.storage import (
    KVRepository,
    access_requests_email_index_key,
    access_requests_index_key,
    association_contact_key,
    association_key,
    associations_index_key,
    entity_key,
    index_key,
    metadata_key,
    snapshot_key,
    user_key,
    users_index_key,
)


class FakeKV:
    def __init__(self):
        self.values = {}
        self.deleted = []

    async def get(self, key, type=None):
        value = self.values.get(key)
        if value is None:
            return None
        if type == "json":
            return json.loads(value)
        return value

    async def put(self, key, value):
        self.values[key] = value

    async def delete(self, key):
        self.deleted.append(key)
        self.values.pop(key, None)


class KVRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_data_does_not_get_skipped_or_rewritten(self):
        for key, raw in [
            (index_key("tenant-a", "instruments"), '{"secret": "wrong shape"}'),
            (index_key("tenant-a", "instruments"), 'invalid JSON private data'),
            (metadata_key("tenant-a"), '{"revision": "bad"}'),
            (metadata_key("tenant-a"), '[]'),
        ]:
            kv = FakeKV()
            kv.values[key] = raw
            snapshot = dict(kv.values)
            repo = KVRepository(kv)
            with self.assertRaises(DataIntegrityError):
                if key.endswith(":meta"):
                    await repo.load_metadata("tenant-a")
                else:
                    await repo.load_tenant("tenant-a")
            with self.assertRaises(DataIntegrityError):
                await repo.save_tenant("tenant-a", {"instruments": [{"id": "new"}]})
            self.assertEqual(kv.values, snapshot)
            self.assertEqual(kv.deleted, [])

    async def test_missing_or_mismatched_indexed_record_blocks_reads(self):
        for record in [None, [], {"id": "different", "note": "private"}]:
            kv = FakeKV()
            kv.values[index_key("tenant-a", "instruments")] = '["inst_1"]'
            if record is not None:
                kv.values[entity_key("tenant-a", "instruments", "inst_1")] = json.dumps(record)
            with self.assertRaises(DataVisibilityPending if record is None else DataIntegrityError):
                await KVRepository(kv).load_tenant("tenant-a")

    async def test_user_reads_use_directory_without_overwriting_kv_snapshot(self):
        kv = FakeKV()
        snapshot = {"id": "user_a", "email": "member@example.test", "global_role": "admin"}
        await kv.put(user_key("user_a"), json.dumps(snapshot))
        await kv.put(users_index_key(), json.dumps(["user_a"]))
        directory = type("Directory", (), {})()
        directory.read_access = AsyncMock(return_value={**snapshot, "global_role": "none"})
        repo = KVRepository(kv, directory=directory)
        self.assertEqual((await repo.load_user("user_a"))["global_role"], "none")
        self.assertEqual((await repo.list_users())[0]["global_role"], "none")
        self.assertEqual(json.loads(kv.values[user_key("user_a")]), snapshot)
        self.assertEqual(directory.read_access.await_count, 2)

    async def test_snapshot_publication_preserves_legacy_and_administrative_keys(self):
        kv = FakeKV()
        old = {"id": "inst_1", "name": "Flute"}
        kv.values[index_key("tenant-a", "instruments")] = '["inst_1"]'
        kv.values[entity_key("tenant-a", "instruments", "inst_1")] = json.dumps(old)
        kv.values["associations:tenant-a"] = '{"tenant_id":"tenant-a","display_name":"A"}'
        kv.values["users:example"] = '{"role":"admin"}'
        legacy = dict(kv.values)
        repo = KVRepository(kv)
        metadata = await repo.save_tenant("tenant-a", {"instruments": []})
        self.assertEqual(metadata["revision"], 1)
        self.assertEqual((await repo.load_tenant("tenant-a"))["instruments"], [])
        self.assertEqual(await repo.load_metadata("tenant-a"), metadata)
        self.assertEqual({key: kv.values[key] for key in legacy}, legacy)
        self.assertEqual(kv.deleted, [])
        self.assertEqual(set(kv.values) - set(legacy), {snapshot_key("tenant-a")})
        # Delayed legacy indices/records are no longer consulted after publication.
        kv.values[index_key("tenant-a", "instruments")] = 'invalid old index'
        self.assertEqual((await repo.load_state("tenant-a"))["records"]["instruments"], [])

    async def test_snapshot_changes_only_matching_tenant(self):
        kv = FakeKV()
        repo = KVRepository(kv)
        await repo.save_tenant("tenant-a", {"instruments": [{"id": "inst_1", "name": "Flute"}]})
        await repo.save_tenant("tenant-b", {"instruments": [{"id": "inst_1", "name": "Other Flute"}]})
        before = kv.values[snapshot_key("tenant-b")]
        await repo.save_tenant("tenant-a", {"instruments": []})
        self.assertEqual(kv.values[snapshot_key("tenant-b")], before)
        self.assertEqual((await repo.load_tenant("tenant-a"))["instruments"], [])
        self.assertEqual((await repo.load_metadata("tenant-a"))["revision"], 2)

    async def test_failed_snapshot_publication_leaves_old_state_readable(self):
        kv = FakeKV()
        repo = KVRepository(kv)
        await repo.save_tenant("tenant-a", {"instruments": [{"id": "old", "name": "Flute"}]})
        before = dict(kv.values)
        async def fail(*args):
            raise RuntimeError("unavailable")
        kv.put = fail
        with self.assertRaises(RuntimeError):
            await repo.save_tenant("tenant-a", {"instruments": []})
        self.assertEqual(kv.values, before)
        self.assertEqual((await repo.load_tenant("tenant-a"))["instruments"][0]["id"], "old")

    async def test_load_metadata_defaults_for_new_tenant(self):
        repo = KVRepository(FakeKV())

        self.assertEqual(await repo.load_metadata("tenant-a"), {
            "tenant_id": "tenant-a",
            "revision": 0,
            "updated_at": None,
        })

    async def test_tenant_exists_uses_metadata(self):
        kv = FakeKV()
        repo = KVRepository(kv)

        self.assertFalse(await repo.tenant_exists("tenant-a"))

        await repo.save_tenant("tenant-a", {
            "instruments": [],
            "members": [{"id": "member_1", "display_name": "Member One"}],
            "rentals": [],
            "service_records": [],
            "history": [],
        })

        self.assertTrue(await repo.tenant_exists("tenant-a"))

    async def test_tenant_exists_supports_entity_only_indexes(self):
        kv = FakeKV()
        repo = KVRepository(kv)
        await kv.put(index_key("tenant-a", "members"), json.dumps(["member_1"]))

        self.assertTrue(await repo.tenant_exists("tenant-a"))
        self.assertFalse(await repo.tenant_exists("tenant-b"))

    async def test_association_registry_round_trip(self):
        kv = FakeKV()
        tenant_access_kv = FakeKV()
        repo = KVRepository(kv, tenant_access_kv)

        saved = await repo.save_association("tenant-a", {
            "tenant_id": "tenant-a",
            "contact": "board@example.test",
            "display_name": "Tenant A",
            "status": "active",
        })

        self.assertEqual(saved["display_name"], "Tenant A")
        self.assertIn(associations_index_key(), kv.values)
        self.assertIn(association_key("tenant-a"), kv.values)
        self.assertEqual(json.loads(tenant_access_kv.values[association_contact_key("tenant-a")])["contact"], "board@example.test")
        self.assertEqual((await repo.load_association("tenant-a"))["status"], "active")
        self.assertEqual([item["tenant_id"] for item in await repo.list_associations()], ["tenant-a"])

    async def test_association_registry_sorts_like_local_admin_center(self):
        kv = FakeKV()
        repo = KVRepository(kv)

        await repo.save_association("z-band", {
            "tenant_id": "z-band",
            "display_name": "Z Band",
            "status": "active",
        })
        await repo.save_association("a-band", {
            "tenant_id": "a-band",
            "display_name": "A Band",
            "status": "active",
        })

        self.assertEqual([item["tenant_id"] for item in await repo.list_associations()], ["a-band", "z-band"])

    async def test_user_registry_round_trip(self):
        kv = FakeKV()
        tenant_access_kv = FakeKV()
        repo = KVRepository(kv, tenant_access_kv)

        saved = await repo.save_user("user_abc123", {
            "id": "user_abc123",
            "email": "reader@example.test",
            "global_role": "reader",
            "tenant_roles": [{"tenant_id": "tenant-a", "role": "reader"}],
            "member_links": [],
        })

        self.assertEqual(saved["email"], "reader@example.test")
        self.assertIn(users_index_key(), kv.values)
        self.assertIn(user_key("user_abc123"), kv.values)
        self.assertNotIn("user:reader@example.test", tenant_access_kv.values)
        self.assertEqual((await repo.load_user("user_abc123"))["global_role"], "reader")
        self.assertEqual([item["id"] for item in await repo.list_users()], ["user_abc123"])
        self.assertEqual((await repo.delete_user("user_abc123"))["email"], "reader@example.test")
        self.assertIn("user:reader@example.test", tenant_access_kv.deleted)
        self.assertNotIn(user_key("user_abc123"), kv.values)
        self.assertEqual(json.loads(kv.values[users_index_key()]), [])
        self.assertIsNone(await repo.load_user("user_abc123"))

    async def test_access_request_email_index_is_created_and_removed(self):
        tenant_access_kv = FakeKV()
        repo = KVRepository(FakeKV(), tenant_access_kv)
        request_id = "access_request:1234567890abcdef12345678"
        request = {
            "id": request_id,
            "email": "Member@Example.Test",
            "tenant_id": "tenant-a",
            "status": "pending",
        }

        await repo.save_access_request(request_id, request)

        email_index = access_requests_email_index_key("member@example.test")
        self.assertEqual(json.loads(tenant_access_kv.values[access_requests_index_key()]), [request_id])
        self.assertEqual(json.loads(tenant_access_kv.values[email_index]), [request_id])

        removed = await repo.delete_access_request(request_id)

        self.assertEqual(removed["email"], "Member@Example.Test")
        self.assertEqual(json.loads(tenant_access_kv.values[access_requests_index_key()]), [])
        self.assertNotIn(email_index, tenant_access_kv.values)


if __name__ == "__main__":
    unittest.main()
