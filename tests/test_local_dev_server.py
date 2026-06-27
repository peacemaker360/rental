import tempfile
import unittest
import json
from pathlib import Path

from scripts.local_dev_server import JsonFileRepository


class LocalDevServerTests(unittest.IsolatedAsyncioTestCase):
    def test_tenant_file_uses_valid_tenant_id_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = JsonFileRepository(Path(tmp))

            self.assertEqual(repo.tenant_file("tenant-one").name, "tenant-one.json")

    def test_tenant_file_rejects_invalid_tenant_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = JsonFileRepository(Path(tmp))

            with self.assertRaisesRegex(ValueError, "tenant id must use"):
                repo.tenant_file("../tenant")

    async def test_save_tenant_tracks_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = JsonFileRepository(Path(tmp))
            first = await repo.save_tenant("tenant-one", {
                "instruments": [],
                "members": [],
                "rentals": [],
                "history": [],
            })
            second = await repo.save_tenant("tenant-one", {
                "instruments": [],
                "members": [],
                "rentals": [],
                "history": [],
            })

            self.assertEqual(first["revision"], 1)
            self.assertEqual(second["revision"], 2)
            self.assertEqual((await repo.load_metadata("tenant-one"))["revision"], 2)

    async def test_load_tenant_supports_legacy_local_json_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tenant-one.json"
            path.write_text(json.dumps({
                "instruments": [{"id": "inst_1"}],
                "members": [],
                "rentals": [],
                "history": [],
            }), encoding="utf-8")
            repo = JsonFileRepository(Path(tmp))

            records = await repo.load_tenant("tenant-one")

            self.assertEqual(records["instruments"], [{"id": "inst_1"}])
            self.assertEqual((await repo.load_metadata("tenant-one"))["revision"], 0)


if __name__ == "__main__":
    unittest.main()
