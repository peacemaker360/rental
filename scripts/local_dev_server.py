from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from worker.api_core import context_from_headers, handle_api_request, is_api_request_path, parse_api_path, validate_tenant_id
from worker.domain import ENTITY_TYPES, empty_records, utc_now
from worker.storage import empty_metadata


PUBLIC_DIR = ROOT / "public"
DATA_DIR = ROOT / ".data" / "local-kv"
JSON_HEADERS = {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "pragma": "no-cache",
    "referrer-policy": "no-referrer",
    "x-content-type-options": "nosniff",
    "access-control-allow-methods": "GET,POST,PUT,DELETE,OPTIONS",
    "access-control-allow-headers": "content-type,authorization,x-rental-context,x-rental-context-signature,x-rental-expected-revision,x-rental-tenant-id,x-rental-actor-id,x-rental-role,x-rental-access-profile,x-rental-member-id,x-rental-user-email",
}


class InvalidJsonBody(ValueError):
    pass


def parse_json_body(raw: bytes) -> Any:
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidJsonBody("invalid JSON body") from exc


class JsonFileRepository:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def tenant_file(self, tenant_id: str) -> Path:
        error = validate_tenant_id(tenant_id)
        if error:
            raise ValueError(error)
        return self.data_dir / f"{tenant_id}.json"

    def associations_file(self) -> Path:
        return self.data_dir / "_associations.json"

    def users_file(self) -> Path:
        return self.data_dir / "_users.json"

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

    async def tenant_exists(self, tenant_id: str) -> bool:
        return self.tenant_file(tenant_id).exists()

    async def list_associations(self) -> list[dict[str, Any]]:
        associations = []
        path = self.associations_file()
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            associations.extend(data.get("associations", []))
        known = {item.get("tenant_id") for item in associations}
        for tenant_file in sorted(self.data_dir.glob("*.json")):
            if tenant_file.name.startswith("_"):
                continue
            tenant_id = tenant_file.stem
            if tenant_id not in known:
                associations.append({
                    "tenant_id": tenant_id,
                    "display_name": tenant_id.replace("-", " ").replace("_", " ").title(),
                    "status": "active",
                    "locale": "de-CH",
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                })
        return sorted(associations, key=lambda item: item.get("display_name", item.get("tenant_id", "")))

    async def load_association(self, tenant_id: str) -> dict[str, Any] | None:
        for association in await self.list_associations():
            if association.get("tenant_id") == tenant_id:
                return association
        return None

    async def save_association(self, tenant_id: str, association: dict[str, Any]) -> dict[str, Any]:
        path = self.associations_file()
        associations = [item for item in await self.list_associations() if item.get("tenant_id") != tenant_id]
        associations.append(association)
        associations.sort(key=lambda item: item.get("display_name", item.get("tenant_id", "")))
        temp_path = path.with_suffix(".json.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump({"associations": associations}, handle, indent=2, sort_keys=True)
        temp_path.replace(path)
        return association

    async def list_users(self) -> list[dict[str, Any]]:
        path = self.users_file()
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        users = data.get("users", []) if isinstance(data, dict) else []
        return sorted(users, key=lambda item: item.get("email", item.get("id", "")))

    async def load_user(self, user_id: str) -> dict[str, Any] | None:
        for user in await self.list_users():
            if user.get("id") == user_id:
                return user
        return None

    async def save_user(self, user_id: str, user: dict[str, Any]) -> dict[str, Any]:
        path = self.users_file()
        users = [item for item in await self.list_users() if item.get("id") != user_id]
        users.append(user)
        users.sort(key=lambda item: item.get("email", item.get("id", "")))
        temp_path = path.with_suffix(".json.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump({"users": users}, handle, indent=2, sort_keys=True)
        temp_path.replace(path)
        return user

    async def delete_user(self, user_id: str) -> dict[str, Any] | None:
        path = self.users_file()
        existing = await self.load_user(user_id)
        if existing is None:
            return None
        users = [item for item in await self.list_users() if item.get("id") != user_id]
        temp_path = path.with_suffix(".json.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump({"users": users}, handle, indent=2, sort_keys=True)
        temp_path.replace(path)
        return existing


class RentalDevHandler(BaseHTTPRequestHandler):
    repo = JsonFileRepository(DATA_DIR)
    auth_mode = "local"
    context_secret = None

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
        if is_api_request_path(parsed.path):
            self.send_json({"error": "route not found"}, HTTPStatus.NOT_FOUND)
            return
        self.serve_static(parsed.path)

    def dispatch_api(self, parsed) -> None:
        parts = parse_api_path(parsed.path)
        try:
            payload = self.read_json_body() if self.command in ("POST", "PUT") else {}
        except InvalidJsonBody as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        context = None
        headers = {}
        if parts != ["health"]:
            headers = {key: value for key, value in self.headers.items()}
            path_tenant_id = None if parts == ["context"] or parts[0] == "admin" else parts[0]
            context, error = context_from_headers(path_tenant_id, headers, self.auth_mode, self.context_secret)
            if error:
                self.send_json({"error": error}, HTTPStatus.FORBIDDEN)
                return
        status, body = asyncio.run(
            handle_api_request(self.command, parsed.path, parsed.query, payload, self.repo, context, headers)
        )
        self.send_json(body, status)

    def serve_static(self, pathname: str) -> None:
        candidate = static_path_for(pathname)
        if candidate is None:
            self.send_error(HTTPStatus.FORBIDDEN)
            return

        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        payload = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def read_json_body(self) -> Any:
        length = int(self.headers.get("content-length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return parse_json_body(raw)

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


def configured_handler(
    repo: JsonFileRepository,
    *,
    auth_mode: str = "local",
    context_secret: str | None = None,
) -> type[RentalDevHandler]:
    class ConfiguredRentalDevHandler(RentalDevHandler):
        pass

    ConfiguredRentalDevHandler.repo = repo
    ConfiguredRentalDevHandler.auth_mode = auth_mode
    ConfiguredRentalDevHandler.context_secret = context_secret
    return ConfiguredRentalDevHandler


def static_path_for(pathname: str, public_dir: Path = PUBLIC_DIR) -> Path | None:
    public_root = public_dir.resolve()
    relative = pathname.lstrip("/") or "index.html"
    candidate = (public_root / relative).resolve()
    if not candidate.is_relative_to(public_root):
        return None
    if not candidate.exists() or not candidate.is_file():
        return public_root / "index.html"
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the rental app against local JSON storage.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8787, type=int)
    parser.add_argument(
        "--auth-mode",
        choices=("local", "header", "signed"),
        default="local",
        help="Tenant context mode for local API debugging. Default local grants admin access.",
    )
    parser.add_argument(
        "--context-secret",
        default=os.environ.get("RENTAL_CONTEXT_SECRET"),
        help="Signing secret required when --auth-mode signed is used.",
    )
    args = parser.parse_args()
    if args.auth_mode == "signed" and not args.context_secret:
        parser.error("--context-secret or RENTAL_CONTEXT_SECRET is required with --auth-mode signed")

    handler = configured_handler(JsonFileRepository(DATA_DIR), auth_mode=args.auth_mode, context_secret=args.context_secret)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Rental Desk local dev server: http://{args.host}:{args.port}")
    print(f"Local JSON data: {DATA_DIR}")
    print(f"Auth mode: {args.auth_mode}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local dev server")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
