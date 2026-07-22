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
        self.assertEqual(config["vars"]["CF_ACCESS_TEAM_DOMAIN"], "kittythecat.cloudflareaccess.com")
        self.assertNotIn("kv_namespaces", config["vars"])
        self.assertEqual(config["kv_namespaces"][0]["binding"], "RENTAL_KV")
        self.assertTrue(any(item["binding"] == "TENANT_ACCESS_KV" for item in config["kv_namespaces"]))
        self.assertEqual(config["assets"]["binding"], "ASSETS")
        self.assertEqual(config["assets"]["run_worker_first"], ["/api/*", "/auth/logout"])

    def test_frontdoor_wrangler_binds_backend_and_assignment_kv(self):
        config = tomllib.loads((ROOT / "wrangler.frontdoor.toml").read_text(encoding="utf-8"))

        self.assertEqual(config["main"], "frontdoor/access_context_worker.js")
        self.assertEqual(config["kv_namespaces"][0]["binding"], "TENANT_ACCESS_KV")
        self.assertEqual(config["services"][0]["binding"], "RENTAL_BACKEND")
        self.assertIn("CF_ACCESS_TEAM_DOMAIN", config["vars"])
        self.assertIn("CF_ACCESS_AUD", config["vars"])
        self.assertFalse(config["workers_dev"])
        route_patterns = {item["pattern"] for item in config["routes"]}
        self.assertEqual(route_patterns, {"rental.kittythecat.ch/api/*"})
        self.assertTrue(all(item["zone_name"] == "kittythecat.ch" for item in config["routes"]))

    def test_package_exposes_frontdoor_scripts(self):
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        scripts = package["scripts"]

        self.assertEqual(scripts["dev"], "uv run pywrangler dev")
        self.assertEqual(scripts["deploy"], "uv run pywrangler deploy")
        self.assertEqual(scripts["preflight"], "python3 scripts/deploy_preflight.py --allow-placeholders")
        self.assertEqual(scripts["preflight:deploy"], "python3 scripts/deploy_preflight.py")
        self.assertEqual(scripts["preflight:frontdoor"], "python3 scripts/deploy_preflight.py --include-frontdoor")
        self.assertEqual(scripts["smoke:signed"], "PYTHONPATH=.:worker python3 scripts/smoke_local.py --signed")
        self.assertEqual(scripts["check:js"], "node --check public/app.js && node --check frontdoor/access_context_worker.js")
        self.assertIn("wrangler dev --config wrangler.frontdoor.toml", scripts["dev:frontdoor"])
        self.assertIn("wrangler deploy --config wrangler.frontdoor.toml", scripts["deploy:frontdoor"])
        self.assertIn("TENANT_ACCESS_KV", scripts["kv:create-tenant-access"])

    def test_pyproject_declares_python_worker_tooling(self):
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(pyproject["project"]["requires-python"], ">=3.12")
        self.assertIn("workers-py>=1.14.0", pyproject["dependency-groups"]["dev"])
        self.assertIn("workers-runtime-sdk", pyproject["dependency-groups"]["dev"])

    def test_cloudflare_refactor_ci_uses_local_validation_not_azure_deploy(self):
        source = (ROOT / ".github" / "workflows" / "cloudflare_refactor_ci.yml").read_text(encoding="utf-8")

        self.assertIn("npm test", source)
        self.assertIn("npm run smoke:signed", source)
        self.assertIn("python3 scripts/deploy_preflight.py --allow-placeholders --include-frontdoor", source)
        self.assertIn("npm run check:js", source)
        self.assertIn("npm ci", source)
        self.assertNotIn("azure/", source.lower())
        self.assertNotIn("requirements.txt", source)

    def test_frontdoor_strips_untrusted_identity_headers(self):
        source = (ROOT / "frontdoor" / "access_context_worker.js").read_text(encoding="utf-8")

        self.assertIn("cf-access-jwt-assertion", source)
        self.assertIn("/cdn-cgi/access/certs", source)
        self.assertIn("RSASSA-PKCS1-v1_5", source)
        self.assertIn("claims.email", source)
        self.assertIn("validEmail(email)", source)
        self.assertIn("valid email is required", source)
        self.assertIn("user:${email}", source)
        self.assertIn("resolveUserAssignment", source)
        self.assertIn('const LOGIN_PATH = "/api/auth/login"', source)
        self.assertLess(source.index("url.pathname === LOGIN_PATH"), source.index('url.pathname === "/api/health"'))
        self.assertIn('url.pathname === "/api/access-requests" && request.method === "POST"', source)
        self.assertIn("return createAccessRequest(request, env, null)", source)
        self.assertIn('!url.pathname.startsWith("/api/")', source)
        self.assertIn('url.pathname === LOGIN_PATH', source)
        self.assertIn("return completeAccessLogin(request, env)", source)
        self.assertIn("async function completeAccessLogin(request, env)", source)
        self.assertIn("await verifyAccessJwt(accessJwt, env)", source)
        self.assertIn('return forwardToBackend(rewriteRequestPath(request, "/"), env, null)', source)
        self.assertIn("function rewriteRequestPath(request, pathname)", source)
        self.assertNotIn('return redirectResponse("/")', source)
        self.assertIn("function authenticatedErrorBody(error, claims)", source)
        self.assertIn("body.user_email = email", source)
        self.assertIn("return jsonResponse(authenticatedErrorBody(error, claims), error.status || 403)", source)
        self.assertIn("claims?.email || payload.email", source)
        self.assertIn("association_contact:${tenantId}", source)
        self.assertIn("item.association", source)
        self.assertIn('url.pathname === "/api/access-requests" && request.method === "POST"', source)
        self.assertIn('!url.pathname.startsWith("/api/")', source)
        self.assertIn("return forwardToBackend(request, env, null)", source)
        self.assertIn("validateUserProfile(user)", source)
        self.assertIn('const ACCESS_PROFILES = new Set(["full", "basic"])', source)
        self.assertIn("user access profile has invalid access profile", source)
        self.assertIn("user access profile tenant roles must be a list", source)
        self.assertIn("user access profile has invalid member id", source)
        self.assertIn("opaqueMemberId(item.member_id)", source)
        self.assertIn("tenant_roles", source)
        self.assertIn("access_profile", source)
        self.assertIn("member_id", source)
        self.assertIn("firstMemberLink(user)?.tenant_id", source)
        self.assertIn('user.access_profile === "basic" && (user.member_links || []).some', source)
        self.assertIn('const adminRoute = url.pathname.startsWith("/api/admin")', source)
        self.assertIn('const platformAdminRoute = adminRoute && user.global_role === "platform_admin"', source)
        self.assertIn('platformAdminRoute\n    ? "platform-admin"', source)
        self.assertIn('globalRole === "platform_admin" && tenantId === "platform-admin"', source)
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

    def test_backend_worker_redirects_logout_to_access_team_domain(self):
        module = load_worker_module_for_test()
        response = module.access_logout_response(
            types.SimpleNamespace(CF_ACCESS_TEAM_DOMAIN="kittythecat.cloudflareaccess.com"),
            "GET",
        )

        self.assertEqual(response.kwargs["status"], 302)
        self.assertEqual(
            response.kwargs["headers"]["location"],
            "https://kittythecat.cloudflareaccess.com/cdn-cgi/access/logout",
        )
        self.assertEqual(response.kwargs["headers"]["cache-control"], "no-store")
        self.assertIn("CF_Authorization=; Max-Age=0", response.kwargs["headers"]["set-cookie"])
        self.assertEqual(response.kwargs["headers"]["x-rental-auth-handler"], "backend")

    def test_backend_worker_rejects_unconfigured_logout(self):
        module = load_worker_module_for_test()
        response = module.access_logout_response(types.SimpleNamespace(), "GET")

        self.assertEqual(response.kwargs["status"], 503)

    def test_backend_worker_cors_allows_trusted_access_profile_headers(self):
        module = load_worker_module_for_test()
        allowed = module.JSON_HEADERS["access-control-allow-headers"]

        self.assertIn("x-rental-access-profile", allowed)
        self.assertIn("x-rental-member-id", allowed)
        self.assertIn("x-rental-user-email", allowed)

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
