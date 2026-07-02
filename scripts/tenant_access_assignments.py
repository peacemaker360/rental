from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.api_core import ALLOWED_ROLES, validate_actor_id, validate_tenant_id


PII_FIELD_NAMES = {
    "address",
    "display_name",
    "email",
    "family_name",
    "first_name",
    "full_name",
    "given_name",
    "last_name",
    "mail",
    "mobile",
    "name",
    "phone",
    "telephone",
}


def load_source(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("assignments"), list):
        rows = payload["assignments"]
    else:
        raise ValueError("assignment source must be a JSON array or an object with assignments")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("tenant access assignments must be JSON objects")
    return rows


def normalize_assignment(row: dict[str, Any]) -> dict[str, Any]:
    pii_keys = sorted(key for key, value in row.items() if key.lower() in PII_FIELD_NAMES and value not in (None, ""))
    if pii_keys:
        raise ValueError(f"assignment contains PII-like fields: {', '.join(pii_keys)}")

    principal = clean_text(row.get("principal") or row.get("access_sub") or row.get("sub"))
    if not principal:
        raise ValueError("principal, access_sub, or sub is required")
    principal_error = validate_actor_id(principal)
    if principal_error:
        raise ValueError(principal_error.replace("actor_id", "principal"))

    tenant_id = clean_text(row.get("tenant_id") or row.get("tenant"))
    tenant_error = validate_tenant_id(tenant_id)
    if tenant_error:
        raise ValueError(tenant_error)

    role = clean_text(row.get("role"), "viewer")
    if role not in ALLOWED_ROLES:
        raise ValueError(f"role must be one of {', '.join(sorted(ALLOWED_ROLES))}")

    assignment: dict[str, Any] = {
        "key": f"principal:{principal}",
        "value": {
            "tenant_id": tenant_id,
            "role": role,
        },
    }
    actor_id = clean_text(row.get("actor_id"))
    if actor_id:
        actor_error = validate_actor_id(actor_id)
        if actor_error:
            raise ValueError(actor_error)
        assignment["value"]["actor_id"] = actor_id
    return assignment


def render_kv_bulk(assignments: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "key": assignment["key"],
            "value": json.dumps(assignment["value"], separators=(",", ":"), sort_keys=True),
        }
        for assignment in assignments
    ]


def render_commands(assignments: list[dict[str, Any]], binding: str, config: str, preview: bool) -> list[str]:
    commands = []
    preview_flag = " --preview" if preview else ""
    for item in render_kv_bulk(assignments):
        commands.append(
            "npx wrangler kv key put "
            f"{shlex.quote(item['key'])} {shlex.quote(item['value'])} "
            f"--binding {shlex.quote(binding)} --config {shlex.quote(config)}{preview_flag}"
        )
    return commands


def clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def write_text(path: Path | None, text: str) -> None:
    if path is None:
        print(text)
        return
    path.write_text(text + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate low-PII Cloudflare Access tenant assignments and render TENANT_ACCESS_KV seed data."
    )
    parser.add_argument("source", type=Path, help="JSON array or object with assignments")
    parser.add_argument("--format", choices=("kv-bulk", "commands", "summary"), default="kv-bulk")
    parser.add_argument("--output", type=Path, help="Write rendered output to this file instead of stdout")
    parser.add_argument("--binding", default="TENANT_ACCESS_KV")
    parser.add_argument("--config", default="wrangler.frontdoor.toml")
    parser.add_argument("--preview", action="store_true", help="Add --preview to rendered wrangler commands")
    args = parser.parse_args(argv)

    try:
        assignments = [normalize_assignment(row) for row in load_source(args.source)]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"tenant access assignment error: {exc}", file=sys.stderr)
        return 2

    if args.format == "summary":
        tenants = sorted({assignment["value"]["tenant_id"] for assignment in assignments})
        roles = {role: 0 for role in sorted(ALLOWED_ROLES)}
        for assignment in assignments:
            roles[assignment["value"]["role"]] += 1
        output = json.dumps({
            "assignments": len(assignments),
            "tenants": tenants,
            "roles": roles,
        }, indent=2, sort_keys=True)
    elif args.format == "commands":
        output = "\n".join(render_commands(assignments, args.binding, args.config, args.preview))
    else:
        output = json.dumps(render_kv_bulk(assignments), indent=2, sort_keys=True)

    write_text(args.output, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
