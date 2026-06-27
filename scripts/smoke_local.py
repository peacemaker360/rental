from __future__ import annotations

import argparse
import json
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from local_dev_server import JsonFileRepository, RentalDevHandler


class SmokeHandler(RentalDevHandler):
    pass


def request_json(
    base_url: str,
    path: str,
    method: str = "GET",
    body: dict | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=payload,
        headers={"content-type": "application/json", **(headers or {})},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        raw = response.read()
        return response.status, json.loads(raw or b"{}")


def request_text(base_url: str, path: str) -> tuple[int, str]:
    with urllib.request.urlopen(f"{base_url}{path}", timeout=5) as response:
        return response.status, response.read().decode("utf-8")


def expect_http_error(
    base_url: str,
    path: str,
    method: str,
    body: dict,
    status: int,
    text: str,
    headers: dict[str, str] | None = None,
) -> None:
    try:
        request_json(base_url, path, method, body, headers)
    except urllib.error.HTTPError as exc:
        response = exc.read().decode("utf-8")
        if exc.code != status or text not in response:
            raise AssertionError(f"Expected {status} containing {text!r}, got {exc.code}: {response}") from exc
        return
    raise AssertionError(f"Expected HTTP {status} for {path}")


def run_smoke(verbose: bool = False) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        SmokeHandler.repo = JsonFileRepository(Path(temp_dir))
        server = ThreadingHTTPServer(("127.0.0.1", 0), SmokeHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            if verbose:
                print(f"Smoke server: {base_url}")

            status, html = request_text(base_url, "/")
            assert status == 200 and "<!doctype html>" in html
            assert 'data-lang="de"' in html
            assert 'id="tenantRevision"' in html

            status, app_js = request_text(base_url, "/app.js")
            assert status == 200 and "const translations" in app_js
            assert '"labels.updated_at": "Aktualisiert {date}"' in app_js

            status, context = request_json(base_url, "/api/context")
            assert status == 200 and context["tenant_id"] == "demo-association"
            assert context["capabilities"]["admin"] is True
            assert context["meta"]["revision"] == 0

            status, health = request_json(base_url, "/api/health")
            assert status == 200 and health["ok"] is True

            status, bootstrap = request_json(base_url, "/api/smoke-tenant/bootstrap", "POST", {})
            assert status == 201
            assert bootstrap["meta"]["revision"] == 1

            status, exported = request_json(base_url, "/api/smoke-tenant/export")
            assert status == 200 and exported["summary"]["instruments"] == 2
            assert exported["meta"]["revision"] == 1

            status, imported = request_json(base_url, "/api/smoke-import/import", "PUT", exported)
            assert status == 200 and imported["summary"]["members"] == 2
            assert imported["meta"]["revision"] == 1

            expect_http_error(
                base_url,
                "/api/smoke-import/members",
                "POST",
                {"display_name": "Stale Member"},
                409,
                "tenant revision conflict",
                {"x-rental-expected-revision": "0"},
            )

            status, rentals = request_json(base_url, "/api/smoke-import/rentals")
            assert status == 200 and rentals["data"]
            rental_id = rentals["data"][0]["id"]

            status, _ = request_json(
                base_url,
                f"/api/smoke-import/rentals/{rental_id}/return",
                "POST",
                {"return_date": "2026-01-01"},
            )
            assert status == 200

            status, _ = request_json(base_url, f"/api/smoke-import/rentals/{rental_id}", "DELETE", {})
            assert status == 200

            expect_http_error(
                base_url,
                "/api/smoke-pii/import",
                "PUT",
                {"records": {"members": [{"display_name": "Private Member", "email": "private@example.test"}]}},
                400,
                "blocked PII fields",
            )

            expect_http_error(base_url, "/api/Bad%20Tenant/summary", "GET", {}, 403, "tenant id must use")

            if verbose:
                print("Local smoke passed")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local API/static smoke test without Wrangler.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    run_smoke(verbose=args.verbose)


if __name__ == "__main__":
    main()
