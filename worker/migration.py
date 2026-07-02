from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from .domain import (
    DomainError,
    EMAIL_PATTERN,
    PHONE_PATTERN,
    export_package,
    import_package,
    normalize_instrument,
    normalize_member,
    scan_blocked_fields,
    utc_now,
)


PII_LEGACY_FIELDS = ("email", "phone", "telephone", "mobile", "address", "birthdate")
PII_HITOBITO_FIELDS = ("email", "phone", "telephone", "mobile", "address", "birthday", "birthdate")
INSTRUMENT_EXPORT_SCHEMA = "association-rental-instruments"


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
        description = low_pii_legacy_text(
            get_value(row, "description", "Description"),
            omitted_pii,
            "instrument_description_contact",
        )
        records["instruments"].append({
            "id": record_id,
            "tenant_id": tenant_id,
            "name": clean_text(get_value(row, "name", "Name")) or f"Instrument {index}",
            "brand": clean_text(get_value(row, "brand", "Brand")),
            "type": clean_text(get_value(row, "type", "Type")),
            "serial": serial or record_id,
            "description": description,
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
        rental_note = low_pii_legacy_text(get_value(row, "note", "description", "Description"), omitted_pii, "rental_note_contact")
        records["rentals"].append({
            "id": slug_id("rent", legacy_id, index),
            "tenant_id": tenant_id,
            "instrument_id": instrument_id,
            "member_id": member_id,
            "start_date": clean_text(get_value(row, "start_date", "Start Date")),
            "due_date": nullable_text(get_value(row, "due_date", "end_date", "End Date")),
            "return_date": nullable_text(get_value(row, "return_date", "Return Date")),
            "note": rental_note,
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


def low_pii_legacy_text(value: Any, omitted_pii: dict[str, int], report_field: str) -> str | None:
    text = nullable_text(value)
    if not text:
        return None
    if EMAIL_PATTERN.search(text) or PHONE_PATTERN.search(text):
        omitted_pii[report_field] = omitted_pii.get(report_field, 0) + 1
        return None
    return text


def instrument_export_package(records: dict[str, list[dict[str, Any]]], tenant_id: str) -> dict[str, Any]:
    instruments = deepcopy(records.get("instruments", []))
    return {
        "schema": INSTRUMENT_EXPORT_SCHEMA,
        "version": 1,
        "tenant_id": tenant_id,
        "exported_at": utc_now(),
        "records": {"instruments": instruments},
        "summary": {"instruments": len(instruments)},
    }


def merge_instruments(records: dict[str, list[dict[str, Any]]], tenant_id: str, payload: Any) -> dict[str, Any]:
    blocked = scan_blocked_fields(payload)
    if blocked:
        raise DomainError(f"blocked PII fields found: {', '.join(blocked[:5])}")
    rows = extract_instrument_rows(payload)
    by_id = {instrument.get("id"): index for index, instrument in enumerate(records["instruments"]) if instrument.get("id")}
    by_serial = {
        clean_text(instrument.get("serial")).lower(): index
        for index, instrument in enumerate(records["instruments"])
        if clean_text(instrument.get("serial"))
    }
    created = 0
    updated = 0

    for row in rows:
        incoming_id = clean_text(get_value(row, "id", "instrument_id", "Instrument ID"))
        incoming_serial = clean_text(get_value(row, "serial", "Serial"))
        existing_index = by_id.get(incoming_id) if incoming_id else None
        if existing_index is None and incoming_serial:
            existing_index = by_serial.get(incoming_serial.lower())

        existing = records["instruments"][existing_index] if existing_index is not None else None
        instrument = normalize_instrument(row, tenant_id, existing)
        if existing_index is None:
            records["instruments"].append(instrument)
            by_id[instrument["id"]] = len(records["instruments"]) - 1
            by_serial[instrument["serial"].lower()] = len(records["instruments"]) - 1
            created += 1
            continue

        records["instruments"][existing_index] = instrument
        by_id[instrument["id"]] = existing_index
        by_serial[instrument["serial"].lower()] = existing_index
        updated += 1

    return {
        "source": "instrument-json",
        "received": len(rows),
        "created": created,
        "updated": updated,
        "notes": [
            "Instrument imports merge by serial number, preserving local ids and rentals.",
            "Use full tenant import/export when rentals, members, history, or service records must move together.",
        ],
    }


def extract_instrument_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [flatten_instrument_item(item) for item in payload]
    if not isinstance(payload, dict):
        raise DomainError("instrument import payload must be an object or array")
    if isinstance(payload.get("instruments"), list):
        return [flatten_instrument_item(item) for item in payload["instruments"]]
    records = payload.get("records")
    if isinstance(records, dict) and isinstance(records.get("instruments"), list):
        return [flatten_instrument_item(item) for item in records["instruments"]]
    data = payload.get("data")
    if isinstance(data, list):
        return [flatten_instrument_item(item) for item in data]
    raise DomainError("instrument import payload must contain instruments, records.instruments, or data")


def flatten_instrument_item(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise DomainError("instrument records must be objects")
    attributes = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
    return {**attributes, **{key: value for key, value in item.items() if key != "attributes"}}


def hitobito_members_to_records(payload: Any, tenant_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    people = extract_hitobito_people(payload)
    omitted_pii: dict[str, int] = {field: 0 for field in PII_HITOBITO_FIELDS}
    records = []

    for index, person in enumerate(people, start=1):
        if not isinstance(person, dict):
            raise DomainError("hitobito people must be objects")
        for field in PII_HITOBITO_FIELDS:
            if get_value(person, field) not in (None, ""):
                omitted_pii[field] += 1

        hitobito_id = clean_text(get_value(person, "id", "person_id", "hitobito_id", default=index))
        given_name = nullable_text(get_value(person, "first_name", "firstname", "given_name", "First Name"))
        family_name = nullable_text(get_value(person, "last_name", "lastname", "family_name", "Last Name"))
        display_name = clean_text(get_value(person, "display_name", "full_name", "name", "Name"))
        if not display_name:
            display_name = " ".join(part for part in (given_name, family_name) if part)

        record = normalize_member({
            "display_name": display_name or f"Hitobito member {index}",
            "given_name": given_name,
            "family_name": family_name,
            "member_ref": f"hitobito:{hitobito_id}",
            "contact_hint": "Contact details stored in Hitobito",
            "groups": hitobito_groups(person),
            "is_active": hitobito_active(person),
        }, tenant_id)
        record["id"] = slug_id("mem_hitobito", hitobito_id, index)
        records.append(record)

    report = {
        "source": "hitobito",
        "received": len(people),
        "pii_fields_omitted": [
            {"field": key, "count": count}
            for key, count in omitted_pii.items()
            if count
        ],
        "notes": [
            "Hitobito email, phone, address, and birthday fields are not copied to KV.",
            "member_ref keeps the stable hitobito:{id} link for repeat imports.",
        ],
    }
    return records, report


def merge_hitobito_members(records: dict[str, list[dict[str, Any]]], tenant_id: str, payload: Any) -> dict[str, Any]:
    imported_members, report = hitobito_members_to_records(payload, tenant_id)
    by_ref = {member.get("member_ref"): index for index, member in enumerate(records["members"]) if member.get("member_ref")}
    created = 0
    updated = 0
    for member in imported_members:
        existing_index = by_ref.get(member["member_ref"])
        if existing_index is None:
            records["members"].append(member)
            by_ref[member["member_ref"]] = len(records["members"]) - 1
            created += 1
            continue
        existing = records["members"][existing_index]
        records["members"][existing_index] = {
            **existing,
            "display_name": member["display_name"],
            "given_name": member.get("given_name"),
            "family_name": member.get("family_name"),
            "contact_hint": member.get("contact_hint"),
            "groups": member.get("groups", []),
            "is_active": member.get("is_active", True),
            "updated_at": member["updated_at"],
        }
        updated += 1
    return {**report, "created": created, "updated": updated}


def extract_hitobito_people(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [flatten_hitobito_person(item) for item in payload]
    if not isinstance(payload, dict):
        raise DomainError("hitobito import payload must be an object or array")
    for key in ("people", "persons", "members"):
        if isinstance(payload.get(key), list):
            return [flatten_hitobito_person(item) for item in payload[key]]
    data = payload.get("data")
    if isinstance(data, list):
        return [flatten_hitobito_person(item) for item in data]
    raise DomainError("hitobito import payload must contain people, persons, members, or data")


def flatten_hitobito_person(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise DomainError("hitobito people must be objects")
    attributes = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
    flattened = {**attributes, **{key: value for key, value in item.items() if key not in ("attributes", "relationships")}}
    relationships = item.get("relationships") if isinstance(item.get("relationships"), dict) else {}
    if relationships and "groups" not in flattened:
        relationship_groups = relationships.get("groups") or relationships.get("group") or relationships.get("roles")
        if isinstance(relationship_groups, dict):
            relationship_groups = relationship_groups.get("data", relationship_groups)
        flattened["groups"] = relationship_groups or []
    return flattened


def hitobito_groups(person: dict[str, Any]) -> list[str]:
    values = []
    raw = get_value(person, "groups", "group_names", "roles", "role_names", default=[])
    if isinstance(raw, dict):
        raw = raw.get("data", raw.get("groups", []))
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                name = get_value(item, "name", "label", "id", default="")
                if name:
                    values.append(clean_text(name))
            elif clean_text(item):
                values.append(clean_text(item))
    elif clean_text(raw):
        values.append(clean_text(raw))
    return values


def hitobito_active(person: dict[str, Any]) -> bool:
    status = clean_text(get_value(person, "status", "state", default="active")).lower()
    if status in ("inactive", "archived", "deleted", "disabled"):
        return False
    return boolish(get_value(person, "is_active", "active", default=True))


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
