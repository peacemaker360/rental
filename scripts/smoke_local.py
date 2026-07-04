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
ROOT = SCRIPT_DIR.parent
WORKER_DIR = ROOT / "worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from local_dev_server import JsonFileRepository, configured_handler
from worker.api_core import signed_context_headers


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


def expect_raw_http_error(
    base_url: str,
    path: str,
    method: str,
    body: bytes,
    status: int,
    text: str,
    headers: dict[str, str] | None = None,
) -> None:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        headers={"content-type": "application/json", **(headers or {})},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=5):
            pass
    except urllib.error.HTTPError as exc:
        response = exc.read().decode("utf-8")
        if exc.code != status or text not in response:
            raise AssertionError(f"Expected {status} containing {text!r}, got {exc.code}: {response}") from exc
        return
    raise AssertionError(f"Expected HTTP {status} for {path}")


def run_smoke(verbose: bool = False) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        server = ThreadingHTTPServer(("127.0.0.1", 0), configured_handler(JsonFileRepository(Path(temp_dir))))
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
            assert 'id="hitobitoImportButton"' in html
            assert 'id="instrumentFile"' in html
            assert 'data-view="service_records"' in html

            status, app_js = request_text(base_url, "/app.js")
            assert status == 200 and "const translations" in app_js
            assert '"views.service_records": "Service"' in app_js
            assert '"labels.updated_at": "Aktualisiert {date}"' in app_js
            assert '"sections.service_journey"' in app_js
            assert '"sections.association_details"' in app_js
            assert '"sections.history_details"' in app_js
            assert '"fields.contact_hint": "Roster note"' in app_js
            assert '"table.contact": "Roster note"' in app_js
            assert '"empty.no_attention"' in app_js
            assert '"fields.next_service_date"' in app_js
            assert "blockedImportPiiFields" in app_js
            assert "assertLowPiiImport(payload)" in app_js
            assert '"/members/import/hitobito"' in app_js
            assert '"/instruments/import"' in app_js
            assert "data-open-association" in app_js
            assert 'data-open="history"' in app_js
            assert "data-close-detail" in app_js
            assert "data-sort-direction" in app_js
            assert 'data-open="service_records"' in app_js
            assert "function renderServiceDetail(item)" in app_js
            assert 'data-delete="service_records"' in app_js
            assert "data-open-dashboard-instrument" in app_js

            expect_http_error(base_url, "/api", "GET", {}, 404, "route not found")
            expect_http_error(base_url, "/api/", "GET", {}, 404, "route not found")

            status, context = request_json(base_url, "/api/context")
            assert status == 200 and context["tenant_id"] == "demo-association"
            assert context["capabilities"]["admin"] is True
            assert context["meta"]["revision"] == 0

            status, health = request_json(base_url, "/api/health")
            assert status == 200 and health["ok"] is True

            status, bootstrap = request_json(base_url, "/api/smoke-tenant/bootstrap", "POST", {})
            assert status == 201
            assert bootstrap["meta"]["revision"] == 1

            status, associations = request_json(base_url, "/api/admin/associations")
            assert status == 200
            assert any(item["tenant_id"] == "smoke-tenant" for item in associations["data"])

            status, association = request_json(
                base_url,
                "/api/admin/associations/smoke-tenant",
                "PUT",
                {"display_name": "Smoke Association", "status": "paused", "hitobito_group_ref": "hitobito-42"},
            )
            assert status == 200
            assert association["data"]["display_name"] == "Smoke Association"
            assert association["data"]["status"] == "paused"

            status, user = request_json(
                base_url,
                "/api/admin/users",
                "POST",
                {
                    "email": "smoke-user@example.test",
                    "display_name": "Smoke User",
                    "global_role": "none",
                    "access_profile": "basic",
                    "tenant_roles": [{"tenant_id": "smoke-tenant", "role": "reader"}],
                    "member_links": [{"tenant_id": "smoke-tenant", "member_id": "mem_smoke"}],
                },
            )
            assert status == 201
            assert user["data"]["email"] == "smoke-user@example.test"
            assert user["data"]["access_profile"] == "basic"
            user_id = user["data"]["id"]

            status, user_update = request_json(
                base_url,
                f"/api/admin/users/{user_id}",
                "PUT",
                {"global_role": "reader", "tenant_roles": [], "member_links": []},
            )
            assert status == 200
            assert user_update["data"]["global_role"] == "reader"

            status, users = request_json(base_url, "/api/admin/users")
            assert status == 200
            assert any(item["id"] == user_id and item["email"] == "smoke-user@example.test" for item in users["data"])

            status, access_export = request_json(base_url, "/api/admin/users/export/tenant-access")
            assert status == 200
            assert access_export["schema"] == "tenant-access-kv-bulk"
            assert access_export["summary"]["users"] == 1
            assert access_export["data"][0]["key"] == "user:smoke-user@example.test"
            assert '"access_profile":"basic"' in access_export["data"][0]["value"]

            status, deleted_user = request_json(base_url, f"/api/admin/users/{user_id}", "DELETE", {})
            assert status == 200
            assert deleted_user["deleted"] == user_id
            assert deleted_user["data"]["email"] == "smoke-user@example.test"

            status, users = request_json(base_url, "/api/admin/users")
            assert status == 200
            assert not any(item["id"] == user_id for item in users["data"])

            status, exported = request_json(base_url, "/api/smoke-tenant/export")
            assert status == 200 and exported["summary"]["instruments"] == 2
            assert exported["meta"]["revision"] == 1
            assert len(exported["records"]["service_records"]) == 2
            assert any(record.get("next_service_date") for record in exported["records"]["service_records"])
            assert any(record.get("service_record_id") for record in exported["records"]["history"])
            assert any(record.get("service_condition") == "needs_service" for record in exported["records"]["history"])

            status, instrument_export = request_json(base_url, "/api/smoke-tenant/instruments/export")
            assert status == 200
            assert instrument_export["schema"] == "association-rental-instruments"
            assert instrument_export["summary"]["instruments"] == 2
            assert "members" not in instrument_export["records"]

            status, imported = request_json(base_url, "/api/smoke-import/import", "PUT", exported)
            assert status == 200 and imported["summary"]["members"] == 2
            assert imported["meta"]["revision"] == 1
            assert imported["summary"]["service_attention"] == 1

            status, hitobito = request_json(
                base_url,
                "/api/smoke-import/members/import/hitobito",
                "PUT",
                {
                    "people": [{
                        "id": "hb-100",
                        "first_name": "Smoke",
                        "last_name": "Member",
                        "email": "smoke-member@example.test",
                        "groups": ["Blasorchester"],
                    }]
                },
            )
            assert status == 200
            assert hitobito["report"]["created"] == 1
            assert hitobito["report"]["updated"] == 0
            assert hitobito["summary"]["members"] == 3

            status, instrument_import = request_json(
                base_url,
                "/api/smoke-import/instruments/import",
                "PUT",
                {
                    "instruments": [
                        {"name": "Smoke Piano Updated", "brand": "Yamaha", "type": "Keyboard", "serial": "CP73-001"},
                        {"name": "Smoke Snare", "brand": "Pearl", "type": "Drum", "serial": "SN-1"},
                    ]
                },
            )
            assert status == 200
            assert instrument_import["report"]["created"] == 1
            assert instrument_import["report"]["updated"] == 1
            assert instrument_import["summary"]["instruments"] == 3

            expect_http_error(
                base_url,
                "/api/smoke-import/instruments/import",
                "PUT",
                {"instruments": [{"name": "Private Donation Clarinet", "serial": "CL-PII", "email": "donor@example.test"}]},
                400,
                "blocked PII fields",
            )

            expect_http_error(
                base_url,
                "/api/smoke-import/members",
                "POST",
                {"display_name": "Stale Member"},
                409,
                "tenant revision conflict",
                {"x-rental-expected-revision": "0"},
            )

            expect_http_error(
                base_url,
                "/api/smoke-import/members",
                "POST",
                {"display_name": "Private Member", "contact_hint": "+41 44 000 00 00"},
                400,
                "contact_hint must not contain phone numbers",
            )

            expect_raw_http_error(
                base_url,
                "/api/smoke-import/members",
                "POST",
                b'{"display_name":',
                400,
                "invalid JSON body",
            )

            status, rentals = request_json(base_url, "/api/smoke-import/rentals")
            assert status == 200 and rentals["data"]
            rental_id = rentals["data"][0]["id"]

            status, services = request_json(base_url, "/api/smoke-import/service_records")
            assert status == 200 and services["data"]
            assert services["data"][0]["instrument_name"]
            assert "instrument_serial" in services["data"][0]
            assert services["data"][0]["service_due_status"] in ("ok", "due_soon", "overdue")
            service_id = services["data"][0]["id"]

            status, service_update = request_json(
                base_url,
                f"/api/smoke-import/service_records/{service_id}",
                "PUT",
                {"condition": "in_service", "note": "Smoke check service update"},
            )
            assert status == 200
            assert service_update["data"]["condition"] == "in_service"

            status, _ = request_json(
                base_url,
                f"/api/smoke-import/rentals/{rental_id}/return",
                "POST",
                {"return_date": "2026-01-01"},
            )
            assert status == 200

            status, _ = request_json(base_url, f"/api/smoke-import/rentals/{rental_id}", "DELETE", {})
            assert status == 200

            status, service_delete = request_json(base_url, f"/api/smoke-import/service_records/{service_id}", "DELETE", {})
            assert status == 200 and service_delete["deleted"] == service_id
            assert service_delete["data"]["id"] == service_id
            assert service_delete["data"]["condition"] == "in_service"

            status, history = request_json(base_url, "/api/smoke-import/history")
            assert status == 200
            assert any(record.get("service_record_id") == service_id and record.get("action") == "deleted" for record in history["data"])

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


