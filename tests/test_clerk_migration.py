import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.error import HTTPError

from domain import DomainError
from scripts.migrate_clerk_access import apply_plan, http_transport, main, migration_plan
from worker.clerk_directory import ClerkDirectory


class ClerkMigrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.associations = [{"tenant_id": "band-a", "clerk_organization_id": "org_a"}]
        self.user = {"email": "member@example.test", "access_profile": "basic", "global_role": "none", "member_links": [{"tenant_id": "band-a", "member_id": "member_a"}]}

    def test_standalone_cli_without_pythonpath(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "migrate_clerk_access.py"
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env.pop("CLERK_SECRET_KEY", None)
        with tempfile.TemporaryDirectory() as temp:
            users = Path(temp) / "users.json"
            associations = Path(temp) / "associations.json"
            users.write_text(json.dumps([self.user]), encoding="utf-8")
            associations.write_text(json.dumps(self.associations), encoding="utf-8")
            for args, expected in [
                (["--help"], 0),
                ([], 2),
                (["--users", str(users), "--associations", str(associations)], 0),
            ]:
                with self.subTest(args=args):
                    result = subprocess.run(
                        [sys.executable, "-I", str(script), *args],
                        cwd=temp, env=env, capture_output=True, text=True, timeout=15,
                    )
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    if "--users" in args:
                        self.assertEqual(json.loads(result.stdout)["network_requests"], 0)
                        self.assertNotIn(self.user["email"], result.stdout)

    def test_legacy_bulk_export_preserves_basic_member_only_access(self):
        users, associations = migration_plan({"schema": "tenant-access-kv-bulk", "data": [{"key": "user:member@example.test", "value": json.dumps(self.user)}]}, self.associations)
        self.assertEqual(users[0]["tenant_roles"], [{"tenant_id": "band-a", "role": "reader"}])
        self.assertEqual(users[0]["access_profile"], "basic")
        self.assertEqual(users[0]["member_links"], self.user["member_links"])
        self.assertEqual(associations[0]["clerk_organization_id"], "org_a")

    def test_invalid_or_ambiguous_inputs_fail_before_remote_work(self):
        for users, associations in [
            ([self.user, self.user], self.associations),
            ([self.user], []),
            ([{"key": "principal:old-sub", "value": json.dumps(self.user)}], self.associations),
            ([self.user], self.associations + [{"tenant_id": "band-b", "clerk_organization_id": "org_a"}]),
        ]:
            with self.assertRaises((ValueError, DomainError)):
                migration_plan(users, associations)

    def test_migration_preserves_disabled_tenant_and_pinned_identity(self):
        source = {**self.user, "clerk_user_id": "user_clerk", "tenant_statuses": {"band-a": "disabled"}}
        users, _ = migration_plan([source], self.associations)
        self.assertEqual(users[0]["tenant_statuses"], {"band-a": "disabled"})
        self.assertEqual(users[0]["clerk_user_id"], "user_clerk")

    def test_default_cli_mode_never_contacts_clerk_or_prints_email(self):
        with tempfile.TemporaryDirectory() as temp:
            users = Path(temp) / "users.json"
            associations = Path(temp) / "associations.json"
            users.write_text(json.dumps([self.user]))
            associations.write_text(json.dumps(self.associations))
            output = io.StringIO()
            with patch("scripts.migrate_clerk_access.http_transport", new_callable=AsyncMock) as transport, contextlib.redirect_stdout(output):
                result = main(["--users", str(users), "--associations", str(associations)])
            self.assertEqual(result, 0)
            transport.assert_not_called()
            self.assertNotIn(self.user["email"], output.getvalue())
            self.assertEqual(json.loads(output.getvalue())["network_requests"], 0)

    async def test_apply_reports_failure_by_opaque_id_and_can_be_retried(self):
        users, associations = migration_plan([self.user], self.associations)
        directory = type("Directory", (), {})()
        directory.sync_access = AsyncMock(side_effect=DomainError("Provider unavailable", 503))
        failed = await apply_plan(users, associations, directory)
        self.assertEqual(failed[0]["status"], "failed")
        self.assertNotIn(self.user["email"], json.dumps(failed))
        directory.sync_access = AsyncMock(return_value="user_clerk")
        retried = await apply_plan(users, associations, directory)
        self.assertEqual(retried[0]["status"], "applied")

    async def test_cli_transport_preserves_safe_provider_diagnostics(self):
        body = json.dumps({"errors": [{"code": "form_param_value_invalid",
                                      "message": "private@example.test secret"}]}).encode()
        error = HTTPError("https://api.clerk.com/v1/users", 422, "Invalid", {}, io.BytesIO(body))
        directory = ClerkDirectory("secret", http_transport)
        with patch("scripts.migrate_clerk_access.urlopen", side_effect=error):
            with self.assertRaises(DomainError) as caught:
                await directory.find_user("private@example.test")
        self.assertIn("GET /users (HTTP 422; code=form_param_value_invalid)", str(caught.exception))
        self.assertNotIn("private@example.test", str(caught.exception))
        self.assertNotIn("secret", str(caught.exception))

    async def test_cli_transport_identifies_app_instead_of_default_python_agent(self):
        def respond(request, timeout):
            self.assertEqual(request.get_header("User-agent"), "RentalDesk/0.1")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-only")
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(timeout, 30)
            response = io.BytesIO(b"[]")
            response.status = 200
            return response

        with patch("scripts.migrate_clerk_access.urlopen", side_effect=respond):
            result = await http_transport("https://api.clerk.com/v1/users?limit=1",
                                          method="GET", headers={"Authorization": "Bearer test-only"})
        self.assertEqual(result.status, 200)
        self.assertEqual(await result.text(), "[]")
