"""Validate legacy access exports offline, or explicitly reconcile them to Clerk."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "worker") not in sys.path:
    sys.path.insert(0, str(ROOT / "worker"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.api_core import normalize_association, normalize_user_access
from worker.clerk_directory import ClerkDirectory
from domain import DomainError


def rows(payload):
    result = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
        raise ValueError("Expected a JSON array or an object containing a data array")
    return result


def migration_plan(user_payload, association_payload):
    associations = [normalize_association(item) for item in rows(association_payload)]
    mappings = ClerkDirectory.association_mappings(associations)
    users = []
    seen = set()
    for item in rows(user_payload):
        source = item
        if "key" in item or "value" in item:
            source = json.loads(item["value"]) if isinstance(item.get("value"), str) else item.get("value")
            if not isinstance(source, dict) or item.get("key") != f"user:{source.get('email', '').strip().lower()}":
                raise ValueError("Only email-based user exports are supported; assignment key must match the email")
        user = normalize_user_access(source)
        if user["id"] in seen:
            raise ValueError("Duplicate user in access export")
        seen.add(user["id"])
        # Older basic profiles could grant access through a member link alone.
        assigned = {item["tenant_id"] for item in user["tenant_roles"]}
        if user["access_profile"] == "basic":
            for link in user["member_links"]:
                if link["tenant_id"] not in assigned:
                    user["tenant_roles"].append({"tenant_id": link["tenant_id"], "role": "reader"})
                    assigned.add(link["tenant_id"])
        for tenant in assigned:
            if tenant not in mappings:
                raise ValueError(f"Association {tenant} has no Clerk organization mapping")
        statuses = source.get("tenant_statuses", {})
        if not isinstance(statuses, dict) or any(tenant not in assigned or status not in ("active", "disabled") for tenant, status in statuses.items()):
            raise ValueError("Invalid tenant-specific status in access export")
        user["tenant_statuses"] = dict(statuses)
        if source.get("clerk_user_id"):
            user["clerk_user_id"] = source["clerk_user_id"]
        users.append(user)
    return users, associations


async def http_transport(url, **options):
    def send():
        # Clerk's edge can reject urllib's default Python User-Agent (error 1010).
        headers = {"User-Agent": "RentalDesk/0.1", **options["headers"]}
        request = Request(url, data=options.get("body", "").encode() if "body" in options else None,
                          headers=headers, method=options["method"])
        try:
            with urlopen(request, timeout=30) as response:
                return response.status, response.read().decode()
        except HTTPError as error:
            # The directory only exposes allowlisted codes, never raw messages.
            return error.code, error.read(65536).decode("utf-8", errors="replace")
    status, body = await asyncio.to_thread(send)

    class Response:
        async def text(self):
            return body
    response = Response()
    response.status = status
    return response


async def apply_plan(users, associations, directory):
    results = []
    for user in users:
        try:
            await directory.sync_access(user, associations)
            results.append({"user_id": user["id"], "status": "applied"})
        except DomainError as error:
            results.append({"user_id": user["id"], "status": "failed", "error": str(error)})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--users", required=True, type=Path, help="Existing JSON user or Tenant Access KV export")
    parser.add_argument("--associations", required=True, type=Path, help="JSON association array with clerk_organization_id mappings")
    parser.add_argument("--apply", action="store_true", help="Write the planned roles to Clerk using CLERK_SECRET_KEY; otherwise validate offline")
    args = parser.parse_args(argv)
    try:
        users, associations = migration_plan(json.loads(args.users.read_text()), json.loads(args.associations.read_text()))
        if not args.apply:
            print(json.dumps({"mode": "dry-run", "users": len(users), "associations": len(associations), "network_requests": 0}))
            return 0
        secret = os.environ.get("CLERK_SECRET_KEY")
        if not secret:
            raise ValueError("Set CLERK_SECRET_KEY in the environment before using --apply")
        results = asyncio.run(apply_plan(users, associations, ClerkDirectory(secret, http_transport)))
        print(json.dumps({"mode": "apply", "results": results}))
        return 1 if any(item["status"] == "failed" for item in results) else 0
    except (ValueError, KeyError, OSError, DomainError) as error:
        print(f"Migration not applied: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
