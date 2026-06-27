from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from worker.api_core import context_from_headers, handle_api_request, parse_api_path, validate_tenant_id
from worker.domain import ENTITY_TYPES, empty_records, utc_now
from worker.storage import empty_metadata


PUBLIC_DIR = ROOT / "public"
DATA_DIR = ROOT / ".data" / "local-kv"
JSON_HEADERS = {
    "content-type": "application/json; charset=utf-8",
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,PUT,DELETE,OPTIONS",
    "access-control-allow-headers": "content-type,authorization,x-rental-context,x-rental-context-signature,x-rental-expected-revision,x-rental-tenant-id,x-rental-actor-id,x-rental-role",
}


class JsonFileRepository:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def tenant_file(self, tenant_id: str) -> Path:
        error = validate_tenant_id(tenant_id)
        if error:
            raise ValueError(error)
        return self.data_dir / f"{tenant_id}.json"

    async def load_tenant(self, tenant_id: str) -> dict[str, list[dict[str, Any]]]:
        path = self.tenant_file(tenant_id)
        if not path.exists():
            return empty_records()
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        data = data.get("records", data)
        return {entity: data.get(entity, []) for entity in ENTITY_TYPES}

    async def load_metadata(self, tenant_id: str) -> dict[str, Any]:
        path = self.tenant_file(tenant_id)
        if not path.exists():
            return empty_metadata(tenant_id)
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        metadata = data.get("meta", empty_metadata(tenant_id)) if isinstance(data, dict) else {}
        return {**empty_metadata(tenant_id), **metadata, "tenant_id": tenant_id}

    async def save_tenant(self, tenant_id: str, records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        path = self.tenant_file(tenant_id)
        previous_metadata = await self.load_metadata(tenant_id)
        metadata = {
            "tenant_id": tenant_id,
            "revision": int(previous_metadata.get("revision", 0)) + 1,
            "updated_at": utc_now(),
        }
        temp_path = path.with_suffix(".json.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump({"meta": metadata, "records": records}, handle, indent=2, sort_keys=True)
        temp_path.replace(path)
        return metadata


class RentalDevHandler(BaseHTTPRequestHandler):
    repo = JsonFileRepository(DATA_DIR)

    def do_OPTIONS(self) -> None:
        self.send_json({}, HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:
        self.dispatch()

    def do_POST(self) -> None:
        self.dispatch()

    def do_PUT(self) -> None:
        self.dispatch()

    def do_DELETE(self) -> None:
        self.dispatch()

    def dispatch(self) -> None:
        parsed = urlparse(self.path)
        if parse_api_path(parsed.path):
            self.dispatch_api(parsed)
            return
        self.serve_static(parsed.path)

    def dispatch_api(self, parsed) -> None:
        parts = parse_api_path(parsed.path)
        payload = self.read_json_body() if self.command in ("POST", "PUT") else {}
        context = None
        headers = {}
        if parts != ["health"]:
            headers = {key: value for key, value in self.headers.items()}
            path_tenant_id = None if parts == ["context"] else parts[0]
            context, error = context_from_headers(path_tenant_id, headers, "local")
            if error:
                self.send_json({"error": error}, HTTPStatus.FORBIDDEN)
                return
        status, body = asyncio.run(
            handle_api_request(self.command, parsed.path, parsed.query, payload, self.repo, context, headers)
        )
        self.send_json(body, status)

    def serve_static(self, pathname: str) -> None:
        relative = pathname.lstrip("/") or "index.html"
        candidate = (PUBLIC_DIR / relative).resolve()
        if not str(candidate).startswith(str(PUBLIC_DIR.resolve())):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not candidate.exists() or not candidate.is_file():
            candidate = PUBLIC_DIR / "index.html"

        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        payload = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def send_json(self, body: Any, status: int | HTTPStatus = HTTPStatus.OK) -> None:
        payload = b"" if status == HTTPStatus.NO_CONTENT else json.dumps(body, default=str).encode("utf-8")
        self.send_response(int(status))
        for key, value in JSON_HEADERS.items():
            self.send_header(key, value)
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:
        print("%s - %s" % (self.log_date_time_string(), format % args))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the rental app against local JSON storage.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8787, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), RentalDevHandler)
    print(f"Rental Desk local dev server: http://{args.host}:{args.port}")
    print(f"Local JSON data: {DATA_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local dev server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
