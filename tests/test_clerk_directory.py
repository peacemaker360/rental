import json
import unittest
from urllib.parse import urlparse
from unittest.mock import AsyncMock

from worker.clerk_directory import ClerkDirectory
from domain import DomainError


class FakeClerk:
    def __init__(self):
        self.calls = []
        self.roles = {"org_a": "org:reader", "org_b": "org:operator", "org_unrelated": "org:admin"}
        self.user = {
            "id": "user_clerk", "primary_email_address_id": "email_a",
            "email_addresses": [{"id": "email_a", "email_address": "member@example.test", "verification": {"status": "verified"}}],
        }
        self.failure = None

    async def __call__(self, url, **options):
        path = urlparse(url).path.removeprefix("/v1")
        method = options["method"]
        body = json.loads(options["body"]) if "body" in options else None
        self.calls.append((method, path, body))
        status = 200
        result = {}
        if self.failure == (method, path):
            status = 503
        elif method == "GET" and path == "/users":
            result = [self.user]
        elif path.endswith("/organization_memberships"):
            result = {"data": [{"organization": {"id": org}, "role": role} for org, role in self.roles.items()], "total_count": len(self.roles)}
        elif path.startswith("/organizations/"):
            organization = path.split("/")[2]
            if method == "DELETE":
                self.roles.pop(organization, None)
            else:
                self.roles[organization] = body["role"]

        class Response:
            async def text(self):
                return json.dumps(result)
        response = Response()
        response.status = status
        return response


class ClerkDirectoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.remote = FakeClerk()
        self.directory = ClerkDirectory("test-secret", self.remote)
        self.associations = [{"tenant_id": "band-a", "clerk_organization_id": "org_a"}, {"tenant_id": "band-b", "clerk_organization_id": "org_b"}]
        self.user = {"email": "member@example.test", "status": "active", "global_role": "none", "access_profile": "basic", "tenant_roles": [{"tenant_id": "band-a", "role": "reader"}]}

    async def test_full_reconciliation_revokes_removed_memberships_and_keeps_unrelated_orgs(self):
        clerk_id = await self.directory.sync_access(self.user, self.associations)
        self.assertEqual(clerk_id, "user_clerk")
        self.assertEqual(self.remote.roles, {"org_a": "org:member", "org_unrelated": "org:admin"})
        writes = [item for item in self.remote.calls if item[0] != "GET"]
        self.assertEqual(writes[0][:2], ("DELETE", "/organizations/org_b/memberships/user_clerk"))
        self.assertFalse(any(path.endswith("/metadata") for _, path, _ in self.remote.calls))

    async def test_tenant_admin_cannot_change_other_memberships_or_global_metadata(self):
        self.user["global_role"] = "platform_admin"
        await self.directory.sync_access(self.user, self.associations, tenant_id="band-a")
        self.assertEqual(self.remote.roles["org_a"], "org:member")
        self.assertEqual(self.remote.roles["org_b"], "org:operator")
        self.assertFalse(any(path.endswith("/metadata") for _, path, _ in self.remote.calls))

    async def test_create_membership_and_retry_are_idempotent(self):
        self.remote.roles.pop("org_a")
        await self.directory.sync_access(self.user, self.associations, tenant_id="band-a")
        self.assertIn(("POST", "/organizations/org_a/memberships", {"user_id": "user_clerk", "role": "org:member"}), self.remote.calls)
        self.remote.calls.clear()
        await self.directory.sync_access(self.user, self.associations, tenant_id="band-a")
        self.assertTrue(all(method == "GET" for method, _, _ in self.remote.calls))

    async def test_disable_and_delete_revoke_access_without_deleting_account(self):
        self.user["status"] = "disabled"
        await self.directory.sync_access(self.user, self.associations)
        self.assertEqual(self.remote.roles, {"org_unrelated": "org:admin"})
        self.assertFalse(any(method == "DELETE" and path.startswith("/users/") for method, path, _ in self.remote.calls))

    async def test_tenant_disable_only_removes_own_membership(self):
        self.user["tenant_statuses"] = {"band-a": "disabled"}
        await self.directory.sync_access(self.user, self.associations, tenant_id="band-a")
        self.assertNotIn("org_a", self.remote.roles)
        self.assertIn("org_b", self.remote.roles)

    async def test_unverified_primary_email_and_reassigned_identity_do_not_mutate(self):
        for change in ("unverified", "different-account"):
            self.remote.calls.clear()
            self.remote.user["email_addresses"][0]["verification"]["status"] = "unverified" if change == "unverified" else "verified"
            self.user["clerk_user_id"] = "user_previous"
            with self.assertRaises(DomainError):
                await self.directory.sync_access(self.user, self.associations)
            self.assertTrue(all(method == "GET" for method, _, _ in self.remote.calls))

    async def test_mapping_and_secret_errors_fail_before_writes(self):
        with self.assertRaises(DomainError):
            await self.directory.sync_access(self.user, [])
        self.assertEqual(self.remote.calls, [])
        with self.assertRaises(DomainError):
            await ClerkDirectory(None, self.remote).sync_access(self.user, self.associations)
        self.assertEqual(self.remote.calls, [])

    async def test_partial_failure_can_be_retried(self):
        self.remote.failure = ("PATCH", "/organizations/org_a/memberships/user_clerk")
        with self.assertRaises(DomainError):
            await self.directory.sync_access(self.user, self.associations)
        self.assertNotIn("org_b", self.remote.roles)
        self.remote.failure = None
        await self.directory.sync_access(self.user, self.associations)
        self.assertEqual(self.remote.roles["org_a"], "org:member")

    async def test_provider_failure_identifies_operation_without_pii(self):
        class Response:
            status = 422

            async def text(self):
                return json.dumps({"errors": [{
                    "code": "form_param_value_invalid",
                    "message": "member@example.test test-secret",
                    "meta": {"email": "member@example.test"},
                }, {"code": "test-secret"}]})

        directory = ClerkDirectory("test-secret", AsyncMock(return_value=Response()))
        for path in ("/users?email_address[]=member@example.test",
                     "/organizations/org_private/memberships/user_private"):
            with self.assertRaises(DomainError) as caught:
                await directory.request("POST", path, {"role": "org:reader"})
            message = str(caught.exception)
            self.assertIn("HTTP 422", message)
            self.assertIn("form_param_value_invalid", message)
            for sensitive in ("member@example.test", "test-secret", "org_private", "user_private"):
                self.assertNotIn(sensitive, message)

    async def test_non_json_provider_failure_keeps_status(self):
        class Response:
            status = 401

            async def text(self):
                return "<html>private provider response</html>"

        directory = ClerkDirectory("test-secret", AsyncMock(return_value=Response()))
        with self.assertRaises(DomainError) as caught:
            await directory.find_user("member@example.test")
        self.assertIn("GET /users (HTTP 401)", str(caught.exception))
        self.assertNotIn("private provider response", str(caught.exception))

    async def test_reads_reflect_remote_roles_not_saved_grants(self):
        self.user["global_role"] = "platform_admin"
        self.user["member_links"] = [{"tenant_id": "band-a", "member_id": "member_a"}]
        self.remote.roles["org_a"] = "org:member"
        result = await self.directory.read_access(self.user, self.associations)
        self.assertEqual(result["global_role"], "none")
        self.assertEqual(result["tenant_profiles"], {"band-a": "basic", "band-b": "full"})
        self.assertEqual(result["tenant_roles"], [{"tenant_id": "band-a", "role": "reader"}, {"tenant_id": "band-b", "role": "operator"}])
        self.assertEqual(result["member_links"], self.user["member_links"])
        self.remote.roles.pop("org_a")
        refreshed = await self.directory.read_access(self.user, self.associations)
        self.assertEqual(refreshed["tenant_roles"], [{"tenant_id": "band-b", "role": "operator"}])
        self.assertTrue(all(method == "GET" for method, _, _ in self.remote.calls))

    async def test_missing_or_changed_identity_never_shows_old_grants(self):
        self.user["clerk_user_id"] = "user_old"
        result = await self.directory.read_access(self.user, self.associations)
        self.assertEqual(result["identity_status"], "account_changed")
        self.assertEqual(result["tenant_roles"], [])
        self.remote.user["email_addresses"][0]["verification"]["status"] = "unverified"
        result = await self.directory.read_access(self.user, self.associations)
        self.assertEqual(result["identity_status"], "not_registered")
        self.assertEqual(result["global_role"], "none")

    async def test_deleted_clerk_account_does_not_block_local_access_cleanup(self):
        self.user["clerk_user_id"] = "user_deleted"
        self.directory.request = AsyncMock(return_value=None)
        result = await self.directory.sync_access(self.user, self.associations, remove=True)
        self.assertIsNone(result)
        self.directory.request.assert_awaited_once_with("GET", "/users/user_deleted", allow_missing=True)

    async def test_admissions_read_clerk_members_and_only_public_fields(self):
        self.directory.request = AsyncMock(return_value={"id": "org_a", "name": "Brass Band", "has_image": True, "image_url": "https://img.clerk.com/logo", "private_metadata": {"secret": "hidden"}})
        self.directory.organization_memberships = AsyncMock(return_value=[{"id": "membership_new", "role": "org:member", "public_user_data": {"user_id": "user_new", "identifier": "new@example.test", "first_name": "New"}, "private_metadata": {"secret": "hidden"}}])
        self.directory.invitations = AsyncMock(return_value=[])
        result = await self.directory.admissions(self.associations[:1])
        self.assertEqual(result["organizations"][0]["name"], "Brass Band")
        self.assertEqual(result["memberships"][0]["user_id"], "user_new")
        self.assertEqual(result["memberships"][0]["access_profile"], "basic")
        self.assertNotIn("secret", json.dumps(result))

    async def test_organization_memberships_follow_pagination(self):
        self.directory.request = AsyncMock(side_effect=[{"data": [{"id": "first"}], "total_count": 2}, {"data": [{"id": "second"}], "total_count": 2}])
        result = await self.directory.organization_memberships("org_a")
        self.assertEqual([item["id"] for item in result], ["first", "second"])
        self.assertIn("offset=100", self.directory.request.call_args.args[1])
