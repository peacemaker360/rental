import tempfile
import unittest
import json
from pathlib import Path

from scripts.local_dev_server import JSON_HEADERS, InvalidJsonBody, JsonFileRepository, configured_handler, parse_json_body, static_path_for
from worker.api_core import context_from_headers, signed_context_headers


class LocalDevServerTests(unittest.IsolatedAsyncioTestCase):
    def test_parse_json_body_accepts_empty_object_and_list_payloads(self):
        self.assertEqual(parse_json_body(b""), {})
        self.assertEqual(parse_json_body(b'{"name": "Piano"}'), {"name": "Piano"})
        self.assertEqual(parse_json_body(b'[{"serial": "A-1"}]'), [{"serial": "A-1"}])

    def test_parse_json_body_rejects_malformed_json(self):
        with self.assertRaisesRegex(InvalidJsonBody, "invalid JSON body"):
            parse_json_body(b'{"name":')

    def test_local_api_json_headers_are_uncacheable(self):
        self.assertEqual(JSON_HEADERS["cache-control"], "no-store")
        self.assertEqual(JSON_HEADERS["pragma"], "no-cache")
        self.assertEqual(JSON_HEADERS["referrer-policy"], "no-referrer")
        self.assertEqual(JSON_HEADERS["x-content-type-options"], "nosniff")
        self.assertNotIn("access-control-allow-origin", JSON_HEADERS)

    def test_local_api_cors_allows_trusted_access_profile_headers(self):
        allowed = JSON_HEADERS["access-control-allow-headers"]

        self.assertIn("x-rental-access-profile", allowed)
        self.assertIn("x-rental-member-id", allowed)
        self.assertIn("x-rental-user-email", allowed)

    def test_empty_api_path_stays_in_json_api_boundary(self):
        source = (Path(__file__).resolve().parents[1] / "scripts" / "local_dev_server.py").read_text(encoding="utf-8")

        self.assertIn("is_api_request_path", source)
        self.assertIn('self.send_json({"error": "route not found"}, HTTPStatus.NOT_FOUND)', source)

    def test_static_path_for_rejects_traversal_and_keeps_spa_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp) / "public"
            public.mkdir()
            (public / "index.html").write_text("index", encoding="utf-8")
            (public / "app.js").write_text("app", encoding="utf-8")
            outside = Path(tmp) / "public-evil.txt"
            outside.write_text("nope", encoding="utf-8")

            self.assertEqual(static_path_for("/app.js", public), public.resolve() / "app.js")
            self.assertEqual(static_path_for("/missing-route", public), public.resolve() / "index.html")
            self.assertIsNone(static_path_for("/../public-evil.txt", public))

    def test_tenant_file_uses_valid_tenant_id_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = JsonFileRepository(Path(tmp))

            self.assertEqual(repo.tenant_file("tenant-one").name, "tenant-one.json")

    def test_tenant_file_rejects_invalid_tenant_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = JsonFileRepository(Path(tmp))

            with self.assertRaisesRegex(ValueError, "tenant id must use"):
                repo.tenant_file("../tenant")

    def test_configured_handler_supports_signed_context_debugging(self):
        with tempfile.TemporaryDirectory() as tmp:
            handler = configured_handler(
                JsonFileRepository(Path(tmp)),
                auth_mode="signed",
                context_secret="dev-secret",
            )
            headers = signed_context_headers({
                "tenant_id": "tenant-one",
                "actor_id": "debug-user",
                "role": "operator",
            }, "dev-secret")

            context, error = context_from_headers("tenant-one", headers, handler.auth_mode, handler.context_secret)

            self.assertIsNone(error)
            self.assertEqual(context.tenant_id, "tenant-one")
            self.assertEqual(context.actor_id, "debug-user")
            self.assertEqual(context.role, "operator")

    def test_configured_handler_rejects_unsigned_context_in_signed_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            handler = configured_handler(
                JsonFileRepository(Path(tmp)),
                auth_mode="signed",
                context_secret="dev-secret",
            )

            context, error = context_from_headers("tenant-one", {}, handler.auth_mode, handler.context_secret)

            self.assertIsNone(context)
            self.assertEqual(error, "missing signed tenant context")

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

    async def test_tenant_exists_tracks_local_json_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = JsonFileRepository(Path(tmp))

            self.assertFalse(await repo.tenant_exists("tenant-one"))

            await repo.save_tenant("tenant-one", {
                "instruments": [],
                "members": [{"id": "member_1", "display_name": "Member One"}],
                "rentals": [],
                "service_records": [],
                "history": [],
            })

            self.assertTrue(await repo.tenant_exists("tenant-one"))
            self.assertFalse(await repo.tenant_exists("tenant-two"))

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

    async def test_association_registry_discovers_tenant_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tenant-one.json"
            path.write_text(json.dumps({
                "records": {
                    "instruments": [],
                    "members": [],
                    "rentals": [],
                    "service_records": [],
                    "history": [],
                }
            }), encoding="utf-8")
            repo = JsonFileRepository(Path(tmp))

            associations = await repo.list_associations()

            self.assertEqual(associations[0]["tenant_id"], "tenant-one")
            self.assertEqual(associations[0]["status"], "active")

    async def test_association_registry_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = JsonFileRepository(Path(tmp))

            await repo.save_association("tenant-one", {
                "tenant_id": "tenant-one",
                "display_name": "Tenant One",
                "status": "paused",
                "locale": "de-CH",
            })

            self.assertEqual((await repo.load_association("tenant-one"))["display_name"], "Tenant One")
            self.assertEqual((await repo.list_associations())[0]["status"], "paused")

    async def test_user_registry_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = JsonFileRepository(Path(tmp))

            await repo.save_user("user_abc123", {
                "id": "user_abc123",
                "email": "reader@example.test",
                "global_role": "reader",
            })

            self.assertEqual((await repo.load_user("user_abc123"))["email"], "reader@example.test")
            self.assertEqual([item["id"] for item in await repo.list_users()], ["user_abc123"])
            self.assertEqual((await repo.delete_user("user_abc123"))["email"], "reader@example.test")
            self.assertIsNone(await repo.load_user("user_abc123"))
            self.assertEqual(await repo.list_users(), [])


if __name__ == "__main__":
    unittest.main()
