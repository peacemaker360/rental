import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CloudflareConfigTests(unittest.TestCase):
    def test_backend_wrangler_has_top_level_kv_binding(self):
        config = tomllib.loads((ROOT / "wrangler.toml").read_text(encoding="utf-8"))

        self.assertEqual(config["main"], "worker/worker.py")
        self.assertEqual(config["compatibility_flags"], ["python_workers"])
        self.assertEqual(config["vars"]["RENTAL_AUTH_MODE"], "auto")
        self.assertNotIn("kv_namespaces", config["vars"])
        self.assertEqual(config["kv_namespaces"][0]["binding"], "RENTAL_KV")
        self.assertEqual(config["assets"]["binding"], "ASSETS")
        self.assertEqual(config["assets"]["run_worker_first"], ["/api/*"])

    def test_frontdoor_wrangler_binds_backend_and_assignment_kv(self):
        config = tomllib.loads((ROOT / "wrangler.frontdoor.toml").read_text(encoding="utf-8"))

        self.assertEqual(config["main"], "frontdoor/access_context_worker.js")
        self.assertEqual(config["kv_namespaces"][0]["binding"], "TENANT_ACCESS_KV")
        self.assertEqual(config["services"][0]["binding"], "RENTAL_BACKEND")
        self.assertIn("CF_ACCESS_TEAM_DOMAIN", config["vars"])
        self.assertIn("CF_ACCESS_AUD", config["vars"])

    def test_package_exposes_frontdoor_scripts(self):
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        scripts = package["scripts"]

        self.assertIn("wrangler dev --config wrangler.frontdoor.toml", scripts["dev:frontdoor"])
        self.assertIn("wrangler deploy --config wrangler.frontdoor.toml", scripts["deploy:frontdoor"])
        self.assertIn("TENANT_ACCESS_KV", scripts["kv:create-tenant-access"])

    def test_frontdoor_strips_untrusted_identity_headers(self):
        source = (ROOT / "frontdoor" / "access_context_worker.js").read_text(encoding="utf-8")

        self.assertIn("cf-access-jwt-assertion", source)
        self.assertIn("/cdn-cgi/access/certs", source)
        self.assertIn("RSASSA-PKCS1-v1_5", source)
        self.assertIn("principal:${principal}", source)
        self.assertIn('headers.delete("cf-access-authenticated-user-email")', source)
        self.assertIn('headers.delete("cookie")', source)
        self.assertIn('headers.delete("authorization")', source)
        self.assertIn("startsWith(RENTAL_HEADER_PREFIX)", source)
        self.assertIn("TENANT_ACCESS_KV", source)
        self.assertIn("RENTAL_CONTEXT_SECRET", source)


if __name__ == "__main__":
    unittest.main()
