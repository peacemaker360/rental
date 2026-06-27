import json
import unittest

from worker.storage import KVRepository, entity_key, index_key, metadata_key


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


if __name__ == "__main__":
    unittest.main()
