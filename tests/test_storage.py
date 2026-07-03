import json
import unittest

from worker.storage import KVRepository, association_key, associations_index_key, entity_key, index_key, metadata_key, user_key, users_index_key


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
    async def test_save_tenant_deletes_stale_record_keys(self):
        kv = FakeKV()
        repo = KVRepository(kv)

        await repo.save_tenant("tenant-a", {
            "instruments": [{"id": "inst_1", "name": "Flute"}, {"id": "inst_2", "name": "Horn"}],
            "members": [],
            "rentals": [],
            "history": [],
        })
        self.assertIn(entity_key("tenant-a", "instruments", "inst_2"), kv.values)
        self.assertEqual(json.loads(kv.values[metadata_key("tenant-a")])["revision"], 1)

        await repo.save_tenant("tenant-a", {
            "instruments": [{"id": "inst_1", "name": "Flute"}],
            "members": [],
            "rentals": [],
            "history": [],
        })

        stale_key = entity_key("tenant-a", "instruments", "inst_2")
        self.assertIn(stale_key, kv.deleted)
        self.assertNotIn(stale_key, kv.values)
        self.assertEqual(json.loads(kv.values[index_key("tenant-a", "instruments")]), ["inst_1"])
        self.assertEqual(json.loads(kv.values[metadata_key("tenant-a")])["revision"], 2)

    async def test_save_tenant_prunes_only_matching_tenant(self):
        kv = FakeKV()
        repo = KVRepository(kv)
        await repo.save_tenant("tenant-a", {
            "instruments": [{"id": "inst_1", "name": "Flute"}],
            "members": [],
            "rentals": [],
            "history": [],
        })
        await repo.save_tenant("tenant-b", {
            "instruments": [{"id": "inst_1", "name": "Other Flute"}],
            "members": [],
            "rentals": [],
            "history": [],
        })
        await repo.save_tenant("tenant-a", {
            "instruments": [],
            "members": [],
            "rentals": [],
            "history": [],
        })

        self.assertNotIn(entity_key("tenant-a", "instruments", "inst_1"), kv.values)
        self.assertIn(entity_key("tenant-b", "instruments", "inst_1"), kv.values)

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
        repo = KVRepository(kv)

        saved = await repo.save_association("tenant-a", {
            "tenant_id": "tenant-a",
            "display_name": "Tenant A",
            "status": "active",
        })

        self.assertEqual(saved["display_name"], "Tenant A")
        self.assertIn(associations_index_key(), kv.values)
        self.assertIn(association_key("tenant-a"), kv.values)
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
        repo = KVRepository(kv)

        saved = await repo.save_user("user_abc123", {
            "id": "user_abc123",
            "email": "reader@example.test",
            "global_role": "reader",
        })

        self.assertEqual(saved["email"], "reader@example.test")
        self.assertIn(users_index_key(), kv.values)
        self.assertIn(user_key("user_abc123"), kv.values)
        self.assertEqual((await repo.load_user("user_abc123"))["global_role"], "reader")
        self.assertEqual([item["id"] for item in await repo.list_users()], ["user_abc123"])
        self.assertEqual((await repo.delete_user("user_abc123"))["email"], "reader@example.test")
        self.assertNotIn(user_key("user_abc123"), kv.values)
        self.assertEqual(json.loads(kv.values[users_index_key()]), [])
        self.assertIsNone(await repo.load_user("user_abc123"))


if __name__ == "__main__":
    unittest.main()
