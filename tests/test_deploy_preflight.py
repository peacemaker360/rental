import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.deploy_preflight import (
    validate_ci_workflow,
    validate_backend_wrangler,
    validate_frontend_assets,
    validate_frontdoor_wrangler,
    validate_gitignore,
    validate_no_legacy_runtime_dependencies,
    validate_no_wildcard_cors,
    validate_project,
    validate_uv_lock,
)


ROOT = Path(__file__).resolve().parents[1]


class DeployPreflightTests(unittest.TestCase):
    def test_local_refactor_preflight_passes_with_placeholders(self):
        errors, warnings = validate_project(ROOT, allow_placeholders=True)

        self.assertEqual(errors, [])
        self.assertTrue(any("placeholder Cloudflare ids allowed" in warning for warning in warnings))

    def test_strict_backend_preflight_rejects_placeholder_kv_ids(self):
        errors = []
        validate_backend_wrangler({
            "main": "worker/worker.py",
            "compatibility_flags": ["python_workers"],
            "kv_namespaces": [{
                "binding": "RENTAL_KV",
                "id": "replace-with-kv-id",
                "preview_id": "replace-with-preview-kv-id",
            }],
            "vars": {"RENTAL_AUTH_MODE": "auto"},
            "assets": {
                "directory": "./public",
                "binding": "ASSETS",
                "run_worker_first": ["/api/*"],
            },
        }, False, errors)

        self.assertTrue(any("RENTAL_KV id still uses a placeholder" in error for error in errors))
        self.assertTrue(any("RENTAL_KV preview_id still uses a placeholder" in error for error in errors))

    def test_uv_lock_guard_requires_valid_lockfile(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            errors: list[str] = []
            validate_uv_lock(root, errors)
            self.assertTrue(any("uv.lock is required" in error for error in errors))

            (root / "uv.lock").write_text("not a lock\n", encoding="utf-8")
            errors = []
            validate_uv_lock(root, errors)
            self.assertTrue(any("uv.lock must be a valid uv lockfile" in error for error in errors))

            (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
            errors = []
            validate_uv_lock(root, errors)
            self.assertTrue(any("uv.lock must lock workers-py" in error for error in errors))

            (root / "uv.lock").write_text('version = 1\n\n[[package]]\nname = "workers-py"\n', encoding="utf-8")
            errors = []
            validate_uv_lock(root, errors)
            self.assertEqual(errors, [])

    def test_preflight_rejects_removed_azure_workflows(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "public").mkdir()
            (root / "worker").mkdir()
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "cloudflare_refactor_ci.yml").write_text(
                "run: npm test\n"
                "run: npm run smoke:signed\n"
                "run: python3 scripts/deploy_preflight.py --allow-placeholders --include-frontdoor\n"
                "run: npm run check:js\n"
                "run: npm ci\n",
                encoding="utf-8",
            )
            (root / ".github" / "workflows" / "master_mgwrent.yml").write_text("uses: azure/webapps-deploy@v3\n", encoding="utf-8")
            (root / "public" / "index.html").write_text(
                '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; connect-src \'self\'; object-src \'none\'; base-uri \'none\'">'
                '<meta name="referrer" content="no-referrer">'
                '<script src="/app.js"></script><link href="/styles.css"><section id="view"></section>',
                encoding="utf-8",
            )
            (root / "public" / "app.js").write_text("", encoding="utf-8")
            (root / "public" / "styles.css").write_text("", encoding="utf-8")
            (root / "worker" / "worker.py").write_text("", encoding="utf-8")
            (root / "worker" / "api_core.py").write_text("", encoding="utf-8")
            (root / "worker" / "domain.py").write_text("", encoding="utf-8")
            (root / "worker" / "storage.py").write_text("", encoding="utf-8")
            (root / ".gitignore").write_text("**/__pycache__\nnode_modules/\n.venv/\n.venv-workers/\n.wrangler/\n.data/local-kv/\n.env\n", encoding="utf-8")
            (root / "package.json").write_text('{"scripts": {}}', encoding="utf-8")
            (root / "pyproject.toml").write_text("", encoding="utf-8")
            (root / "wrangler.toml").write_text("", encoding="utf-8")

            errors, _ = validate_project(root, allow_placeholders=True)

        self.assertTrue(any("legacy path should be removed: .github/workflows/master_mgwrent.yml" in error for error in errors))

    def test_preflight_rejects_hidden_legacy_diagrams(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "public").mkdir()
            (root / "worker").mkdir()
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".docs" / "digramms").mkdir(parents=True)
            (root / ".docs" / "digramms" / "erDiagram.md").write_text(
                "Customer { string email string phone }\n",
                encoding="utf-8",
            )
            (root / ".github" / "workflows" / "cloudflare_refactor_ci.yml").write_text(
                "run: npm test\n"
                "run: npm run smoke:signed\n"
                "run: python3 scripts/deploy_preflight.py --allow-placeholders --include-frontdoor\n"
                "run: npm run check:js\n"
                "run: npm ci\n",
                encoding="utf-8",
            )
            (root / "public" / "index.html").write_text(
                '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; connect-src \'self\'; object-src \'none\'; base-uri \'none\'">'
                '<meta name="referrer" content="no-referrer">'
                '<script src="/app.js"></script><link href="/styles.css"><section id="view"></section>',
                encoding="utf-8",
            )
            (root / "public" / "app.js").write_text("", encoding="utf-8")
            (root / "public" / "styles.css").write_text("", encoding="utf-8")
            (root / "worker" / "worker.py").write_text("", encoding="utf-8")
            (root / "worker" / "api_core.py").write_text("", encoding="utf-8")
            (root / "worker" / "domain.py").write_text("", encoding="utf-8")
            (root / "worker" / "storage.py").write_text("", encoding="utf-8")
            (root / ".gitignore").write_text("**/__pycache__\nnode_modules/\n.venv/\n.venv-workers/\n.wrangler/\n.data/local-kv/\n.env\n", encoding="utf-8")
            (root / "package.json").write_text('{"scripts": {}}', encoding="utf-8")
            (root / "pyproject.toml").write_text("", encoding="utf-8")
            (root / "wrangler.toml").write_text("", encoding="utf-8")

            errors, _ = validate_project(root, allow_placeholders=True)

        self.assertTrue(any("legacy path should be removed: .docs" in error for error in errors))

    def test_strict_frontdoor_preflight_rejects_placeholder_access_values(self):
        errors = []
        validate_frontdoor_wrangler({
            "main": "frontdoor/access_context_worker.js",
            "kv_namespaces": [{
                "binding": "TENANT_ACCESS_KV",
                "id": "replace-with-tenant-access-kv-id",
                "preview_id": "replace-with-tenant-access-preview-kv-id",
            }],
            "services": [{"binding": "RENTAL_BACKEND", "service": "association-rental"}],
            "vars": {
                "CF_ACCESS_TEAM_DOMAIN": "replace-with-team-domain",
                "CF_ACCESS_AUD": "replace-with-aud",
            },
        }, False, errors)

        self.assertTrue(any("TENANT_ACCESS_KV id still uses a placeholder" in error for error in errors))
        self.assertTrue(any("vars.CF_ACCESS_TEAM_DOMAIN still uses a placeholder" in error for error in errors))
        self.assertTrue(any("vars.CF_ACCESS_AUD still uses a placeholder" in error for error in errors))

    def test_frontdoor_preflight_passes_when_placeholders_are_allowed(self):
        errors, warnings = validate_project(ROOT, allow_placeholders=True, include_frontdoor=True)

        self.assertEqual(errors, [])
        self.assertTrue(any("RENTAL_CONTEXT_SECRET" in warning for warning in warnings))

    def test_runtime_dependency_guard_rejects_legacy_imports_and_dependencies(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "worker").mkdir()
            (root / "frontdoor").mkdir()
            (root / "worker" / "bad.py").write_text("from flask import Flask\nimport sqlalchemy\n", encoding="utf-8")
            (root / "frontdoor" / "bad.js").write_text("const azure = require('azure-storage');\n", encoding="utf-8")
            (root / "pyproject.toml").write_text('dependencies = ["alembic>=1.0"]\n', encoding="utf-8")

            errors: list[str] = []
            validate_no_legacy_runtime_dependencies(root, errors)

        self.assertTrue(any("legacy runtime dependency 'flask' found in worker/bad.py:1" in error for error in errors))
        self.assertTrue(any("legacy runtime dependency 'sqlalchemy' found in worker/bad.py:2" in error for error in errors))
        self.assertTrue(any("legacy runtime dependency 'azure-storage' found in frontdoor/bad.js:1" in error for error in errors))
        self.assertTrue(any("legacy runtime dependency 'alembic' found in pyproject.toml:1" in error for error in errors))

    def test_runtime_dependency_guard_allows_migration_text(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "scripts" / "migrate_legacy.py").write_text(
                'description = "Transform legacy Flask rental exports into the KV JSON package."\n',
                encoding="utf-8",
            )

            errors: list[str] = []
            validate_no_legacy_runtime_dependencies(root, errors)

        self.assertEqual(errors, [])

    def test_wildcard_cors_guard_rejects_runtime_headers(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "worker").mkdir()
            (root / "worker" / "bad.py").write_text(
                'JSON_HEADERS = {"access-control-allow-origin": "*"}\n',
                encoding="utf-8",
            )

            errors: list[str] = []
            validate_no_wildcard_cors(root, errors)

        self.assertTrue(any("wildcard CORS origin found in worker/bad.py:1" in error for error in errors))

    def test_wildcard_cors_guard_accepts_same_origin_headers(self):
        errors: list[str] = []
        validate_no_wildcard_cors(ROOT, errors)

        self.assertEqual(errors, [])

    def test_gitignore_guard_requires_local_artifact_patterns(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".gitignore").write_text("node_modules/\n.env\n", encoding="utf-8")

            errors: list[str] = []
            validate_gitignore(root, errors)

        self.assertTrue(any("**/__pycache__" in error for error in errors))
        self.assertTrue(any(".venv/" in error for error in errors))
        self.assertTrue(any(".venv-workers/" in error for error in errors))
        self.assertTrue(any(".wrangler/" in error for error in errors))
        self.assertTrue(any(".data/local-kv/" in error for error in errors))

    def test_gitignore_guard_accepts_refactor_local_artifact_patterns(self):
        errors: list[str] = []
        validate_gitignore(ROOT, errors)

        self.assertEqual(errors, [])

    def test_frontend_asset_guard_requires_security_metadata(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "public").mkdir()
            (root / "public" / "index.html").write_text(
                '<script src="/app.js"></script><link href="/styles.css"><section id="view"></section>',
                encoding="utf-8",
            )

            errors: list[str] = []
            validate_frontend_assets(root, errors)

        self.assertTrue(any("Content-Security-Policy" in error for error in errors))
        self.assertTrue(any("no-referrer" in error for error in errors))

    def test_local_debug_server_uses_pathlib_static_containment(self):
        source = (ROOT / "scripts" / "local_dev_server.py").read_text(encoding="utf-8")

        self.assertIn("def static_path_for", source)
        self.assertIn("candidate.is_relative_to(public_root)", source)
        self.assertNotIn("startswith(str(PUBLIC_DIR.resolve()))", source)

    def test_ci_workflow_guard_rejects_legacy_or_incomplete_workflow(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "cloudflare_refactor_ci.yml").write_text(
                "run: pip install -r requirements.txt\nuses: azure/webapps-deploy@v3\n",
                encoding="utf-8",
            )

            errors: list[str] = []
            validate_ci_workflow(root, errors)

        self.assertTrue(any("must run 'npm test'" in error for error in errors))
        self.assertTrue(any("legacy deployment reference 'azure/'" in error for error in errors))
        self.assertTrue(any("legacy deployment reference 'requirements.txt'" in error for error in errors))

    def test_ci_workflow_guard_accepts_cloudflare_refactor_workflow(self):
        errors: list[str] = []
        validate_ci_workflow(ROOT, errors)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
