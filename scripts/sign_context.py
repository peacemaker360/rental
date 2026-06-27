from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.api_core import signed_context_headers


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate signed rental tenant context headers for debugging.")
    parser.add_argument("--tenant", required=True, help="Tenant slug, for example demo-association")
    parser.add_argument("--actor", default="debug-operator", help="Opaque actor id to include in history entries")
    parser.add_argument("--role", default="operator", choices=("viewer", "operator", "admin"))
    parser.add_argument("--secret", default=os.environ.get("RENTAL_CONTEXT_SECRET"))
    parser.add_argument("--no-issued-at", action="store_true", help="Omit the timestamp from the signed payload")
    args = parser.parse_args()

    if not args.secret:
        raise SystemExit("Set RENTAL_CONTEXT_SECRET or pass --secret")

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
