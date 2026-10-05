import time
import unittest
from unittest.mock import AsyncMock
from domain import DomainError

from worker.api_core import (
    RequestContext,
    context_from_headers,
    context_payload,
    handle_api_request,
    is_api_request_path,
    parse_api_path,
    signed_context_headers,
    validate_association_tenant_id,
)
from worker.domain import empty_records


class MemoryRepository:
    def __init__(self):
        self.tenants = {}
        self.meta = {}
        self.associations = {}
        self.users = {}
        self.access_requests = {}

    async def load_tenant(self, tenant_id):
        return self.tenants.get(tenant_id, empty_records())

    async def save_tenant(self, tenant_id, records):
        self.tenants[tenant_id] = records
        current = self.meta.get(tenant_id, {"revision": 0})
        self.meta[tenant_id] = {"tenant_id": tenant_id, "revision": current["revision"] + 1, "updated_at": "test-now"}
        return self.meta[tenant_id]

    async def load_metadata(self, tenant_id):
        return self.meta.get(tenant_id, {"tenant_id": tenant_id, "revision": 0, "updated_at": None})

    async def list_associations(self):
        return sorted(self.associations.values(), key=lambda item: item["tenant_id"])

    async def load_association(self, tenant_id):
        return self.associations.get(tenant_id)

    async def save_association(self, tenant_id, association):
        self.associations[tenant_id] = association
        return association

    async def list_users(self):
        return sorted(self.users.values(), key=lambda item: item["email"])

    async def load_user(self, user_id):
        return self.users.get(user_id)

    async def save_user(self, user_id, user):
        self.users[user_id] = user
        return user

    async def delete_user(self, user_id):
        return self.users.pop(user_id, None)

    async def list_access_requests(self):
        return sorted(self.access_requests.values(), key=lambda item: item["requested_at"])

    async def load_access_request(self, request_id):
        return self.access_requests.get(request_id)

    async def delete_access_request(self, request_id):
        return self.access_requests.pop(request_id, None)


class FailingRepository(MemoryRepository):
    async def load_tenant(self, tenant_id):
        raise RuntimeError("secret internal storage path /tmp/private")


class ApiCoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_tenant_routes_require_explicit_namespace(self):
        repo = FailingRepository()

        status, body = await handle_api_request("GET", "/api/tenant-a/summary", "", {}, repo)
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "route not found")

        status, body = await handle_api_request("GET", "/api/auth/login", "", {}, repo)
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "route not found")

    async def test_bootstrap_and_summary_are_tenant_scoped(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="band-one", actor_id="admin-user", role="admin")

        status, body = await handle_api_request("POST", "/api/tid-band-one/bootstrap", "", {}, repo, admin)
        self.assertEqual(status, 201)
        self.assertEqual(body["tenant_id"], "band-one")
        self.assertEqual(body["meta"]["revision"], 1)

        status, body = await handle_api_request("GET", "/api/tid-band-one/summary", "", {}, repo)
        self.assertEqual(status, 200)
        self.assertEqual(body["instruments"], 2)
        self.assertEqual(body["meta"]["revision"], 1)

        status, body = await handle_api_request("GET", "/api/tid-band-two/summary", "", {}, repo)
        self.assertEqual(status, 200)
        self.assertEqual(body["instruments"], 0)
        self.assertEqual(body["meta"]["revision"], 0)

    async def test_create_member_uses_minimal_pii_fields(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")

        status, member = await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
            "display_name": "Morgan Example",
            "member_ref": "M-42",
            "contact_hint": "stored in roster",
        }, repo, operator)

        self.assertEqual(status, 201)
        self.assertNotIn("email", member["data"])
        self.assertNotIn("phone", member["data"])
        self.assertEqual(member["meta"]["revision"], 1)

    async def test_member_collection_status_filters_match_ui_activity_states(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")

        await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
            "display_name": "Active Member",
            "is_active": True,
        }, repo, operator)
        await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
            "display_name": "Inactive Member",
            "is_active": False,
        }, repo, operator)

        status, active = await handle_api_request("GET", "/api/tid-tenant-a/members", "status=active", {}, repo, operator)
        self.assertEqual(status, 200)
        self.assertEqual([member["display_name"] for member in active["data"]], ["Active Member"])

        status, inactive = await handle_api_request("GET", "/api/tid-tenant-a/members", "status=inactive", {}, repo, operator)
        self.assertEqual(status, 200)
        self.assertEqual([member["display_name"] for member in inactive["data"]], ["Inactive Member"])

    async def test_basic_access_profile_sees_only_related_records(self):
        repo = MemoryRepository()
        repo.associations["tenant-a"] = {
            "tenant_id": "tenant-a",
            "display_name": "Tenant A Band",
            "status": "active",
            "contact": "help@example.test",
        }
        admin = RequestContext(tenant_id="tenant-a", actor_id="admin-user", role="admin")
        status, member_a = await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
            "display_name": "Member A",
            "access_email": "member-a@example.test",
        }, repo, admin)
        self.assertEqual(status, 201)
        self.assertNotIn("access_email", member_a["data"])
        self.assertIn("access_email_hash", member_a["data"])
        status, member_b = await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
            "display_name": "Member B",
        }, repo, admin)
        self.assertEqual(status, 201)
        status, inst_a = await handle_api_request("POST", "/api/tid-tenant-a/instruments", "", {
            "name": "Clarinet A",
            "serial": "A-1",
        }, repo, admin)
        self.assertEqual(status, 201)
        status, inst_b = await handle_api_request("POST", "/api/tid-tenant-a/instruments", "", {
            "name": "Clarinet B",
            "serial": "B-1",
        }, repo, admin)
        self.assertEqual(status, 201)
        await handle_api_request("POST", "/api/tid-tenant-a/rentals", "", {
            "instrument_id": inst_a["data"]["id"],
            "member_id": member_a["data"]["id"],
            "start_date": "2026-01-01",
        }, repo, admin)
        await handle_api_request("POST", "/api/tid-tenant-a/rentals", "", {
            "instrument_id": inst_b["data"]["id"],
            "member_id": member_b["data"]["id"],
            "start_date": "2026-01-01",
        }, repo, admin)
        basic = RequestContext(
            tenant_id="tenant-a",
            actor_id="access-user",
            role="viewer",
            mode="signed",
            access_profile="basic",
            member_id=member_a["data"]["id"],
            user_email="member-a@example.test",
        )

        status, members = await handle_api_request("GET", "/api/tid-tenant-a/members", "", {}, repo, basic)
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in members["data"]], [member_a["data"]["id"]])

        status, instruments = await handle_api_request("GET", "/api/tid-tenant-a/instruments", "", {}, repo, basic)
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in instruments["data"]], [inst_a["data"]["id"]])

        status, hidden = await handle_api_request("GET", f"/api/tid-tenant-a/instruments/{inst_b['data']['id']}", "", {}, repo, basic)
        self.assertEqual(status, 404)
        self.assertEqual(hidden["error"], "record not found")

        auto_basic = RequestContext(
            tenant_id="tenant-a",
            actor_id="access-user",
            role="viewer",
            mode="signed",
            access_profile="basic",
            user_email="member-a@example.test",
        )

        status, auto_rentals = await handle_api_request("GET", "/api/tid-tenant-a/rentals", "", {}, repo, auto_basic)
        self.assertEqual(status, 200)
        self.assertEqual([item["member_id"] for item in auto_rentals["data"]], [member_a["data"]["id"]])

        status, auto_summary = await handle_api_request("GET", "/api/tid-tenant-a/summary", "", {}, repo, auto_basic)
        self.assertEqual(status, 200)
        self.assertEqual(auto_summary["members"], 1)
        self.assertEqual(auto_summary["instruments"], 1)
        self.assertEqual(auto_summary["active_rentals"], 1)
        self.assertEqual(auto_summary["association"], {
            "tenant_id": "tenant-a",
            "display_name": "Tenant A Band",
            "contact": "help@example.test",
        })

        status, body = await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
            "display_name": "Should Not Write",
        }, repo, basic)
        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "operator role required")

    async def test_crud_write_registers_tenant_association(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="new-band", actor_id="operator-user", role="operator")
        platform_admin = RequestContext(tenant_id="platform-admin", actor_id="admin-user", role="admin")

        status, _ = await handle_api_request("POST", "/api/tid-new-band/members", "", {
            "display_name": "Morgan Example",
        }, repo, operator)
        status, body = await handle_api_request("GET", "/api/admin/associations", "", {}, repo, platform_admin)

        self.assertEqual(status, 200)
        self.assertEqual(body["data"][0]["tenant_id"], "new-band")
        self.assertEqual(body["data"][0]["display_name"], "New Band")
        self.assertEqual(body["data"][0]["meta"]["revision"], 1)

    async def test_crud_write_preserves_existing_association_details(self):
        repo = MemoryRepository()
        repo.associations["tenant-a"] = {
            "tenant_id": "tenant-a",
            "display_name": "Curated Name",
            "status": "paused",
            "contact_ref": "board-roster",
            "updated_at": "curated-time",
        }
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")

        status, _ = await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
            "display_name": "Morgan Example",
        }, repo, operator)

        self.assertEqual(status, 201)
        self.assertEqual(repo.associations["tenant-a"]["display_name"], "Curated Name")
        self.assertEqual(repo.associations["tenant-a"]["status"], "paused")
        self.assertEqual(repo.associations["tenant-a"]["updated_at"], "curated-time")

    async def test_create_member_rejects_contact_pii(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")

        status, body = await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
            "display_name": "Private Member",
            "contact_hint": "Call +41 44 000 00 00",
        }, repo, operator)

        self.assertEqual(status, 400)
        self.assertIn("contact_hint must not contain phone numbers", body["error"])

    async def test_crud_write_rejects_non_object_payload(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")

        status, body = await handle_api_request("POST", "/api/tid-tenant-a/members", "", [{
            "display_name": "List Payload",
        }], repo, operator)

        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "request payload must be an object")

    async def test_unexpected_errors_do_not_leak_internal_details(self):
        repo = FailingRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")

        status, body = await handle_api_request("GET", "/api/tid-tenant-a/members", "", {}, repo, operator)

        self.assertEqual(status, 500)
        self.assertEqual(body["error"], "unexpected error")
        self.assertNotIn("secret internal", body["error"])
        self.assertEqual(body["errorCode"], "BACKEND_UNAVAILABLE")
        self.assertRegex(body["requestId"], r"^[a-f0-9]{32}$")
        self.assertTrue(body["retryable"])

    async def test_context_metadata_failure_is_safe_and_not_an_auth_error(self):
        repo = MemoryRepository()
        async def unavailable(_tenant):
            raise RuntimeError("secret credentials and private member")
        repo.load_metadata = unavailable
        status, body = await handle_api_request("GET", "/api/context", "", {}, repo)
        self.assertEqual(status, 500)
        self.assertEqual(body["errorCode"], "BACKEND_UNAVAILABLE")
        self.assertNotIn("secret", str(body))

    async def test_bad_metadata_blocks_mutation_without_overwriting_data(self):
        from worker.storage import KVRepository, metadata_key
        from tests.test_storage import FakeKV
        kv = FakeKV()
        kv.values[metadata_key("tenant-a")] = '{"revision": "secret invalid value"}'
        snapshot = dict(kv.values)
        repo = KVRepository(kv)
        context = RequestContext(tenant_id="tenant-a", role="admin")
        for method, path, payload in [("GET", "/api/context", {}), ("POST", "/api/tid-tenant-a/bootstrap", {})]:
            status, body = await handle_api_request(method, path, "", payload, repo, context)
            self.assertEqual(status, 503)
            self.assertEqual(body["errorCode"], "DATA_INTEGRITY_ERROR")
            self.assertFalse(body["retryable"])
            self.assertNotIn("secret", str(body))
            self.assertEqual(kv.values, snapshot)

    async def test_write_accepts_matching_expected_revision(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")

        status, member = await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
            "display_name": "Morgan Example",
        }, repo, operator, {"x-rental-expected-revision": "0"})

        self.assertEqual(status, 201)
        self.assertEqual(member["meta"]["revision"], 1)

    async def test_write_rejects_stale_expected_revision(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")
        await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
            "display_name": "First Member",
        }, repo, operator)

        status, body = await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
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

        status, body = await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
            "display_name": "Invalid Revision",
        }, repo, operator, {"x-rental-expected-revision": "abc"})

        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "expected revision must be an integer")

    async def test_tenant_context_must_match_route(self):
        repo = MemoryRepository()
        context = RequestContext(tenant_id="tenant-b", actor_id="operator-user", role="operator")

        status, body = await handle_api_request("GET", "/api/tid-tenant-a/summary", "", {}, repo, context)

        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "tenant context does not match route")

    async def test_viewer_cannot_write(self):
        repo = MemoryRepository()
        viewer = RequestContext(tenant_id="tenant-a", actor_id="viewer-user", role="viewer")

        status, body = await handle_api_request("POST", "/api/tid-tenant-a/members", "", {
            "display_name": "Viewer Write",
        }, repo, viewer)

        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "operator role required")

    async def test_rental_history_uses_context_actor(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="tenant-a", actor_id="trusted-actor", role="admin")
        await handle_api_request("POST", "/api/tid-tenant-a/bootstrap", "", {}, repo, admin)

        records = await repo.load_tenant("tenant-a")
        rental_id = records["rentals"][0]["id"]
        status, _ = await handle_api_request("POST", f"/api/tid-tenant-a/rentals/{rental_id}/return", "", {
            "actor": "client-spoof",
            "return_date": "2026-01-01",
        }, repo, admin)

        self.assertEqual(status, 200)
        records = await repo.load_tenant("tenant-a")
        self.assertEqual(records["history"][-1]["actor"], "trusted-actor")

    async def test_export_requires_admin_role(self):
        repo = MemoryRepository()
        viewer = RequestContext(tenant_id="tenant-a", actor_id="viewer-user", role="viewer")

        status, body = await handle_api_request("GET", "/api/tid-tenant-a/export", "", {}, repo, viewer)

        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "admin role required")

    async def test_export_import_round_trip_remaps_tenant(self):
        repo = MemoryRepository()
        source_admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")
        target_admin = RequestContext(tenant_id="tenant-b", actor_id="admin-b", role="admin")
        await handle_api_request("POST", "/api/tid-tenant-a/bootstrap", "", {}, repo, source_admin)

        status, package = await handle_api_request("GET", "/api/tid-tenant-a/export", "", {}, repo, source_admin)
        self.assertEqual(status, 200)
        self.assertEqual(package["schema"], "association-rental")
        self.assertEqual(package["meta"]["revision"], 1)

        status, body = await handle_api_request("PUT", "/api/tid-tenant-b/import", "", package, repo, target_admin)
        self.assertEqual(status, 200)
        self.assertEqual(body["summary"]["instruments"], 2)
        self.assertEqual(body["meta"]["revision"], 1)

        records = await repo.load_tenant("tenant-b")
        self.assertEqual({record["tenant_id"] for record in records["instruments"]}, {"tenant-b"})
        self.assertEqual({record["tenant_id"] for record in records["members"]}, {"tenant-b"})
        self.assertEqual({record["tenant_id"] for record in records["rentals"]}, {"tenant-b"})
        self.assertEqual({record["tenant_id"] for record in records["service_records"]}, {"tenant-b"})

    async def test_tenant_import_without_metadata_preserves_association_details(self):
        repo = MemoryRepository()
        repo.associations["tenant-b"] = {
            "tenant_id": "tenant-b",
            "display_name": "Curated Association",
            "status": "paused",
            "contact_ref": "board-roster",
            "updated_at": "curated-time",
        }
        source_admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")
        target_admin = RequestContext(tenant_id="tenant-b", actor_id="admin-b", role="admin")
        await handle_api_request("POST", "/api/tid-tenant-a/bootstrap", "", {}, repo, source_admin)
        _, package = await handle_api_request("GET", "/api/tid-tenant-a/export", "", {}, repo, source_admin)

        status, _ = await handle_api_request("PUT", "/api/tid-tenant-b/import", "", package, repo, target_admin)

        self.assertEqual(status, 200)
        self.assertEqual(repo.associations["tenant-b"]["display_name"], "Curated Association")
        self.assertEqual(repo.associations["tenant-b"]["status"], "paused")
        self.assertEqual(repo.associations["tenant-b"]["updated_at"], "curated-time")

    async def test_tenant_import_with_metadata_updates_association_display_name(self):
        repo = MemoryRepository()
        repo.associations["tenant-b"] = {
            "tenant_id": "tenant-b",
            "display_name": "Old Association Name",
            "clerk_organization_id": "org_original",
            "status": "active",
        }
        admin = RequestContext(tenant_id="tenant-b", actor_id="admin-b", role="admin")

        status, _ = await handle_api_request("PUT", "/api/tid-tenant-b/import", "", {
            "association_name": "Imported Association Name",
            "clerk_organization_id": "org_attacker",
            "records": {
                "instruments": [],
                "members": [],
                "rentals": [],
                "service_records": [],
                "history": [],
            },
        }, repo, admin)

        self.assertEqual(status, 200)
        self.assertEqual(repo.associations["tenant-b"]["display_name"], "Imported Association Name")
        self.assertEqual(repo.associations["tenant-b"]["clerk_organization_id"], "org_original")
        self.assertEqual(repo.associations["tenant-b"]["status"], "active")

    async def test_service_record_crud_is_tenant_scoped(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")
        await handle_api_request("POST", "/api/tid-tenant-a/bootstrap", "", {}, repo, admin)
        records = await repo.load_tenant("tenant-a")
        instrument_id = records["instruments"][0]["id"]

        status, body = await handle_api_request("POST", "/api/tid-tenant-a/service_records", "", {
            "instrument_id": instrument_id,
            "service_date": "2026-02-03",
            "condition": "watch",
            "next_service_date": "2027-08-03",
            "job_type": "Checkup",
            "note": "Action feels uneven",
        }, repo, admin)

        self.assertEqual(status, 201)
        self.assertEqual(body["data"]["condition"], "watch")
        self.assertEqual(body["data"]["next_service_date"], "2027-08-03")
        self.assertEqual(body["meta"]["revision"], 2)
        service_id = body["data"]["id"]
        records = await repo.load_tenant("tenant-a")
        self.assertEqual(records["history"][-1]["actor"], "admin-a")
        self.assertEqual(records["history"][-1]["service_record_id"], service_id)
        self.assertEqual(records["history"][-1]["service_condition"], "watch")

        status, collection = await handle_api_request("GET", "/api/tid-tenant-a/service_records", "", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(collection["data"]), 1)
        hydrated_service = next(item for item in collection["data"] if item["id"] == service_id)
        self.assertEqual(hydrated_service["instrument_id"], instrument_id)
        self.assertIn("instrument_name", hydrated_service)
        self.assertIn("instrument_serial", hydrated_service)
        self.assertEqual(hydrated_service["service_due_status"], "ok")

        status, detail = await handle_api_request("GET", f"/api/tid-tenant-a/service_records/{service_id}", "", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertEqual(detail["data"]["instrument_name"], hydrated_service["instrument_name"])
        self.assertEqual(detail["data"]["service_due_status"], "ok")

        status, service_filter = await handle_api_request("GET", "/api/tid-tenant-a/service_records", "status=watch", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in service_filter["data"]], [service_id])

        status, instrument_filter = await handle_api_request("GET", "/api/tid-tenant-a/instruments", "status=watch", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in instrument_filter["data"]], [instrument_id])

        status, summary_body = await handle_api_request("GET", "/api/tid-tenant-a/summary", "", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(summary_body["service_attention"], 1)

        status, body = await handle_api_request("DELETE", f"/api/tid-tenant-a/service_records/{service_id}", "", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertEqual(body["deleted"], service_id)
        self.assertEqual(body["data"]["id"], service_id)
        self.assertEqual(body["data"]["condition"], "watch")
        records = await repo.load_tenant("tenant-a")
        self.assertEqual(records["history"][-1]["action"], "deleted")
        self.assertEqual(records["history"][-1]["actor"], "admin-a")
        self.assertEqual(records["history"][-1]["service_record_id"], service_id)

    async def test_service_record_api_rejects_contact_like_notes(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")
        await handle_api_request("POST", "/api/tid-tenant-a/bootstrap", "", {}, repo, admin)
        records = await repo.load_tenant("tenant-a")
        instrument_id = records["instruments"][0]["id"]

        status, body = await handle_api_request("POST", "/api/tid-tenant-a/service_records", "", {
            "instrument_id": instrument_id,
            "service_date": "2026-02-03",
            "condition": "good",
            "note": "Workshop phone +41 44 000 00 00",
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertIn("note must not contain phone numbers", body["error"])

    async def test_deleting_instrument_records_cascaded_service_deletions_in_history(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")
        status, instrument = await handle_api_request("POST", "/api/tid-tenant-a/instruments", "", {
            "name": "Service-only Clarinet",
            "serial": "CL-SVC-1",
            "type": "Clarinet",
        }, repo, admin)
        self.assertEqual(status, 201)

        status, service = await handle_api_request("POST", "/api/tid-tenant-a/service_records", "", {
            "instrument_id": instrument["data"]["id"],
            "service_date": "2026-02-03",
            "condition": "watch",
            "job_type": "Pad check",
        }, repo, admin, {"x-rental-expected-revision": "1"})
        self.assertEqual(status, 201)

        status, body = await handle_api_request(
            "DELETE",
            f"/api/tid-tenant-a/instruments/{instrument['data']['id']}",
            "",
            {},
            repo,
            admin,
            {"x-rental-expected-revision": "2"},
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["deleted"], instrument["data"]["id"])
        self.assertEqual(body["data"]["name"], "Service-only Clarinet")
        self.assertEqual([item["id"] for item in body["cascaded"]["service_records"]], [service["data"]["id"]])
        records = await repo.load_tenant("tenant-a")
        self.assertEqual(records["instruments"], [])
        self.assertEqual(records["service_records"], [])
        self.assertEqual(records["history"][-1]["action"], "deleted")
        self.assertEqual(records["history"][-1]["actor"], "admin-a")
        self.assertEqual(records["history"][-1]["service_record_id"], service["data"]["id"])
        self.assertEqual(records["history"][-1]["instrument_name"], "Service-only Clarinet")

    async def test_import_rejects_blocked_pii_fields(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")

        status, body = await handle_api_request("PUT", "/api/tid-tenant-a/import", "", {
            "records": {
                "members": [{
                    "display_name": "Private Person",
                    "email": "private@example.test",
                }]
            }
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertIn("blocked PII fields", body["error"])

    async def test_import_rejects_contact_like_history_actor(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")
        await handle_api_request("POST", "/api/tid-tenant-a/bootstrap", "", {}, repo, admin)
        status, package = await handle_api_request("GET", "/api/tid-tenant-a/export", "", {}, repo, admin)
        self.assertEqual(status, 200)
        package["records"]["history"][0]["actor"] = "person@example.test"

        status, body = await handle_api_request("PUT", "/api/tid-tenant-a/import", "", package, repo, admin)

        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "actor must be opaque, not an email address")

    async def test_hitobito_member_import_merges_low_pii_members(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")

        status, body = await handle_api_request("PUT", "/api/tid-tenant-a/members/import/hitobito", "", {
            "data": [{
                "id": "1001",
                "attributes": {
                    "first_name": "Lea",
                    "last_name": "Example",
                    "email": "lea@example.test",
                },
                "relationships": {
                    "groups": {"data": [{"id": "orchestra"}]}
                },
            }]
        }, repo, admin)

        self.assertEqual(status, 200)
        self.assertEqual(body["summary"]["members"], 1)
        self.assertEqual(body["report"]["created"], 1)
        self.assertEqual(body["report"]["updated"], 0)
        self.assertEqual(body["meta"]["revision"], 1)

        records = await repo.load_tenant("tenant-a")
        self.assertEqual(records["members"][0]["member_ref"], "hitobito:1001")
        self.assertEqual(records["members"][0]["groups"], ["orchestra"])
        self.assertNotIn("email", records["members"][0])

        status, body = await handle_api_request("PUT", "/api/tid-tenant-a/members/import/hitobito", "", {
            "people": [{"id": "1001", "display_name": "Lea Updated", "groups": ["band"]}]
        }, repo, admin, {"x-rental-expected-revision": "1"})

        self.assertEqual(status, 200)
        self.assertEqual(body["report"]["created"], 0)
        self.assertEqual(body["report"]["updated"], 1)
        records = await repo.load_tenant("tenant-a")
        self.assertEqual(len(records["members"]), 1)
        self.assertEqual(records["members"][0]["display_name"], "Lea Updated")
        self.assertEqual(records["members"][0]["groups"], ["band"])

    async def test_hitobito_member_import_requires_admin(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-a", role="operator")

        status, body = await handle_api_request("PUT", "/api/tid-tenant-a/members/import/hitobito", "", {
            "people": [{"id": "1001", "display_name": "Operator Import"}]
        }, repo, operator)

        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "admin role required")

    async def test_array_payloads_remain_supported_for_import_routes(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")

        status, hitobito = await handle_api_request("PUT", "/api/tid-tenant-a/members/import/hitobito", "", [{
            "id": "1001",
            "display_name": "Array Import Member",
        }], repo, admin)

        self.assertEqual(status, 200)
        self.assertEqual(hitobito["report"]["created"], 1)

        status, instruments = await handle_api_request("PUT", "/api/tid-tenant-a/instruments/import", "", [{
            "name": "Array Import Clarinet",
            "brand": "Buffet",
            "type": "Clarinet",
            "serial": "CL-ARRAY-1",
        }], repo, admin, {"x-rental-expected-revision": "1"})

        self.assertEqual(status, 200)
        self.assertEqual(instruments["report"]["created"], 1)

    async def test_instrument_inventory_export_and_import_merge(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")
        await handle_api_request("POST", "/api/tid-tenant-a/bootstrap", "", {}, repo, admin)

        status, exported = await handle_api_request("GET", "/api/tid-tenant-a/instruments/export", "", {}, repo, admin)

        self.assertEqual(status, 200)
        self.assertEqual(exported["schema"], "association-rental-instruments")
        self.assertEqual(exported["summary"]["instruments"], 2)
        self.assertNotIn("members", exported["records"])
        self.assertEqual(exported["meta"]["revision"], 1)

        status, imported = await handle_api_request("PUT", "/api/tid-tenant-a/instruments/import", "", {
            "instruments": [
                {"name": "Updated Piano", "brand": "Yamaha", "type": "Keyboard", "serial": "CP73-001"},
                {"name": "Marching Snare", "brand": "Pearl", "type": "Drum", "serial": "SN-1"},
            ]
        }, repo, admin, {"x-rental-expected-revision": "1"})

        self.assertEqual(status, 200)
        self.assertEqual(imported["report"]["created"], 1)
        self.assertEqual(imported["report"]["updated"], 1)
        self.assertEqual(imported["summary"]["instruments"], 3)
        self.assertEqual(imported["meta"]["revision"], 2)

        records = await repo.load_tenant("tenant-a")
        self.assertEqual([item for item in records["instruments"] if item["serial"] == "CP73-001"][0]["name"], "Updated Piano")
        self.assertTrue(any(item["serial"] == "SN-1" for item in records["instruments"]))

    async def test_instrument_inventory_import_requires_admin(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-a", role="operator")

        status, body = await handle_api_request("PUT", "/api/tid-tenant-a/instruments/import", "", {
            "instruments": [{"name": "Operator Trumpet", "serial": "TR-1"}]
        }, repo, operator)

        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "admin role required")

    async def test_instrument_inventory_import_rejects_contact_pii_fields(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="tenant-a", actor_id="admin-a", role="admin")

        status, body = await handle_api_request("PUT", "/api/tid-tenant-a/instruments/import", "", {
            "instruments": [{
                "name": "Private Donation Clarinet",
                "serial": "CL-1",
                "phone": "+41 44 000 00 00",
            }]
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertIn("blocked PII fields", body["error"])

    async def test_context_endpoint_reports_capabilities(self):
        repo = MemoryRepository()
        viewer = RequestContext(
            tenant_id="tenant-a",
            actor_id="viewer-user",
            role="viewer",
            mode="header",
            user_email="viewer@example.test",
        )

        status, body = await handle_api_request("GET", "/api/context", "", {}, repo, viewer)

        self.assertEqual(status, 200)
        self.assertEqual(body["tenant_id"], "tenant-a")
        self.assertEqual(body["user_email"], "viewer@example.test")
        self.assertTrue(body["tenant_locked"])
        self.assertFalse(body["capabilities"]["write"])
        self.assertFalse(body["capabilities"]["admin"])
        self.assertFalse(body["capabilities"]["platform_admin"])
        self.assertEqual(body["meta"]["revision"], 0)

    async def test_context_endpoint_defaults_to_local_admin(self):
        repo = MemoryRepository()

        status, body = await handle_api_request("GET", "/api/context", "", {}, repo)

        self.assertEqual(status, 200)
        self.assertEqual(body["tenant_id"], "demo-association")
        self.assertFalse(body["tenant_locked"])
        self.assertTrue(body["capabilities"]["admin"])
        self.assertTrue(body["capabilities"]["platform_admin"])

    async def test_invalid_route_tenant_is_rejected(self):
        repo = MemoryRepository()

        status, body = await handle_api_request("GET", "/api/tid-Bad Tenant/summary", "", {}, repo)

        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "route not found")

    async def test_bootstrap_registers_association_for_admin_center(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="band-one", actor_id="admin-user", role="admin")

        await handle_api_request("POST", "/api/tid-band-one/bootstrap", "", {}, repo, admin)
        status, body = await handle_api_request("GET", "/api/admin/associations", "", {}, repo, admin)

        self.assertEqual(status, 200)
        self.assertEqual(body["data"][0]["tenant_id"], "band-one")
        self.assertEqual(body["data"][0]["status"], "active")
        self.assertEqual(body["data"][0]["meta"]["revision"], 1)

    async def test_admin_can_create_and_update_association_details(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="platform-admin", actor_id="admin-user", role="admin")

        status, created = await handle_api_request("POST", "/api/admin/associations", "", {
            "tenant_id": "music-club",
            "display_name": "Music Club",
            "short_name": "MC",
            "region": "Bern",
            "contact": "board@example.test",
            "contact_ref": "board-roster",
            "hitobito_group_ref": "hitobito-group-42",
        }, repo, admin)

        self.assertEqual(status, 201)
        self.assertEqual(created["data"]["display_name"], "Music Club")
        self.assertEqual(created["data"]["contact"], "board@example.test")
        self.assertEqual(created["data"]["contact_ref"], "board-roster")
        self.assertNotIn("email", created["data"])

        status, updated = await handle_api_request("PUT", "/api/admin/associations/music-club", "", {
            "display_name": "Music Club Updated",
            "status": "paused",
        }, repo, admin)

        self.assertEqual(status, 200)
        self.assertEqual(updated["data"]["display_name"], "Music Club Updated")
        self.assertEqual(updated["data"]["status"], "paused")

    async def test_platform_admin_can_manage_user_access(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="platform-admin", actor_id="admin-user", role="admin")

        status, created = await handle_api_request("POST", "/api/admin/users", "", {
            "email": "Operator@Example.TEST",
            "display_name": "Ops User",
            "global_role": "none",
            "access_profile": "basic",
            "tenant_roles": [{"tenant_id": "tenant-a", "role": "operator"}],
            "member_links": [{"tenant_id": "tenant-a", "member_id": "mem_123"}],
        }, repo, admin)

        self.assertEqual(status, 201)
        self.assertEqual(created["data"]["email"], "operator@example.test")
        self.assertEqual(created["data"]["access_profile"], "basic")
        self.assertEqual(created["data"]["tenant_roles"], [{"tenant_id": "tenant-a", "role": "operator"}])
        self.assertEqual(created["data"]["member_links"], [{"tenant_id": "tenant-a", "member_id": "mem_123"}])
        user_id = created["data"]["id"]

        status, users = await handle_api_request("GET", "/api/admin/users", "", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in users["data"]], [user_id])

        status, export = await handle_api_request("GET", "/api/admin/users/export/tenant-access", "", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertEqual(export["schema"], "tenant-access-kv-bulk")
        self.assertEqual(export["summary"]["users"], 1)
        self.assertEqual(export["data"][0]["key"], "user:operator@example.test")
        self.assertIn('"tenant_roles":[{"role":"operator","tenant_id":"tenant-a"}]', export["data"][0]["value"])

        status, updated = await handle_api_request("PUT", f"/api/admin/users/{user_id}", "", {
            "global_role": "reader",
            "tenant_roles": [],
            "member_links": [],
        }, repo, admin)

        self.assertEqual(status, 200)
        self.assertEqual(updated["data"]["global_role"], "reader")

        status, deleted = await handle_api_request("DELETE", f"/api/admin/users/{user_id}", "", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertEqual(deleted["deleted"], user_id)
        self.assertEqual(deleted["data"]["email"], "operator@example.test")

        status, users = await handle_api_request("GET", "/api/admin/users", "", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertEqual(users["data"], [])

    async def test_user_access_rejects_invalid_roles_and_email_change(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="platform-admin", actor_id="admin-user", role="admin")

        status, body = await handle_api_request("POST", "/api/admin/users", "", {
            "email": "bad-email",
            "global_role": "reader",
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "email must be a valid email address")

        status, body = await handle_api_request("POST", "/api/admin/users", "", {
            "email": "reader@example.test",
            "display_name": "Call +41 44 000 00 00",
            "global_role": "reader",
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "display_name must not contain phone numbers")

        status, body = await handle_api_request("POST", "/api/admin/users", "", {
            "email": "reader@example.test",
            "tenant_roles": [{"tenant_id": "tenant-a", "role": "owner"}],
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "tenant role must be reader, operator, or admin")

        status, body = await handle_api_request("POST", "/api/admin/users", "", {
            "email": "reader@example.test",
            "member_links": [{"tenant_id": "tenant-a", "member_id": "reader@example.test"}],
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "member_id must be opaque, not an email address")

        status, created = await handle_api_request("POST", "/api/admin/users", "", {
            "email": "reader@example.test",
            "global_role": "reader",
        }, repo, admin)
        self.assertEqual(status, 201)

        status, body = await handle_api_request("PUT", f"/api/admin/users/{created['data']['id']}", "", {
            "email": "other@example.test",
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "email cannot be changed for an existing user")

        status, body = await handle_api_request("DELETE", "/api/admin/users/user_0000000000000000", "", {}, repo, admin)

        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "user not found")










    async def test_tenant_metadata_endpoint_returns_only_metadata(self):
        repo = MemoryRepository()
        repo.meta["tenant-a"] = {
            "tenant_id": "tenant-a",
            "revision": 7,
            "updated_at": "2026-07-25T10:00:00Z",
        }

        status, body = await handle_api_request(
            "GET",
            "/api/tid-tenant-a/meta",
            "",
            {},
            repo,
            RequestContext(tenant_id="tenant-a", actor_id="reader", role="viewer"),
        )

        self.assertEqual(status, 200)
        self.assertEqual(body, {"meta": repo.meta["tenant-a"]})

    async def test_non_admin_cannot_use_association_admin_center(self):
        repo = MemoryRepository()
        operator = RequestContext(tenant_id="tenant-a", actor_id="operator-user", role="operator")

        status, body = await handle_api_request("GET", "/api/admin/associations", "", {}, repo, operator)

        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "admin role required")

    async def test_signed_tenant_admin_cannot_use_association_admin_center(self):
        repo = MemoryRepository()
        tenant_admin = RequestContext(tenant_id="tenant-a", actor_id="tenant-admin", role="admin", mode="signed")

        status, body = await handle_api_request("GET", "/api/admin/associations", "", {}, repo, tenant_admin)

        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "platform admin required")


    async def test_clerk_mapping_is_platform_managed_unique_and_clearable(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="platform-admin", actor_id="admin", role="admin", mode="local")
        tenant_admin = RequestContext(tenant_id="band-a", actor_id="admin-a", role="admin", mode="signed")
        status, created = await handle_api_request("POST", "/api/admin/associations", "", {
            "tenant_id": "band-a", "clerk_organization_id": "org_123",
        }, repo, admin)
        self.assertEqual(status, 201)
        self.assertEqual(created["data"]["clerk_organization_id"], "org_123")
        for payload, expected in [
            ({"tenant_id": "band-b", "clerk_organization_id": "org_123"}, 409),
            ({"tenant_id": "band-b", "clerk_organization_id": "not-an-id"}, 400),
        ]:
            status, _ = await handle_api_request("POST", "/api/admin/associations", "", payload, repo, admin)
            self.assertEqual(status, expected)
        self.assertNotIn("band-b", repo.associations)
        status, _ = await handle_api_request("PUT", "/api/admin/associations/band-a", "", {
            "clerk_organization_id": "org_other",
        }, repo, tenant_admin)
        self.assertEqual(status, 403)
        self.assertEqual(repo.associations["band-a"]["clerk_organization_id"], "org_123")
        status, updated = await handle_api_request("PUT", "/api/admin/associations/band-a", "", {
            "display_name": "Band A",
        }, repo, admin)
        self.assertEqual(status, 200)
        self.assertEqual(updated["data"]["clerk_organization_id"], "org_123")
        status, updated = await handle_api_request("PUT", "/api/admin/associations/band-a", "", {
            "clerk_organization_id": "",
        }, repo, admin)
        self.assertEqual(status, 200)
        self.assertIsNone(updated["data"]["clerk_organization_id"])

    async def test_reserved_system_route_cannot_be_created_as_association(self):
        repo = MemoryRepository()
        platform_admin = RequestContext(tenant_id="platform-admin", actor_id="platform-admin", role="admin", mode="local")

        for tenant_id in ("access-requests", "admin", "auth", "context", "health", "platform-admin"):
            status, body = await handle_api_request("POST", "/api/admin/associations", "", {
                "tenant_id": tenant_id,
                "display_name": "Reserved",
            }, repo, platform_admin)

            self.assertEqual(status, 400)
            self.assertEqual(body["error"], "tenant id is reserved for a system route")


    async def test_admin_center_rejects_non_object_payload(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="platform-admin", actor_id="admin-user", role="admin")

        status, body = await handle_api_request("POST", "/api/admin/associations", "", [{
            "tenant_id": "music-club",
            "display_name": "Music Club",
        }], repo, admin)

        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "request payload must be an object")

    async def test_association_references_reject_contact_pii(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="platform-admin", actor_id="admin-user", role="admin")

        status, body = await handle_api_request("POST", "/api/admin/associations", "", {
            "tenant_id": "music-club",
            "display_name": "Music Club",
            "contact_ref": "board@example.test",
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertIn("contact_ref must not contain email", body["error"])

        status, body = await handle_api_request("POST", "/api/admin/associations", "", {
            "tenant_id": "music-club",
            "display_name": "Music Club",
            "note": "Call +41 44 000 00 00 for onboarding",
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertIn("note must not contain phone numbers", body["error"])

    async def test_association_names_reject_contact_pii(self):
        repo = MemoryRepository()
        admin = RequestContext(tenant_id="platform-admin", actor_id="admin-user", role="admin")

        status, body = await handle_api_request("POST", "/api/admin/associations", "", {
            "tenant_id": "music-club",
            "display_name": "board@example.test",
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertIn("display_name must not contain email", body["error"])

        status, body = await handle_api_request("POST", "/api/admin/associations", "", {
            "tenant_id": "music-club",
            "display_name": "Music Club",
            "short_name": "+41 44 000 00 00",
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertIn("short_name must not contain phone numbers", body["error"])

    async def test_association_update_must_clean_existing_contact_name(self):
        repo = MemoryRepository()
        repo.associations["music-club"] = {
            "tenant_id": "music-club",
            "display_name": "board@example.test",
            "status": "active",
        }
        admin = RequestContext(tenant_id="platform-admin", actor_id="admin-user", role="admin")

        status, body = await handle_api_request("PUT", "/api/admin/associations/music-club", "", {
            "status": "paused",
        }, repo, admin)

        self.assertEqual(status, 400)
        self.assertIn("display_name must not contain email", body["error"])

        status, body = await handle_api_request("PUT", "/api/admin/associations/music-club", "", {
            "display_name": "Music Club",
            "status": "paused",
        }, repo, admin)

        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["display_name"], "Music Club")


class ContextTests(unittest.TestCase):
    def test_api_request_path_distinguishes_static_and_api_boundaries(self):
        self.assertTrue(is_api_request_path("/api"))
        self.assertTrue(is_api_request_path("/api/"))
        self.assertTrue(is_api_request_path("/api/tid-tenant-a/summary"))
        self.assertFalse(is_api_request_path("/app.js"))
        self.assertFalse(is_api_request_path("/apiary"))
        self.assertEqual(parse_api_path("/api"), [])
        self.assertEqual(parse_api_path("/api/tid-tenant-a/summary"), ["tenant-a", "summary"])
        self.assertEqual(parse_api_path("/api/tenant-a/summary"), [])
        self.assertEqual(parse_api_path("/api/auth/login"), ["auth", "login"])
        self.assertEqual(parse_api_path("/api/tid-auth/summary"), [])
        self.assertEqual(validate_association_tenant_id("auth"), "tenant id is reserved for a system route")
        self.assertIsNone(validate_association_tenant_id("music-club"))

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
            "x-rental-user-email": "Edge.User@Example.TEST",
        }, "header")

        self.assertIsNone(error)
        self.assertEqual(context.tenant_id, "tenant-a")
        self.assertEqual(context.actor_id, "edge-user")
        self.assertEqual(context.role, "operator")
        self.assertEqual(context.user_email, "edge.user@example.test")

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

    def test_header_mode_rejects_contact_like_actor_id(self):
        context, error = context_from_headers("tenant-a", {
            "x-rental-tenant-id": "tenant-a",
            "x-rental-actor-id": "person@example.test",
        }, "header")

        self.assertIsNone(context)
        self.assertEqual(error, "actor_id must be opaque, not an email address")

    def test_header_mode_rejects_invalid_user_email(self):
        context, error = context_from_headers("tenant-a", {
            "x-rental-tenant-id": "tenant-a",
            "x-rental-user-email": "not-an-email",
        }, "header")

        self.assertIsNone(context)
        self.assertEqual(error, "invalid user email in tenant context")

    def test_header_mode_rejects_contact_like_member_id(self):
        context, error = context_from_headers("tenant-a", {
            "x-rental-tenant-id": "tenant-a",
            "x-rental-member-id": "+41 44 000 00 00",
        }, "header")

        self.assertIsNone(context)
        self.assertEqual(error, "member_id must be opaque, not a phone number")

    def test_local_mode_rejects_invalid_tenant_id(self):
        context, error = context_from_headers(None, {
            "x-rental-tenant-id": "../tenant",
        }, "local")

        self.assertIsNone(context)
        self.assertIn("tenant id must use", error)

    def test_local_mode_rejects_invalid_role(self):
        context, error = context_from_headers("tenant-a", {
            "x-rental-role": "owner",
        }, "local")

        self.assertIsNone(context)
        self.assertEqual(error, "invalid role in tenant context")

    def test_signed_mode_accepts_signed_context(self):
        secret = "test-secret"
        headers = signed_context_headers({
            "tenant_id": "tenant-a",
            "actor_id": "access-user-1",
            "role": "operator",
            "issued_at": time.time(),
            "user_email": "Signed.User@Example.TEST",
        }, secret)

        context, error = context_from_headers("tenant-a", headers, "signed", secret)

        self.assertIsNone(error)
        self.assertEqual(context.tenant_id, "tenant-a")
        self.assertEqual(context.actor_id, "access-user-1")
        self.assertEqual(context.role, "operator")
        self.assertEqual(context.mode, "signed")
        self.assertEqual(context.user_email, "signed.user@example.test")

    def test_signed_mode_rejects_invalid_user_email(self):
        headers = signed_context_headers({
            "tenant_id": "tenant-a",
            "actor_id": "access-user-1",
            "role": "operator",
            "user_email": "not-an-email",
        }, "test-secret")

        context, error = context_from_headers("tenant-a", headers, "signed", "test-secret")

        self.assertIsNone(context)
        self.assertEqual(error, "invalid user email in signed tenant context")

    def test_signed_mode_rejects_contact_like_member_id(self):
        headers = signed_context_headers({
            "tenant_id": "tenant-a",
            "actor_id": "access-user-1",
            "role": "viewer",
            "access_profile": "basic",
            "member_id": "member@example.test",
        }, "test-secret")

        context, error = context_from_headers("tenant-a", headers, "signed", "test-secret")

        self.assertIsNone(context)
        self.assertEqual(error, "member_id must be opaque, not an email address")

    def test_signed_mode_rejects_contact_like_actor_id(self):
        headers = signed_context_headers({
            "tenant_id": "tenant-a",
            "actor_id": "+41 44 000 00 00",
            "role": "operator",
        }, "test-secret")

        context, error = context_from_headers("tenant-a", headers, "signed", "test-secret")

        self.assertIsNone(context)
        self.assertEqual(error, "actor_id must be opaque, not a phone number")

    def test_signed_mode_exposes_coarse_tenant_switch_hints(self):
        headers = signed_context_headers({
            "tenant_id": "tenant-a",
            "actor_id": "access-user-1",
            "role": "viewer",
            "tenant_count": 2,
            "tenant_switchable": True,
        }, "test-secret")

        context, error = context_from_headers("tenant-a", headers, "signed", "test-secret")

        self.assertIsNone(error)
        self.assertEqual(context.global_role, "none")
        self.assertEqual(context.tenant_count, 2)
        self.assertTrue(context.tenant_switchable)
        payload = context_payload(context)
        self.assertFalse(payload["has_global_role"])
        self.assertTrue(payload["tenant_switchable"])

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


class AdmissionsTests(unittest.IsolatedAsyncioTestCase):
    async def test_admissions_are_scoped_and_read_only(self):
        repo = MemoryRepository()
        repo.list_admissions = AsyncMock(return_value={"organizations": [], "memberships": [], "invitations": []})
        admin = RequestContext(tenant_id="band-a", actor_id="admin", role="admin", mode="signed")
        status, _ = await handle_api_request("GET", "/api/admin/admissions", "", {}, repo, admin)
        self.assertEqual(status, 200)
        repo.list_admissions.assert_awaited_once_with("band-a")
        status, _ = await handle_api_request("POST", "/api/admin/admissions", "", {}, repo, admin)
        self.assertEqual(status, 405)
        reader = RequestContext(tenant_id="band-a", actor_id="reader", role="reader", mode="signed")
        status, _ = await handle_api_request("GET", "/api/admin/admissions", "", {}, repo, reader)
        self.assertEqual(status, 403)
        platform = RequestContext(tenant_id="band-a", actor_id="admin", role="admin", mode="signed", global_role="platform_admin")
        await handle_api_request("GET", "/api/admin/admissions", "", {}, repo, platform)
        repo.list_admissions.assert_awaited_with("band-a")

    async def test_request_resolution_requires_membership_and_hides_delivery_details(self):
        repo = MemoryRepository()
        request_id = "access_request:1234567890abcdef12345678"
        repo.access_requests[request_id] = {"id": request_id, "tenant_id": "band-a", "email": "member@example.test", "requested_at": "now", "notification": {"status": "sent", "sent_user_ids": ["private_admin_id"]}}
        repo.list_admissions = AsyncMock(return_value={"memberships": []})
        admin = RequestContext(tenant_id="band-a", actor_id="admin", role="admin", mode="signed")
        status, body = await handle_api_request("GET", "/api/admin/access-requests", "", {}, repo, admin)
        self.assertEqual(body["data"][0]["notification_status"], "sent")
        self.assertNotIn("notification", body["data"][0])
        path = f"/api/admin/access-requests/{request_id}/resolve"
        status, _ = await handle_api_request("POST", path, "", {}, repo, admin)
        self.assertEqual(status, 409)
        self.assertIn(request_id, repo.access_requests)
        repo.list_admissions.return_value = {"memberships": [{"identifier": "member@example.test", "access_profile": "basic"}]}
        status, _ = await handle_api_request("POST", path, "", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertNotIn(request_id, repo.access_requests)

    async def test_hosted_legacy_permissions_and_global_admin_routes_are_retired(self):
        repo = MemoryRepository()
        repo.sync_user_access = AsyncMock()
        for global_role in ("none", "admin", "platform_admin"):
            admin = RequestContext(tenant_id="band-a", actor_id="admin", role="admin", mode="signed", global_role=global_role)
            for method in ("GET", "POST", "PUT", "DELETE"):
                status, _ = await handle_api_request(method, "/api/admin/users", "", {}, repo, admin)
                self.assertEqual(status, 410)
            for method in ("GET", "POST"):
                status, _ = await handle_api_request(method, "/api/admin/associations", "", {}, repo, admin)
                self.assertEqual(status, 403)
            for method in ("POST", "DELETE"):
                status, _ = await handle_api_request(method, "/api/admin/invitations/band-a", "", {}, repo, admin)
                self.assertEqual(status, 405)
        repo.sync_user_access.assert_not_awaited()

    def test_signed_context_rejects_every_global_role(self):
        for role in ("reader", "operator", "admin", "platform_admin"):
            headers = signed_context_headers({"tenant_id": "band-a", "actor_id": "user_a", "role": "admin", "global_role": role}, "test-secret")
            context, error = context_from_headers("band-a", headers, "signed", "test-secret")
            self.assertIsNone(context)
            self.assertEqual(error, "global roles are not supported in signed tenant context")

    async def test_request_review_stays_tenant_scoped_and_cannot_grant_roles(self):
        repo = MemoryRepository()
        request_id = "access_request:1234567890abcdef12345678"
        repo.access_requests[request_id] = {"id": request_id, "tenant_id": "band-b", "email": "member@example.test", "requested_at": "now", "status": "pending"}
        admin = RequestContext(tenant_id="band-a", actor_id="admin", role="admin", mode="signed")
        status, body = await handle_api_request("GET", "/api/admin/access-requests", "", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertEqual(body["data"], [])
        for action in ("deny", "resolve", "approve"):
            status, _ = await handle_api_request("POST", f"/api/admin/access-requests/{request_id}/{action}", "", {}, repo, admin)
            self.assertEqual(status, 404)
        repo.access_requests[request_id]["tenant_id"] = "band-a"
        status, _ = await handle_api_request("POST", f"/api/admin/access-requests/{request_id}/approve", "", {"global_role": "platform_admin"}, repo, admin)
        self.assertEqual(status, 405)
        self.assertIn(request_id, repo.access_requests)
        self.assertEqual(repo.users, {})
        status, _ = await handle_api_request("POST", f"/api/admin/access-requests/{request_id}/deny", "", {}, repo, admin)
        self.assertEqual(status, 200)
        self.assertNotIn(request_id, repo.access_requests)

    async def test_member_self_service_shows_current_rentals_without_shared_instrument_history(self):
        from worker.domain import email_hash
        repo = MemoryRepository()
        records = empty_records()
        records["members"] = [{"id": "member_a", "display_name": "A", "access_email_hash": email_hash("member@example.test"), "is_active": True}, {"id": "member_b", "display_name": "B"}]
        records["instruments"] = [{"id": "instrument_current", "name": "Current"}, {"id": "instrument_returned", "name": "Returned"}]
        records["rentals"] = [
            {"id": "rental_current", "instrument_id": "instrument_current", "member_id": "member_a", "start_date": "2026-01-01"},
            {"id": "rental_returned", "instrument_id": "instrument_returned", "member_id": "member_a", "start_date": "2026-01-01", "return_date": "2026-02-01"},
            {"id": "rental_other", "instrument_id": "instrument_current", "member_id": "member_b", "start_date": "2025-01-01", "return_date": "2025-02-01"},
        ]
        records["history"] = [{"id": "other_history", "member_id": "member_b", "instrument_id": "instrument_current"}]
        repo.tenants["band-a"] = records
        member = RequestContext(tenant_id="band-a", actor_id="clerk-user", role="viewer", mode="signed", access_profile="basic", user_email="member@example.test")
        for entity, expected in (("rentals", ["rental_current"]), ("instruments", ["instrument_current"]), ("members", ["member_a"]), ("history", [])):
            status, result = await handle_api_request("GET", f"/api/tid-band-a/{entity}", "", {}, repo, member)
            self.assertEqual(status, 200)
            self.assertEqual([item["id"] for item in result["data"]], expected)
        status, _ = await handle_api_request("POST", "/api/tid-band-a/rentals", "", {}, repo, member)
        self.assertEqual(status, 403)
        status, _ = await handle_api_request("GET", "/api/admin/admissions", "", {}, repo, member)
        self.assertEqual(status, 403)
        records["members"][0]["is_active"] = False
        status, result = await handle_api_request("GET", "/api/tid-band-a/rentals", "", {}, repo, member)
        self.assertEqual(result["data"], [])
