import time
import unittest

from worker.api_core import RequestContext, context_from_headers, handle_api_request, signed_context_headers
from worker.domain import empty_records


class MemoryRepository:
    def __init__(self):
        self.tenants = {}
        self.meta = {}

    async def load_tenant(self, tenant_id):
        return self.tenants.get(tenant_id, empty_records())

    async def save_tenant(self, tenant_id, records):
        self.tenants[tenant_id] = records
        current = self.meta.get(tenant_id, {"revision": 0})
        self.meta[tenant_id] = {"tenant_id": tenant_id, "revision": current["revision"] + 1, "updated_at": "test-now"}
        return self.meta[tenant_id]

    async def load_metadata(self, tenant_id):
        return self.meta.get(tenant_id, {"tenant_id": tenant_id, "revision": 0, "updated_at": None})


class ApiCoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_bootstrap_and_summary_are_tenant_scoped(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="band-one", actor_id="admin-user", role="admin")

        status, body = await handle_api_request("POST", "/api/band-one/bootstrap", "", {}, repo, admin)
        self.assertEqual(status, 201)
        self.assertEqual(body["tenant_id"], "band-one")
        self.assertEqual(body["meta"]["revision"], 1)

        status, body = await handle_api_request("GET", "/api/band-one/summary", "", {}, repo)
        self.assertEqual(status, 200)
        self.assertEqual(body["instruments"], 2)
        self.assertEqual(body["meta"]["revision"], 1)

        status, body = await handle_api_request("GET", "/api/band-two/summary", "", {}, repo)
        self.assertEqual(status, 200)
        self.assertEqual(body["instruments"], 0)
        self.assertEqual(body["meta"]["revision"], 0)

    async def test_create_member_uses_minimal_pii_fields(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")

        status, member = await handle_api_request("POST", "/api/tenant-a/members", "", {
            "display_name": "Morgan Example",
            "member_ref": "M-42",
            "contact_hint": "stored in roster",
        }, repo, operator)

        self.assertEqual(status, 201)
        self.assertNotIn("email", member["data"])
        self.assertNotIn("phone", member["data"])
        self.assertEqual(member["meta"]["revision"], 1)

    async def test_write_accepts_matching_expected_revision(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")

        status, member = await handle_api_request("POST", "/api/tenant-a/members", "", {
            "display_name": "Morgan Example",
        }, repo, operator, {"x-rental-expected-revision": "0"})

        self.assertEqual(status, 201)
        self.assertEqual(member["meta"]["revision"], 1)

    async def test_write_rejects_stale_expected_revision(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")
        await handle_api_request("POST", "/api/tenant-a/members", "", {
            "display_name": "First Member",
        }, repo, operator)

        status, body = await handle_api_request("POST", "/api/tenant-a/members", "", {
            "display_name": "Stale Member",
        }, repo, operator, {"x-rental-expected-revision": "0"})

        self.assertEqual(status, 409)
        self.assertIn("tenant revision conflict", body["error"])
        self.assertEqual(body["meta"]["revision"], 1)
        records = await repo.load_tenant("tenant-a")
        self.assertEqual([member["display_name"] for member in records["members"]], ["First Member"])

    async def test_write_rejects_invalid_expected_revision(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")

        status, body = await handle_api_request("POST", "/api/tenant-a/members", "", {
            "display_name": "Invalid Revision",
        }, repo, operator, {"x-rental-expected-revision": "abc"})

        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "expected revision must be an integer")

    async def test_tenant_context_must_match_route(self):
        repo = MemoryRepository()
        context = RequestContext(tenant_id="tenant-b", actor_id="operator-user", role="operator")

        status, body = await handle_api_request("GET", "/api/tenant-a/summary", "", {}, repo, context)

        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "tenant context does not match route")

    async def test_viewer_cannot_write(self):
        repo = MemoryRepository()
        viewer = RequestContext(tenant_id="tenant-a", actor_id="viewer-user", role="viewer")

        status, body = await handle_api_request("POST", "/api/tenant-a/members", "", {
            "display_name": "Viewer Write",
        }, repo, viewer)

        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "operator role required")

    async def test_rental_history_uses_context_actor(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="tenant-a", actor_id="trusted-actor", role="admin")
        await handle_api_request("POST", "/api/tenant-a/bootstrap", "", {}, repo, admin)

        records = await repo.load_tenant("tenant-a")
        rental_id = records["rentals"][0]["id"]
        status, _ = await handle_api_request("POST", f"/api/tenant-a/rentals/{rental_id}/return", "", {
            "actor": "client-spoof",
            "return_date": "2026-01-01",
        }, repo, admin)

        self.assertEqual(status, 200)
        records = await repo.load_tenant("tenant-a")
        self.assertEqual(records["history"][-1]["actor"], "trusted-actor")

    async def test_export_requires_admin_role(self):
        repo = MemoryRepository()
        viewer = RequestContext(tenant_id="tenant-a", actor_id="viewer-user", role="viewer")

        status, body = await handle_api_request("GET", "/api/tenant-a/export", "", {}, repo, viewer)

        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "admin role required")

    async def test_export_import_round_trip_remaps_tenant(self):
        repo = MemoryRepository()
        source_admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")
        target_admin = RequestContext(tenant_id="tenant-b", actor_id="admin-b", role="admin")
        await handle_api_request("POST", "/api/tenant-a/bootstrap", "", {}, repo, source_admin)

        status, package = await handle_api_request("GET", "/api/tenant-a/export", "", {}, repo, source_admin)
        self.assertEqual(status, 200)
        self.assertEqual(package["schema"], "association-rental")
        self.assertEqual(package["meta"]["revision"], 1)

        status, body = await handle_api_request("PUT", "/api/tenant-b/import", "", package, repo, target_admin)
        self.assertEqual(status, 200)
        self.assertEqual(body["summary"]["instruments"], 2)
        self.assertEqual(body["meta"]["revision"], 1)

        records = await repo.load_tenant("tenant-b")
        self.assertEqual({record["tenant_id"] for record in records["instruments"]}, {"tenant-b"})
        self.assertEqual({record["tenant_id"] for record in records["members"]}, {"tenant-b"})
        self.assertEqual({record["tenant_id"] for record in records["rentals"]}, {"tenant-b"})

    async def test_import_rejects_blocked_pii_fields(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")

        status, body = await handle_api_request("PUT", "/api/tenant-a/import", "", {
            "records": {
                "members": [{
                    "display_name": "Private Person",
                    "email": "private@example.test",
                }]
            }
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertIn("blocked PII fields", body["error"])

    async def test_context_endpoint_reports_capabilities(self):
        repo = MemoryRepository()
        viewer = RequestContext(tenant_id="tenant-a", actor_id="viewer-user", role="viewer", mode="header")

        status, body = await handle_api_request("GET", "/api/context", "", {}, repo, viewer)

        self.assertEqual(status, 200)
        self.assertEqual(body["tenant_id"], "tenant-a")
        self.assertTrue(body["tenant_locked"])
        self.assertFalse(body["capabilities"]["write"])
        self.assertFalse(body["capabilities"]["admin"])
        self.assertEqual(body["meta"]["revision"], 0)

    async def test_context_endpoint_defaults_to_local_admin(self):
        repo = MemoryRepository()

        status, body = await handle_api_request("GET", "/api/context", "", {}, repo)

        self.assertEqual(status, 200)
        self.assertEqual(body["tenant_id"], "demo-association")
        self.assertFalse(body["tenant_locked"])
        self.assertTrue(body["capabilities"]["admin"])

    async def test_invalid_route_tenant_is_rejected(self):
        repo = MemoryRepository()

        status, body = await handle_api_request("GET", "/api/Bad Tenant/summary", "", {}, repo)

        self.assertEqual(status, 404)
        self.assertIn("tenant id must use", body["error"])


class ContextTests(unittest.TestCase):
    def test_header_mode_requires_tenant_header(self):
        context, error = context_from_headers("tenant-a", {}, "header")

        self.assertIsNone(context)
        self.assertEqual(error, "missing tenant context")

    def test_header_mode_rejects_tenant_mismatch(self):
        context, error = context_from_headers("tenant-a", {"x-rental-tenant-id": "tenant-b"}, "header")

        self.assertIsNone(context)
        self.assertEqual(error, "tenant context does not match route")

    def test_local_mode_defaults_to_admin(self):
        context, error = context_from_headers("tenant-a", {}, "local")

        self.assertIsNone(error)
        self.assertEqual(context.tenant_id, "tenant-a")
        self.assertEqual(context.role, "admin")

    def test_header_mode_allows_context_without_route_tenant(self):
        context, error = context_from_headers(None, {
            "x-rental-tenant-id": "tenant-a",
            "x-rental-role": "operator",
            "x-rental-actor-id": "edge-user",
        }, "header")

        self.assertIsNone(error)
        self.assertEqual(context.tenant_id, "tenant-a")
        self.assertEqual(context.actor_id, "edge-user")
        self.assertEqual(context.role, "operator")

    def test_header_mode_rejects_invalid_tenant_id(self):
        context, error = context_from_headers("tenant-a", {
            "x-rental-tenant-id": "Bad Tenant",
        }, "header")

        self.assertIsNone(context)
        self.assertIn("tenant id must use", error)

    def test_header_mode_rejects_invalid_role(self):
        context, error = context_from_headers("tenant-a", {
            "x-rental-tenant-id": "tenant-a",
            "x-rental-role": "owner",
        }, "header")

        self.assertIsNone(context)
        self.assertEqual(error, "invalid role in tenant context")

    def test_local_mode_rejects_invalid_tenant_id(self):
        context, error = context_from_headers(None, {
            "x-rental-tenant-id": "../tenant",
        }, "local")

        self.assertIsNone(context)
        self.assertIn("tenant id must use", error)

    def test_signed_mode_accepts_signed_context(self):
        secret = "test-secret"
        headers = signed_context_headers({
            "tenant_id": "tenant-a",
            "actor_id": "access-user-1",
            "role": "operator",
            "issued_at": time.time(),
        }, secret)

        context, error = context_from_headers("tenant-a", headers, "signed", secret)

        self.assertIsNone(error)
        self.assertEqual(context.tenant_id, "tenant-a")
        self.assertEqual(context.actor_id, "access-user-1")
        self.assertEqual(context.role, "operator")
        self.assertEqual(context.mode, "signed")

    def test_signed_mode_requires_secret(self):
        headers = signed_context_headers({"tenant_id": "tenant-a", "role": "viewer"}, "test-secret")

        context, error = context_from_headers("tenant-a", headers, "signed")

        self.assertIsNone(context)
        self.assertEqual(error, "missing signed tenant context secret")

    def test_signed_mode_rejects_bad_signature(self):
        headers = signed_context_headers({"tenant_id": "tenant-a", "role": "admin"}, "test-secret")
        headers["x-rental-context-signature"] = "bad"

        context, error = context_from_headers("tenant-a", headers, "signed", "test-secret")

        self.assertIsNone(context)
        self.assertEqual(error, "invalid signed tenant context")

    def test_signed_mode_rejects_route_mismatch(self):
        headers = signed_context_headers({"tenant_id": "tenant-b", "role": "viewer"}, "test-secret")

        context, error = context_from_headers("tenant-a", headers, "signed", "test-secret")

        self.assertIsNone(context)
        self.assertEqual(error, "tenant context does not match route")

    def test_signed_mode_rejects_expired_context(self):
        headers = signed_context_headers({
            "tenant_id": "tenant-a",
            "role": "viewer",
            "issued_at": time.time() - 7200,
        }, "test-secret")

        context, error = context_from_headers("tenant-a", headers, "signed", "test-secret")

        self.assertIsNone(context)
        self.assertEqual(error, "expired signed tenant context")


if __name__ == "__main__":
    unittest.main()
