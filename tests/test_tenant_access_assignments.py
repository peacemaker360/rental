import json
import tempfile
import unittest
from pathlib import Path

from scripts.sign_context import main as sign_context_main
from scripts.tenant_access_assignments import main, normalize_assignment, render_commands, render_kv_bulk


class TenantAccessAssignmentTests(unittest.TestCase):
    def test_normalize_assignment_uses_opaque_principal_key(self):
        assignment = normalize_assignment({
            "access_sub": "access-user-123",
            "tenant_id": "music-club",
            "role": "operator",
            "actor_id": "roster-user-42",
        })

        self.assertEqual(assignment["key"], "principal:access-user-123")
        self.assertEqual(assignment["value"], {
            "tenant_id": "music-club",
            "role": "operator",
            "actor_id": "roster-user-42",
        })

    def test_assignment_rejects_pii_like_fields(self):
        with self.assertRaisesRegex(ValueError, "PII-like fields"):
            normalize_assignment({
                "access_sub": "access-user-123",
                "tenant_id": "music-club",
                "role": "viewer",
                "email": "person@example.test",
            })
        with self.assertRaisesRegex(ValueError, "PII-like fields"):
            normalize_assignment({
                "access_sub": "access-user-123",
                "tenant_id": "music-club",
                "role": "viewer",
                "given_name": "Private",
            })

    def test_assignment_rejects_email_principal_and_actor(self):
        with self.assertRaisesRegex(ValueError, "not an email address"):
            normalize_assignment({
                "access_sub": "person@example.test",
                "tenant_id": "music-club",
                "role": "viewer",
            })
        with self.assertRaisesRegex(ValueError, "actor_id must be opaque"):
            normalize_assignment({
                "access_sub": "access-user-123",
                "tenant_id": "music-club",
                "role": "viewer",
                "actor_id": "person@example.test",
            })

    def test_assignment_rejects_phone_principal(self):
        with self.assertRaisesRegex(ValueError, "principal must be opaque, not a phone number"):
            normalize_assignment({
                "access_sub": "+41 44 000 00 00",
                "tenant_id": "music-club",
                "role": "viewer",
            })

    def test_assignment_rejects_phone_actor(self):
        with self.assertRaisesRegex(ValueError, "actor_id must be opaque, not a phone number"):
            normalize_assignment({
                "access_sub": "access-user-123",
                "tenant_id": "music-club",
                "role": "viewer",
                "actor_id": "+41 44 000 00 00",
            })

    def test_assignment_validates_tenant_and_role(self):
        with self.assertRaisesRegex(ValueError, "tenant id must use"):
            normalize_assignment({"access_sub": "sub-1", "tenant_id": "Bad Tenant", "role": "viewer"})
        with self.assertRaisesRegex(ValueError, "role must be one of"):
            normalize_assignment({"access_sub": "sub-1", "tenant_id": "tenant-a", "role": "owner"})

    def test_render_kv_bulk_and_commands(self):
        assignments = [
            normalize_assignment({"sub": "sub-1", "tenant": "tenant-a", "role": "admin"}),
        ]

        bulk = render_kv_bulk(assignments)
        self.assertEqual(bulk[0]["key"], "principal:sub-1")
        self.assertEqual(json.loads(bulk[0]["value"]), {"tenant_id": "tenant-a", "role": "admin"})

        commands = render_commands(assignments, "TENANT_ACCESS_KV", "wrangler.frontdoor.toml", True)
        self.assertIn("npx wrangler kv key put principal:sub-1", commands[0])
        self.assertIn("--binding TENANT_ACCESS_KV", commands[0])
        self.assertIn("--config wrangler.frontdoor.toml", commands[0])
        self.assertIn("--preview", commands[0])

    def test_cli_renders_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "assignments.json"
            output = Path(temp_dir) / "summary.json"
            source.write_text(json.dumps({
                "assignments": [
                    {"access_sub": "sub-1", "tenant_id": "tenant-a", "role": "admin"},
                    {"access_sub": "sub-2", "tenant_id": "tenant-a", "role": "viewer"},
                ]
            }), encoding="utf-8")

            status = main([str(source), "--format", "summary", "--output", str(output)])

            self.assertEqual(status, 0)
            summary = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(summary["assignments"], 2)
            self.assertEqual(summary["tenants"], ["tenant-a"])
            self.assertEqual(summary["roles"]["admin"], 1)
            self.assertEqual(summary["roles"]["viewer"], 1)

    def test_signed_context_helper_rejects_contact_like_actor(self):
        with self.assertRaisesRegex(SystemExit, "actor_id must be opaque"):
            sign_context_main([
                "--tenant", "tenant-a",
                "--actor", "person@example.test",
                "--secret", "dev-secret",
            ])


if __name__ == "__main__":
    unittest.main()
