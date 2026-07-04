from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
WORKER_DIR = ROOT / "worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.api_core import signed_context_headers, validate_actor_id, validate_tenant_id


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate signed rental tenant context headers for debugging.")
    parser.add_argument("--tenant", required=True, help="Tenant slug, for example demo-association")
    parser.add_argument("--actor", default="debug-operator", help="Opaque actor id to include in history entries")
    parser.add_argument("--role", default="operator", choices=("viewer", "operator", "admin"))
    parser.add_argument("--secret", default=os.environ.get("RENTAL_CONTEXT_SECRET"))
    parser.add_argument("--no-issued-at", action="store_true", help="Omit the timestamp from the signed payload")
    args = parser.parse_args(argv)

    if not args.secret:
        raise SystemExit("Set RENTAL_CONTEXT_SECRET or pass --secret")
    tenant_error = validate_tenant_id(args.tenant)
    if tenant_error:
        raise SystemExit(tenant_error)
    actor_error = validate_actor_id(args.actor)
    if actor_error:
        raise SystemExit(actor_error)

    payload = {
        "tenant_id": args.tenant,
        "actor_id": args.actor,
        "role": args.role,
    }
    if not args.no_issued_at:
        payload["issued_at"] = time.time()

    for name, value in signed_context_headers(payload, args.secret).items():
        print(f"{name}: {value}")


if __name__ == "__main__":
    main()
