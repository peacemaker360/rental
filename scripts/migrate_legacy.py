from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "worker"))
sys.path.insert(0, str(ROOT))

from worker.migration import legacy_to_package


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser(description="Transform legacy Flask rental exports into the KV JSON package.")
    parser.add_argument("--tenant", required=True, help="Tenant id for the target association.")
    parser.add_argument("--legacy-json", type=Path, help="JSON object with instruments, customers/members, and rentals arrays.")
    parser.add_argument("--instruments-csv", type=Path, help="Legacy instruments CSV export.")
    parser.add_argument("--members-json", type=Path, help="Legacy customers/members JSON file.")
    parser.add_argument("--rentals-csv", type=Path, help="Legacy rentals CSV export.")
    parser.add_argument("--output", type=Path, help="Output JSON package. Defaults to stdout.")
    args = parser.parse_args()

    if args.legacy_json:
        source = read_json(args.legacy_json)
    else:
        members_payload = read_json(args.members_json) if args.members_json else {}
        source = {
            "instruments": read_csv(args.instruments_csv) if args.instruments_csv else [],
            "members": members_payload.get("members", members_payload.get("customers", [])),
            "rentals": read_csv(args.rentals_csv) if args.rentals_csv else [],
        }

    package = legacy_to_package(source, args.tenant)
    payload = json.dumps(package, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
