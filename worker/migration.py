from __future__ import annotations

import re
from typing import Any

from .domain import DomainError, export_package, import_package


PII_LEGACY_FIELDS = ("email", "phone", "telephone", "mobile", "address", "birthdate")


def get_value(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    lowered = {str(key).lower(): value for key, value in row.items()}
    for name in names:
        if name in row:
            return row[name]
        lowered_name = name.lower()
        if lowered_name in lowered:
            return lowered[lowered_name]
    return default


def clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def slug_id(prefix: str, value: Any, fallback_index: int) -> str:
    raw = clean_text(value) or str(fallback_index)
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw).strip("_").lower()
    return f"{prefix}_legacy_{slug or fallback_index}"


def legacy_to_package(source: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    records = {
        "instruments": [],
        "members": [],
        "rentals": [],
        "history": [],
    }
    instrument_ids: dict[str, str] = {}
    member_ids: dict[str, str] = {}
    omitted_pii: dict[str, int] = {field: 0 for field in PII_LEGACY_FIELDS}

    for index, row in enumerate(source.get("instruments", []), start=1):
        if not isinstance(row, dict):
            raise DomainError("legacy instruments must be objects")
        legacy_id = get_value(row, "id", "instrument_id", "Instrument ID", "serial", "Serial", default=index)
        serial = clean_text(get_value(row, "serial", "Serial", default=legacy_id))
        record_id = slug_id("inst", legacy_id, index)
        instrument_ids[clean_text(legacy_id)] = record_id
        if serial:
            instrument_ids[serial] = record_id
        records["instruments"].append({
            "id": record_id,
            "tenant_id": tenant_id,
            "name": clean_text(get_value(row, "name", "Name")) or f"Instrument {index}",
            "brand": clean_text(get_value(row, "brand", "Brand")),
            "type": clean_text(get_value(row, "type", "Type")),
            "serial": serial or record_id,
            "description": nullable_text(get_value(row, "description", "Description")),
            "value_chf": number_or_none(get_value(row, "value_chf", "price", "Price")),
            "purchase_year": year_or_none(get_value(row, "purchase_year", "year_of_purchase", "Year Of Purchase")),
        })

    legacy_members = source.get("members", source.get("customers", []))
    for index, row in enumerate(legacy_members, start=1):
        if not isinstance(row, dict):
            raise DomainError("legacy members/customers must be objects")
        for field in PII_LEGACY_FIELDS:
            if get_value(row, field) not in (None, ""):
                omitted_pii[field] += 1

        legacy_id = get_value(row, "id", "customer_id", "Customer ID", "external_id", default=index)
        record_id = slug_id("mem", legacy_id, index)
        member_ids[clean_text(legacy_id)] = record_id
        external_id = clean_text(get_value(row, "external_id", "External ID"))
        if external_id:
            member_ids[external_id] = record_id

        given_name = nullable_text(get_value(row, "firstname", "first_name", "given_name", "First Name"))
        family_name = nullable_text(get_value(row, "lastname", "last_name", "family_name", "Last Name"))
        display_name = clean_text(get_value(row, "display_name", "name", "Name"))
        if not display_name:
            display_name = " ".join(part for part in (given_name, family_name) if part)
        records["members"].append({
            "id": record_id,
            "tenant_id": tenant_id,
            "display_name": display_name or f"Member {index}",
            "given_name": given_name,
            "family_name": family_name,
            "member_ref": external_id or f"legacy-customer-{clean_text(legacy_id)}",
            "contact_hint": "Contact details intentionally omitted during migration",
            "groups": list_or_empty(get_value(row, "groups")),
            "is_active": boolish(get_value(row, "is_active", "active", default=True)),
        })

    for index, row in enumerate(source.get("rentals", []), start=1):
        if not isinstance(row, dict):
            raise DomainError("legacy rentals must be objects")
        legacy_id = get_value(row, "id", "rental_id", default=index)
        instrument_ref = clean_text(get_value(row, "instrument_id", "Instrument ID", "instrument", "serial"))
        member_ref = clean_text(get_value(row, "member_id", "customer_id", "Customer ID", "member", "customer"))
        instrument_id = instrument_ids.get(instrument_ref)
        member_id = member_ids.get(member_ref)
        if not instrument_id:
            raise DomainError(f"legacy rental {legacy_id} references unknown instrument {instrument_ref}")
        if not member_id:
            raise DomainError(f"legacy rental {legacy_id} references unknown member {member_ref}")
        records["rentals"].append({
            "id": slug_id("rent", legacy_id, index),
            "tenant_id": tenant_id,
            "instrument_id": instrument_id,
            "member_id": member_id,
            "start_date": clean_text(get_value(row, "start_date", "Start Date")),
            "due_date": nullable_text(get_value(row, "due_date", "end_date", "End Date")),
            "return_date": nullable_text(get_value(row, "return_date", "Return Date")),
            "note": nullable_text(get_value(row, "note", "description", "Description")),
        })

    package = export_package(import_package({"records": records}, tenant_id), tenant_id)
    package["migration"] = {
        "source": "legacy-flask",
        "pii_fields_omitted": [
            {"field": key, "count": count}
            for key, count in omitted_pii.items()
            if count
        ],
        "notes": [
            "Member email and phone fields are not copied to the KV package.",
            "Use member_ref to reconnect records to the association roster if needed.",
        ],
    }
    return package


def nullable_text(value: Any) -> str | None:
    text = clean_text(value)
    return text or None


def number_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def year_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    text = clean_text(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        text = text[:4]
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return clean_text(value, "true").lower() not in ("0", "false", "no", "inactive")


def list_or_empty(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    return [value]
