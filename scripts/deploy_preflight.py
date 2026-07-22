from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = (
    "public/index.html",
    "public/app.js",
    "public/styles.css",
    "worker/worker.py",
    "worker/api_core.py",
    "worker/domain.py",
    "worker/storage.py",
    "wrangler.toml",
    "pyproject.toml",
    "package.json",
    ".github/workflows/cloudflare_refactor_ci.yml",
)

REMOVED_LEGACY_PATHS = (
    "app",
    "azure_iac",
    "config",
    ".docs",
    "migrations",
    "migrations_old",
    ".flaskenv",
    "alembic.ini",
    "requirements.txt",
    "requirements_1.txt",
    "run.py",
    "startup.sh",
    ".github/workflows/hosting_mgwrent.yml",
    ".github/workflows/master_mgwrent.yml",
)

RUNTIME_SCAN_DIRS = (
    "worker",
    "scripts",
    "public",
    "frontdoor",
)

RUNTIME_SCAN_FILES = (
    "package.json",
    "pyproject.toml",
    "wrangler.toml",
    "wrangler.frontdoor.toml",
)

LEGACY_PYTHON_IMPORT = re.compile(r"^\s*(?:from|import)\s+(flask|sqlalchemy|alembic|azure)(?:[.\s]|$)", re.IGNORECASE)
LEGACY_JS_IMPORT = re.compile(
    r"^\s*(?:import\b.*\bfrom\s+|import\s*\(|(?:const|let|var)\b.*=\s*require\()\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
LEGACY_CONFIG_DEPENDENCY = re.compile(r"[\"']?(flask|sqlalchemy|alembic|azure[-_.a-z0-9]*)[\"']?\s*(?:[<>=!~]=?|[,;\]}\n]|$)", re.IGNORECASE)
CI_WORKFLOW_PATH = ".github/workflows/cloudflare_refactor_ci.yml"
CI_REQUIRED_SNIPPETS = (
    "npm test",
    "npm run smoke:signed",
    "python3 scripts/deploy_preflight.py --allow-placeholders --include-frontdoor",
    "npm run check:js",
    "npm ci",
)
CI_FORBIDDEN_SNIPPETS = (
    "azure/",
    "azureappsservice",
    "requirements.txt",
    "startup.sh",
)


def validate_project(
    root: Path = ROOT,
    *,
    allow_placeholders: bool = False,
    include_frontdoor: bool = False,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    root = root.resolve()

    for relative in REQUIRED_PATHS:
        require_path(root, relative, errors)
    for relative in REMOVED_LEGACY_PATHS:
        if (root / relative).exists():
            errors.append(f"legacy path should be removed: {relative}")

    package = read_json(root / "package.json", errors)
    pyproject = read_toml(root / "pyproject.toml", errors)
    backend = read_toml(root / "wrangler.toml", errors)

    if package:
        validate_package(package, errors)
    if pyproject:
        validate_pyproject(pyproject, errors)
    validate_uv_lock(root, errors)
    if backend:
        validate_backend_wrangler(backend, allow_placeholders, errors)
    validate_ci_workflow(root, errors)
    validate_frontend_assets(root, errors)
    validate_gitignore(root, errors)
    validate_no_legacy_runtime_dependencies(root, errors)
    validate_no_wildcard_cors(root, errors)

    if include_frontdoor:
        require_path(root, "frontdoor/access_context_worker.js", errors)
        require_path(root, "wrangler.frontdoor.toml", errors)
        frontdoor = read_toml(root / "wrangler.frontdoor.toml", errors)
        if frontdoor:
            validate_frontdoor_wrangler(frontdoor, allow_placeholders, errors)
    else:
        warnings.append("frontdoor config skipped; pass --include-frontdoor to validate Cloudflare Access routing")

    if allow_placeholders:
        warnings.append("placeholder Cloudflare ids allowed; omit --allow-placeholders before production deploy")
    warnings.append("RENTAL_CONTEXT_SECRET is a Cloudflare secret and must be set outside version control")
    return errors, warnings


def validate_package(package: dict[str, Any], errors: list[str]) -> None:
    scripts = package.get("scripts", {})
    expected = {
        "dev": "uv run pywrangler dev",
        "deploy": "uv run pywrangler deploy",
        "dev:python": "python3 scripts/local_dev_server.py",
        "test": "PYTHONPATH=.:worker python3 -m unittest discover -s tests",
        "smoke:python": "PYTHONPATH=.:worker python3 scripts/smoke_local.py",
        "smoke:signed": "PYTHONPATH=.:worker python3 scripts/smoke_local.py --signed",
        "tenant-access": "python3 scripts/tenant_access_assignments.py",
        "check:js": "node --check public/app.js && node --check frontdoor/access_context_worker.js",
    }
    for name, command in expected.items():
        if scripts.get(name) != command:
            errors.append(f"package.json script {name!r} must be {command!r}")
    for name in ("kv:create", "kv:create-preview", "kv:create-tenant-access", "deploy:frontdoor"):
        if name not in scripts:
            errors.append(f"package.json script {name!r} is required")


def validate_pyproject(pyproject: dict[str, Any], errors: list[str]) -> None:
    if pyproject.get("project", {}).get("requires-python") != ">=3.12":
        errors.append("pyproject.toml must require Python >=3.12 for Python Workers")
    dev_dependencies = pyproject.get("dependency-groups", {}).get("dev", [])
    if "workers-py>=1.14.0" not in dev_dependencies:
        errors.append("pyproject.toml dev dependency group must include workers-py>=1.14.0")
    if "workers-runtime-sdk" not in dev_dependencies:
        errors.append("pyproject.toml dev dependency group must include workers-runtime-sdk")


def validate_uv_lock(root: Path, errors: list[str]) -> None:
    path = root / "uv.lock"
    if not path.exists():
        errors.append("uv.lock is required for reproducible Python Worker tooling")
        return
    try:
        source = path.read_text(encoding="utf-8")
        first_line = source.splitlines()[0]
    except (OSError, IndexError) as exc:
        errors.append(f"could not read uv.lock: {exc}")
        return
    if first_line.strip() != "version = 1":
        errors.append("uv.lock must be a valid uv lockfile")
    if 'name = "workers-py"' not in source:
        errors.append("uv.lock must lock workers-py for Python Worker tooling")


def validate_backend_wrangler(config: dict[str, Any], allow_placeholders: bool, errors: list[str]) -> None:
    if config.get("main") != "worker/worker.py":
        errors.append("wrangler.toml main must be worker/worker.py")
    if "python_workers" not in config.get("compatibility_flags", []):
        errors.append("wrangler.toml must include python_workers compatibility flag")
    if config.get("vars", {}).get("RENTAL_AUTH_MODE") != "auto":
        errors.append("wrangler.toml must set RENTAL_AUTH_MODE=auto")

    namespace = namespace_by_binding(config, "RENTAL_KV")
    if not namespace:
        errors.append("wrangler.toml must bind RENTAL_KV")
    else:
        validate_namespace_ids(namespace, "RENTAL_KV", allow_placeholders, errors)

    assets = config.get("assets", {})
    if assets.get("directory") != "./public":
        errors.append("wrangler.toml assets.directory must be ./public")
    if assets.get("binding") != "ASSETS":
        errors.append("wrangler.toml assets.binding must be ASSETS")
    if "/api/*" not in assets.get("run_worker_first", []):
        errors.append("wrangler.toml assets.run_worker_first must include /api/*")


def validate_frontdoor_wrangler(config: dict[str, Any], allow_placeholders: bool, errors: list[str]) -> None:
    if config.get("main") != "frontdoor/access_context_worker.js":
        errors.append("wrangler.frontdoor.toml main must be frontdoor/access_context_worker.js")
    if config.get("workers_dev") is not False:
        errors.append("wrangler.frontdoor.toml workers_dev must be false for production routing")

    route_patterns = {str(item.get("pattern", "")) for item in config.get("routes", [])}
    for pattern in ("rental.kittythecat.ch/api/*", "rental.kittythecat.ch/auth/*"):
        if pattern not in route_patterns:
            errors.append(f"wrangler.frontdoor.toml routes must include {pattern}")

    namespace = namespace_by_binding(config, "TENANT_ACCESS_KV")
    if not namespace:
        errors.append("wrangler.frontdoor.toml must bind TENANT_ACCESS_KV")
    else:
        validate_namespace_ids(namespace, "TENANT_ACCESS_KV", allow_placeholders, errors)

    services = config.get("services", [])
    if not any(item.get("binding") == "RENTAL_BACKEND" and item.get("service") == "association-rental" for item in services):
        errors.append("wrangler.frontdoor.toml must bind RENTAL_BACKEND service to association-rental")

    vars_ = config.get("vars", {})
    for name in ("CF_ACCESS_TEAM_DOMAIN", "CF_ACCESS_AUD"):
        value = str(vars_.get(name, ""))
        if not value:
            errors.append(f"wrangler.frontdoor.toml vars.{name} is required")
        elif not allow_placeholders and looks_placeholder(value):
            errors.append(f"wrangler.frontdoor.toml vars.{name} still uses a placeholder")


def validate_namespace_ids(
    namespace: dict[str, Any],
    binding: str,
    allow_placeholders: bool,
    errors: list[str],
) -> None:
    for field in ("id", "preview_id"):
        value = str(namespace.get(field, ""))
        if not value:
            errors.append(f"{binding} {field} is required")
        elif not allow_placeholders and looks_placeholder(value):
            errors.append(f"{binding} {field} still uses a placeholder")


def validate_frontend_assets(root: Path, errors: list[str]) -> None:
    index_path = root / "public/index.html"
    if not index_path.exists():
        return
    index = index_path.read_text(encoding="utf-8")
    if "/app.js" not in index:
        errors.append("public/index.html must load /app.js")
    if "/styles.css" not in index:
        errors.append("public/index.html must load /styles.css")
    if 'id="view"' not in index:
        errors.append("public/index.html must contain the app view mount")
    if 'http-equiv="Content-Security-Policy"' not in index:
        errors.append("public/index.html must declare a Content-Security-Policy meta tag")
    for directive in ("default-src 'self'", "connect-src 'self'", "object-src 'none'", "base-uri 'none'"):
        if directive not in index:
            errors.append(f"public/index.html Content-Security-Policy must include {directive}")
    if 'name="referrer" content="no-referrer"' not in index:
        errors.append("public/index.html must declare no-referrer metadata")


def validate_ci_workflow(root: Path, errors: list[str]) -> None:
    path = root / CI_WORKFLOW_PATH
    if not path.exists():
        return
    source = path.read_text(encoding="utf-8")
    source_lower = source.lower()
    for snippet in CI_REQUIRED_SNIPPETS:
        if snippet not in source:
            errors.append(f"{CI_WORKFLOW_PATH} must run {snippet!r}")
    for snippet in CI_FORBIDDEN_SNIPPETS:
        if snippet in source_lower:
            errors.append(f"{CI_WORKFLOW_PATH} must not contain legacy deployment reference {snippet!r}")


def validate_gitignore(root: Path, errors: list[str]) -> None:
    path = root / ".gitignore"
    if not path.exists():
        errors.append(".gitignore is required to keep local debug artifacts out of the refactor")
        return
    ignored = {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    required = {
        "**/__pycache__": "Python bytecode caches",
        "node_modules/": "installed Node packages",
        ".venv/": "local Python virtual environment",
        ".venv-workers/": "local Python Worker virtual environment",
        ".wrangler/": "Wrangler local state",
        ".data/local-kv/": "local JSON KV debug data",
        ".env": "local secrets",
    }
    for pattern, description in required.items():
        if pattern not in ignored:
            errors.append(f".gitignore must ignore {description}: {pattern}")


def validate_no_legacy_runtime_dependencies(root: Path, errors: list[str]) -> None:
    for path in iter_runtime_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as exc:
            errors.append(f"could not scan {path.relative_to(root)} for legacy dependencies: {exc}")
            continue
        for lineno, line in enumerate(lines, start=1):
            legacy = legacy_dependency_name(path, line)
            if legacy:
                errors.append(
                    f"legacy runtime dependency {legacy!r} found in {path.relative_to(root)}:{lineno}"
                )


def validate_no_wildcard_cors(root: Path, errors: list[str]) -> None:
    for path in iter_runtime_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as exc:
            errors.append(f"could not scan {path.relative_to(root)} for wildcard CORS: {exc}")
            continue
        for lineno, line in enumerate(lines, start=1):
            lowered = line.lower()
            has_cors_origin = "access-control-allow-origin" in lowered
            has_wildcard = '"*"' in line or "'*'" in line
            if has_cors_origin and has_wildcard:
                errors.append(f"wildcard CORS origin found in {path.relative_to(root)}:{lineno}")


def iter_runtime_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for relative in RUNTIME_SCAN_DIRS:
        directory = root / relative
        if directory.exists():
            paths.extend(
                path
                for path in directory.rglob("*")
                if path.is_file() and path.suffix.lower() in {".css", ".html", ".js", ".py"}
            )
    for relative in RUNTIME_SCAN_FILES:
        path = root / relative
        if path.exists():
            paths.append(path)
    return sorted(set(paths))


def legacy_dependency_name(path: Path, line: str) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".py":
        match = LEGACY_PYTHON_IMPORT.search(line)
        return match.group(1).lower() if match else None
    if suffix == ".js":
        match = LEGACY_JS_IMPORT.search(line)
        if not match:
            return None
        package = match.group(1).split("/", 1)[0].lower()
        return package if package in {"flask", "sqlalchemy", "alembic"} or package.startswith("azure") else None
    if suffix in {".json", ".toml"}:
        match = LEGACY_CONFIG_DEPENDENCY.search(line)
        return match.group(1).lower() if match else None
    return None


def namespace_by_binding(config: dict[str, Any], binding: str) -> dict[str, Any] | None:
    for item in config.get("kv_namespaces", []):
        if item.get("binding") == binding:
            return item
    return None


def require_path(root: Path, relative: str, errors: list[str]) -> None:
    if not (root / relative).exists():
        errors.append(f"required path missing: {relative}")


def read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"could not read {path.name}: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{path.name} must contain a JSON object")
        return None
    return payload


def read_toml(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        with path.open("rb") as handle:
            payload = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"could not read {path.name}: {exc}")
        return None
    return payload


def looks_placeholder(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("replace-with") or "placeholder" in lowered or lowered.startswith("your-")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate local Cloudflare deployment readiness for Rental Desk.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--allow-placeholders", action="store_true", help="Allow placeholder Cloudflare ids and Access vars")
    parser.add_argument("--include-frontdoor", action="store_true", help="Also validate the Cloudflare Access front door")
    args = parser.parse_args(argv)

    errors, warnings = validate_project(
        args.root,
        allow_placeholders=args.allow_placeholders,
        include_frontdoor=args.include_frontdoor,
    )
    for warning in warnings:
        print(f"WARN {warning}")
    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1
    print("OK deploy preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
