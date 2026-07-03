from __future__ import annotations

import json
from urllib.parse import urlparse

from workers import Response, WorkerEntrypoint

# from .api_core import context_from_headers, handle_api_request, is_api_request_path, parse_api_path
from api_core import (
    context_from_headers,
    handle_api_request,
    is_api_request_path,
    parse_api_path,
)
from storage import KVRepository


JSON_HEADERS = {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "pragma": "no-cache",
    "referrer-policy": "no-referrer",
    "x-content-type-options": "nosniff",
    "access-control-allow-methods": "GET,POST,PUT,DELETE,OPTIONS",
    "access-control-allow-headers": "content-type,authorization,x-rental-context,x-rental-context-signature,x-rental-expected-revision,x-rental-tenant-id,x-rental-actor-id,x-rental-role,x-rental-access-profile,x-rental-member-id,x-rental-user-email",
}


def json_response(data, status=200):
    return Response(json.dumps(data, default=str), status=status, headers=JSON_HEADERS)


class InvalidJsonBody(ValueError):
    pass


async def request_json(request):
    try:
        raw = await request.text()
    except Exception as exc:
        raise InvalidJsonBody("invalid JSON body") from exc
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidJsonBody("invalid JSON body") from exc


def worker_auth_mode(env, hostname: str) -> str:
    configured = getattr(env, "RENTAL_AUTH_MODE", "auto")
    if configured != "auto":
        return configured
    if hostname in ("127.0.0.1", "localhost") or hostname.endswith(".localhost"):
        return "local"
    return "signed"


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if request.method == "OPTIONS":
            return Response("", status=204, headers=JSON_HEADERS)

        parsed = urlparse(request.url)
        parts = parse_api_path(parsed.path)
        if not parts:
            if is_api_request_path(parsed.path):
                return json_response({"error": "route not found"}, 404)
            return await self.env.ASSETS.fetch(request)

        auth_mode = worker_auth_mode(self.env, parsed.hostname or "")
        context = None
        headers = {}
        if parts != ["health"]:
            headers = {key: value for key, value in request.headers.items()}
            path_tenant_id = None if parts == ["context"] or parts[0] == "admin" else parts[0]
            context, error = context_from_headers(
                path_tenant_id,
                headers,
                auth_mode,
                getattr(self.env, "RENTAL_CONTEXT_SECRET", None),
            )
            if error:
                return json_response({"error": error}, 403)

        repo = KVRepository(self.env.RENTAL_KV)
        try:
            payload = await request_json(request) if request.method in ("POST", "PUT") else {}
        except InvalidJsonBody as exc:
            return json_response({"error": str(exc)}, 400)
        status, body = await handle_api_request(request.method, parsed.path, parsed.query, payload, repo, context, headers)
        return json_response(body, status)
