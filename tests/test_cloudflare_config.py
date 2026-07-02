import asyncio
import importlib.util
import json
import sys
import tomllib
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_worker_module_for_test():
    workers_stub = types.ModuleType("workers")

    class Response:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class WorkerEntrypoint:
        pass

    workers_stub.Response = Response
    workers_stub.WorkerEntrypoint = WorkerEntrypoint
    previous = sys.modules.get("workers")
    sys.modules["workers"] = workers_stub
    try:
        spec = importlib.util.spec_from_file_location("worker.worker_test_runtime", ROOT / "worker" / "worker.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            sys.modules.pop("workers", None)
        else:
            sys.modules["workers"] = previous


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

        self.assertEqual(scripts["dev"], "uv run pywrangler dev")
        self.assertEqual(scripts["deploy"], "uv run pywrangler deploy")
        self.assertEqual(scripts["preflight"], "python3 scripts/deploy_preflight.py --allow-placeholders")
        self.assertEqual(scripts["preflight:deploy"], "python3 scripts/deploy_preflight.py")
        self.assertEqual(scripts["preflight:frontdoor"], "python3 scripts/deploy_preflight.py --include-frontdoor")
        self.assertEqual(scripts["smoke:signed"], "python3 scripts/smoke_local.py --signed")
        self.assertIn("wrangler dev --config wrangler.frontdoor.toml", scripts["dev:frontdoor"])
        self.assertIn("wrangler deploy --config wrangler.frontdoor.toml", scripts["deploy:frontdoor"])
        self.assertIn("TENANT_ACCESS_KV", scripts["kv:create-tenant-access"])

    def test_pyproject_declares_python_worker_tooling(self):
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(pyproject["project"]["requires-python"], ">=3.12")
        self.assertIn("workers-py>=0.2.0", pyproject["dependency-groups"]["dev"])

    def test_cloudflare_refactor_ci_uses_local_validation_not_azure_deploy(self):
        source = (ROOT / ".github" / "workflows" / "cloudflare_refactor_ci.yml").read_text(encoding="utf-8")

        self.assertIn("python3 -m unittest discover -s tests", source)
        self.assertIn("python3 scripts/smoke_local.py --signed", source)
        self.assertIn("python3 scripts/deploy_preflight.py --allow-placeholders --include-frontdoor", source)
        self.assertIn("node --check public/app.js", source)
        self.assertIn("npm ci", source)
        self.assertNotIn("azure/", source.lower())
        self.assertNotIn("requirements.txt", source)

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

    def test_backend_worker_rejects_malformed_json_bodies(self):
        source = (ROOT / "worker" / "worker.py").read_text(encoding="utf-8")

        self.assertIn("class InvalidJsonBody", source)
        self.assertIn("invalid JSON body", source)
        self.assertIn("await request.text()", source)
        self.assertIn("json.loads(raw)", source)
        self.assertIn('return json_response({"error": str(exc)}, 400)', source)

    def test_backend_worker_keeps_empty_api_path_in_json_api_boundary(self):
        source = (ROOT / "worker" / "worker.py").read_text(encoding="utf-8")

        self.assertIn("is_api_request_path", source)
        self.assertIn('return json_response({"error": "route not found"}, 404)', source)

    def test_backend_worker_parses_json_without_content_length(self):
        module = load_worker_module_for_test()

        class RequestWithoutContentLength:
            async def text(self):
                return '{"name": "Piano"}'

        payload = asyncio.run(module.request_json(RequestWithoutContentLength()))

        self.assertEqual(payload, {"name": "Piano"})

    def test_backend_worker_treats_empty_body_as_empty_object(self):
        module = load_worker_module_for_test()

        class EmptyRequest:
            async def text(self):
                return ""

        self.assertEqual(asyncio.run(module.request_json(EmptyRequest())), {})

    def test_backend_worker_rejects_invalid_json_body(self):
        module = load_worker_module_for_test()

        class BadRequest:
            async def text(self):
                return '{"name":'

        with self.assertRaisesRegex(module.InvalidJsonBody, "invalid JSON body"):
            asyncio.run(module.request_json(BadRequest()))

    def test_backend_worker_marks_api_json_uncacheable(self):
        source = (ROOT / "worker" / "worker.py").read_text(encoding="utf-8")

        self.assertIn('"cache-control": "no-store"', source)
        self.assertIn('"pragma": "no-cache"', source)
        self.assertIn('"referrer-policy": "no-referrer"', source)
        self.assertIn('"x-content-type-options": "nosniff"', source)
        self.assertNotIn('"access-control-allow-origin": "*"', source)


if __name__ == "__main__":
    unittest.main()