def signed_headers(
    tenant_id: str,
    role: str = "admin",
    actor_id: str = "smoke-signed-user",
    extra: dict | None = None,
) -> dict[str, str]:
    return signed_context_headers({
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "role": role,
        **(extra or {}),
    }, "dev-smoke-secret")


def run_signed_smoke(verbose: bool = False) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        handler = configured_handler(
            JsonFileRepository(Path(temp_dir)),
            auth_mode="signed",
            context_secret="dev-smoke-secret",
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            if verbose:
                print(f"Signed smoke server: {base_url}")

            status, health = request_json(base_url, "/api/health")
            assert status == 200 and health["ok"] is True

            expect_http_error(base_url, "/api/context", "GET", {}, 403, "missing signed tenant context")

            headers = signed_headers("signed-tenant")
            status, context = request_json(base_url, "/api/context", headers=headers)
            assert status == 200
            assert context["tenant_id"] == "signed-tenant"
            assert context["tenant_locked"] is True
            assert context["mode"] == "signed"
            assert context["capabilities"]["admin"] is True
            assert context["capabilities"]["platform_admin"] is False

            status, bootstrap = request_json(base_url, "/api/signed-tenant/bootstrap", "POST", {}, headers)
            assert status == 201
            assert bootstrap["meta"]["revision"] == 1

            status, summary = request_json(base_url, "/api/signed-tenant/summary", headers=headers)
            assert status == 200
            assert summary["instruments"] == 2
            assert summary["meta"]["revision"] == 1

            status, members = request_json(base_url, "/api/signed-tenant/members", headers=headers)
            assert status == 200 and members["data"]
            member_id = members["data"][0]["id"]

            basic_headers = signed_headers(
                "signed-tenant",
                role="viewer",
                actor_id="basic-smoke-user",
                extra={
                    "access_profile": "basic",
                    "member_id": member_id,
                    "user_email": "basic-smoke@example.test",
                },
            )
            status, basic_context = request_json(base_url, "/api/context", headers=basic_headers)
            assert status == 200
            assert basic_context["capabilities"]["write"] is False
            assert basic_context["capabilities"]["access_profile"] == "basic"

            status, basic_members = request_json(base_url, "/api/signed-tenant/members", headers=basic_headers)
            assert status == 200
            assert [item["id"] for item in basic_members["data"]] == [member_id]

            status, basic_rentals = request_json(base_url, "/api/signed-tenant/rentals", headers=basic_headers)
            assert status == 200
            assert all(item["member_id"] == member_id for item in basic_rentals["data"])

            expect_http_error(
                base_url,
                "/api/signed-tenant/members",
                "POST",
                {"display_name": "Blocked Basic User"},
                403,
                "operator role required",
                basic_headers,
            )

            expect_http_error(
                base_url,
                "/api/other-tenant/summary",
                "GET",
                {},
                403,
                "tenant context does not match route",
                headers,
            )

            platform_headers = signed_headers("platform-admin")
            status, associations = request_json(base_url, "/api/admin/associations", headers=platform_headers)
            assert status == 200
            assert any(item["tenant_id"] == "signed-tenant" for item in associations["data"])

            if verbose:
                print("Signed local smoke passed")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local API/static smoke test without Wrangler.")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--signed", action="store_true", help="Also run the signed-context local smoke path.")
    args = parser.parse_args()
    run_smoke(verbose=args.verbose)
    if args.signed:
        run_signed_smoke(verbose=args.verbose)


if __name__ == "__main__":
    main()
