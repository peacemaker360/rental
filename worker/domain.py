from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import re
from typing import Any
from uuid import uuid4


ENTITY_TYPES = ("instruments", "members", "rentals", "service_records", "history")
EXPORT_SCHEMA_VERSION = 1
BLOCKED_MEMBER_FIELDS = {"email", "phone", "telephone", "mobile", "address", "birthday", "birthdate"}
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PHONE_PATTERN = re.compile(r"(?=(?:\D*\d){7,})\+?[\d][\d\s()./-]{6,}\d")
SERVICE_CONDITIONS = {"good", "watch", "needs_service", "in_service", "retired"}


class DomainError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_iso() -> str:
    return date.today().isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def optional_text(value: Any) -> str | None:
    text = clean_text(value)
    return text or None


def normalize_email(value: Any) -> str:
    return clean_text(value).lower()


def email_hash(value: Any) -> str | None:
    email = normalize_email(value)
    if not email:
        return None
    if not EMAIL_PATTERN.fullmatch(email):
        raise DomainError("access_email must be a valid email address")
    return hashlib.sha256(email.encode("utf-8")).hexdigest()


def require_text(payload: dict[str, Any], field: str) -> str:
    value = clean_text(payload.get(field))
    if not value:
        raise DomainError(f"{field} is required")
    return value


def validate_date(value: Any, field: str, required: bool = False) -> str | None:
    text = clean_text(value)
    if not text:
        if required:
            raise DomainError(f"{field} is required")
        return None
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise DomainError(f"{field} must use YYYY-MM-DD") from exc
    return text


def clone_records(records: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {entity: deepcopy(records.get(entity, [])) for entity in ENTITY_TYPES}


def empty_records() -> dict[str, list[dict[str, Any]]]:
    return {entity: [] for entity in ENTITY_TYPES}


def scan_blocked_fields(value: Any, path: str = "payload") -> list[str]:
    blocked: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key.lower() in BLOCKED_MEMBER_FIELDS and key.lower() != "access_email":
                blocked.append(child_path)
            blocked.extend(scan_blocked_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            blocked.extend(scan_blocked_fields(child, f"{path}[{index}]"))
    return blocked


def reject_blocked_member_pii(payload: dict[str, Any]) -> None:
    blocked = scan_blocked_fields(payload)
    if blocked:
        raise DomainError(f"blocked PII fields found: {', '.join(blocked[:5])}")

    email_fields = ("display_name", "given_name", "family_name", "member_ref", "contact_hint")
    for field in email_fields:
        value = clean_text(payload.get(field))
        if value and EMAIL_PATTERN.search(value):
            raise DomainError(f"{field} must not contain email addresses")

    contact_hint = clean_text(payload.get("contact_hint"))
    if contact_hint and PHONE_PATTERN.search(contact_hint):
        raise DomainError("contact_hint must not contain phone numbers")


def reject_contact_reference_pii(payload: dict[str, Any], *fields: str) -> None:
    for field in fields:
        value = clean_text(payload.get(field))
        if not value:
            continue
        if EMAIL_PATTERN.search(value):
            raise DomainError(f"{field} must not contain email addresses")
        if PHONE_PATTERN.search(value):
            raise DomainError(f"{field} must not contain phone numbers")


def clean_actor_id(value: Any, default: str = "system") -> str:
    actor = clean_text(value) or default
    if EMAIL_PATTERN.search(actor):
        raise DomainError("actor must be opaque, not an email address")
    if PHONE_PATTERN.search(actor):
        raise DomainError("actor must be opaque, not a phone number")
    return actor


def normalize_instrument(
    payload: dict[str, Any],
    tenant_id: str,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    reject_contact_reference_pii({"description": payload.get("description", current.get("description"))}, "description")
    now = utc_now()
    brand = clean_text(payload.get("brand", current.get("brand")))
    instrument_type = clean_text(payload.get("type", current.get("type")))
    serial = require_text(payload if "serial" in payload or existing is None else current, "serial")
    name = clean_text(payload.get("name", current.get("name")))
    if not name:
        parts = [part for part in (brand, instrument_type, serial) if part]
        name = " ".join(parts)
    if not name:
        raise DomainError("name is required")

    value = payload.get("value_chf", current.get("value_chf"))
    if value in ("", None):
        value = None
    else:
        try:
            value = float(value)
        except (TypeError, ValueError) as exc:
            raise DomainError("value_chf must be a number") from exc

    purchase_year = payload.get("purchase_year", current.get("purchase_year"))
    if purchase_year in ("", None):
        purchase_year = None
    else:
        try:
            purchase_year = int(purchase_year)
        except (TypeError, ValueError) as exc:
            raise DomainError("purchase_year must be a year") from exc

    return {
        "id": current.get("id") or new_id("inst"),
        "tenant_id": tenant_id,
        "name": name,
        "brand": brand,
        "type": instrument_type,
        "serial": serial,
        "description": optional_text(payload.get("description", current.get("description"))),
        "value_chf": value,
        "purchase_year": purchase_year,
        "created_at": current.get("created_at") or now,
        "updated_at": now,
    }


def normalize_member(
    payload: dict[str, Any],
    tenant_id: str,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    reject_blocked_member_pii(payload)
    now = utc_now()
    display_name = clean_text(payload.get("display_name", current.get("display_name")))
    given_name = optional_text(payload.get("given_name", current.get("given_name")))
    family_name = optional_text(payload.get("family_name", current.get("family_name")))
    if not display_name:
        display_name = " ".join(part for part in (given_name, family_name) if part)
    if not display_name:
        raise DomainError("display_name is required")
    access_email_hash = current.get("access_email_hash")
    if "access_email" in payload:
        access_email_hash = email_hash(payload.get("access_email"))
    elif "access_email_hash" in payload:
        access_email_hash = clean_text(payload.get("access_email_hash")) or None

    return {
        "id": current.get("id") or new_id("mem"),
        "tenant_id": tenant_id,
        "display_name": display_name,
        "given_name": given_name,
        "family_name": family_name,
        "member_ref": optional_text(payload.get("member_ref", current.get("member_ref"))),
        "contact_hint": optional_text(payload.get("contact_hint", current.get("contact_hint"))),
        "access_email_hash": access_email_hash,
        "groups": payload.get("groups", current.get("groups", [])) or [],
        "is_active": bool(payload.get("is_active", current.get("is_active", True))),
        "created_at": current.get("created_at") or now,
        "updated_at": now,
    }


def normalize_rental(
    payload: dict[str, Any],
    tenant_id: str,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    reject_contact_reference_pii({"note": payload.get("note", current.get("note"))}, "note")
    now = utc_now()
    return {
        "id": current.get("id") or new_id("rent"),
        "tenant_id": tenant_id,
        "instrument_id": require_text(payload if "instrument_id" in payload or existing is None else current, "instrument_id"),
        "member_id": require_text(payload if "member_id" in payload or existing is None else current, "member_id"),
        "start_date": validate_date(payload.get("start_date", current.get("start_date")), "start_date", True),
        "due_date": validate_date(payload.get("due_date", current.get("due_date")), "due_date"),
        "return_date": validate_date(payload.get("return_date", current.get("return_date")), "return_date"),
        "note": optional_text(payload.get("note", current.get("note"))),
        "created_at": current.get("created_at") or now,
        "updated_at": now,
    }


def normalize_service_record(
    payload: dict[str, Any],
    tenant_id: str,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = existing or {}
    reject_contact_reference_pii({
        "provider": payload.get("provider", current.get("provider")),
        "note": payload.get("note", current.get("note")),
    }, "provider", "note")
    now = utc_now()
    condition = clean_text(payload.get("condition", current.get("condition", "good")), "good")
    if condition not in SERVICE_CONDITIONS:
        raise DomainError("condition must be good, watch, needs_service, in_service, or retired")

    cost = payload.get("cost_chf", current.get("cost_chf"))
    if cost in ("", None):
        cost = None
    else:
        try:
            cost = float(cost)
        except (TypeError, ValueError) as exc:
            raise DomainError("cost_chf must be a number") from exc

    return {
        "id": current.get("id") or new_id("svc"),
        "tenant_id": tenant_id,
        "instrument_id": require_text(payload if "instrument_id" in payload or existing is None else current, "instrument_id"),
        "service_date": validate_date(payload.get("service_date", current.get("service_date", today_iso())), "service_date", True),
        "next_service_date": validate_date(payload.get("next_service_date", current.get("next_service_date")), "next_service_date"),
        "condition": condition,
        "job_type": optional_text(payload.get("job_type", current.get("job_type"))),
        "provider": optional_text(payload.get("provider", current.get("provider"))),
        "note": optional_text(payload.get("note", current.get("note"))),
        "cost_chf": cost,
        "created_at": current.get("created_at") or now,
        "updated_at": now,
    }


def index_by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in items}


def active_rental_for_instrument(
    rentals: list[dict[str, Any]],
    instrument_id: str,
    exclude_rental_id: str | None = None,
) -> dict[str, Any] | None:
    for rental in rentals:
        if rental["instrument_id"] != instrument_id:
            continue
        if rental.get("return_date"):
            continue
        if exclude_rental_id and rental["id"] == exclude_rental_id:
            continue
        return rental
    return None


def rental_status(rental: dict[str, Any]) -> str:
    if rental.get("return_date"):
        return "returned"
    due_date = rental.get("due_date")
    if due_date and due_date < today_iso():
        return "overdue"
    return "active"


def instrument_status(instrument_id: str, rentals: list[dict[str, Any]]) -> str:
    rental = active_rental_for_instrument(rentals, instrument_id)
    if not rental:
        return "available"
    if rental_status(rental) == "overdue":
        return "overdue"
    return "rented"


def service_due_status(next_service_date: str | None) -> str:
    if not next_service_date:
        return "ok"
    today = date.fromisoformat(today_iso())
    due = date.fromisoformat(next_service_date)
    if due < today:
        return "overdue"
    if (due - today).days <= 30:
        return "due_soon"
    return "ok"


def hydrate(records: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    result = clone_records(records)
    members = index_by_id(result["members"])
    instruments = index_by_id(result["instruments"])
    service_records_by_instrument: dict[str, list[dict[str, Any]]] = {}
    for service_record in sorted(result["service_records"], key=lambda item: item.get("service_date") or "", reverse=True):
        service_records_by_instrument.setdefault(service_record.get("instrument_id"), []).append(service_record)

    for instrument in result["instruments"]:
        instrument["status"] = instrument_status(instrument["id"], result["rentals"])
        service_records = service_records_by_instrument.get(instrument["id"], [])
        instrument["service_condition"] = service_records[0]["condition"] if service_records else "good"
        instrument["last_service_date"] = service_records[0]["service_date"] if service_records else None
        instrument["next_service_date"] = service_records[0].get("next_service_date") if service_records else None
        instrument["service_due_status"] = service_due_status(instrument["next_service_date"])
        instrument["service_record_count"] = len(service_records)

    for rental in result["rentals"]:
        rental["status"] = rental_status(rental)
        member = members.get(rental["member_id"])
        instrument = instruments.get(rental["instrument_id"])
        rental["member_name"] = member["display_name"] if member else "Unknown member"
        rental["instrument_name"] = instrument["name"] if instrument else "Unknown instrument"

    for service_record in result["service_records"]:
        instrument = instruments.get(service_record["instrument_id"])
        service_record["instrument_name"] = instrument["name"] if instrument else "Unknown instrument"
        service_record["instrument_serial"] = instrument.get("serial") if instrument else None
        service_record["service_due_status"] = service_due_status(service_record.get("next_service_date"))

    return result


def summary(records: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    hydrated = hydrate(records)
    return {
        "instruments": len(hydrated["instruments"]),
        "members": len([member for member in hydrated["members"] if member.get("is_active", True)]),
        "active_rentals": len([rental for rental in hydrated["rentals"] if rental["status"] in ("active", "overdue")]),
        "available_instruments": len([item for item in hydrated["instruments"] if item["status"] == "available"]),
        "overdue_rentals": len([rental for rental in hydrated["rentals"] if rental["status"] == "overdue"]),
        "service_attention": len([
            item for item in hydrated["instruments"]
            if item.get("service_condition") in ("watch", "needs_service", "in_service")
            or item.get("service_due_status") in ("due_soon", "overdue")
        ]),
    }


def add_history(
    records: dict[str, list[dict[str, Any]]],
    tenant_id: str,
    rental: dict[str, Any],
    action: str,
    actor: str = "system",
) -> dict[str, Any]:
    hydrated = hydrate(records)
    rental_view = next((item for item in hydrated["rentals"] if item["id"] == rental["id"]), rental)
    instrument = next((item for item in records["instruments"] if item["id"] == rental.get("instrument_id")), None)
    member = next((item for item in records["members"] if item["id"] == rental.get("member_id")), None)
    entry = {
        "id": new_id("hist"),
        "tenant_id": tenant_id,
        "rental_id": rental["id"],
        "instrument_id": rental.get("instrument_id"),
        "instrument_name": rental_view.get("instrument_name") or (instrument or {}).get("name"),
        "member_id": rental.get("member_id"),
        "member_name": rental_view.get("member_name") or (member or {}).get("display_name"),
        "start_date": rental.get("start_date"),
        "due_date": rental.get("due_date"),
        "return_date": rental.get("return_date"),
        "note": rental.get("note"),
        "action": action,
        "actor": clean_actor_id(actor),
        "created_at": utc_now(),
    }
    records["history"].append(entry)
    return entry


def add_service_history(
    records: dict[str, list[dict[str, Any]]],
    tenant_id: str,
    service_record: dict[str, Any],
    action: str,
    actor: str = "system",
) -> dict[str, Any]:
    instrument = next((item for item in records["instruments"] if item["id"] == service_record.get("instrument_id")), None)
    instrument_name = service_record.get("instrument_name") or (instrument or {}).get("name")
    entry = {
        "id": new_id("hist"),
        "tenant_id": tenant_id,
        "rental_id": None,
        "service_record_id": service_record.get("id"),
        "instrument_id": service_record.get("instrument_id"),
        "instrument_name": instrument_name,
        "member_id": None,
        "member_name": None,
        "start_date": None,
        "due_date": None,
        "return_date": None,
        "service_date": service_record.get("service_date"),
        "next_service_date": service_record.get("next_service_date"),
        "service_condition": service_record.get("condition"),
        "note": service_record.get("note") or service_record.get("job_type"),
        "action": action,
        "actor": clean_actor_id(actor),
        "created_at": utc_now(),
    }
    records["history"].append(entry)
    return entry


def create_record(
    records: dict[str, list[dict[str, Any]]],
    tenant_id: str,
    entity: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if entity == "instruments":
        record = normalize_instrument(payload, tenant_id)
    elif entity == "members":
        record = normalize_member(payload, tenant_id)
    elif entity == "rentals":
        ensure_known_references(records, payload.get("instrument_id"), payload.get("member_id"))
        if active_rental_for_instrument(records["rentals"], clean_text(payload.get("instrument_id"))):
            raise DomainError("instrument already has an active rental", 409)
        record = normalize_rental(payload, tenant_id)
    elif entity == "service_records":
        ensure_known_instrument(records, payload.get("instrument_id"))
        record = normalize_service_record(payload, tenant_id)
    else:
        raise DomainError(f"cannot create {entity}", 405)
    records[entity].append(record)
    if entity == "rentals":
        add_history(records, tenant_id, record, "created", clean_actor_id(payload.get("actor"), "system"))
    if entity == "service_records":
        add_service_history(records, tenant_id, record, "created", clean_actor_id(payload.get("actor"), "system"))
    return record


def update_record(
    records: dict[str, list[dict[str, Any]]],
    tenant_id: str,
    entity: str,
    record_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    existing = find_record(records, entity, record_id)
    if entity == "instruments":
        updated = normalize_instrument(payload, tenant_id, existing)
    elif entity == "members":
        updated = normalize_member(payload, tenant_id, existing)
    elif entity == "rentals":
        instrument_id = clean_text(payload.get("instrument_id", existing.get("instrument_id")))
        member_id = clean_text(payload.get("member_id", existing.get("member_id")))
        ensure_known_references(records, instrument_id, member_id)
        active = active_rental_for_instrument(records["rentals"], instrument_id, exclude_rental_id=record_id)
        if active:
            raise DomainError("instrument already has an active rental", 409)
        updated = normalize_rental(payload, tenant_id, existing)
    elif entity == "service_records":
        instrument_id = clean_text(payload.get("instrument_id", existing.get("instrument_id")))
        ensure_known_instrument(records, instrument_id)
        updated = normalize_service_record(payload, tenant_id, existing)
    else:
        raise DomainError(f"cannot update {entity}", 405)
    replace_record(records, entity, record_id, updated)
    if entity == "rentals":
        add_history(records, tenant_id, updated, "updated", clean_actor_id(payload.get("actor"), "system"))
    if entity == "service_records":
        add_service_history(records, tenant_id, updated, "updated", clean_actor_id(payload.get("actor"), "system"))
    return updated


def return_rental(
    records: dict[str, list[dict[str, Any]]],
    tenant_id: str,
    record_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    rental = find_record(records, "rentals", record_id)
    if rental.get("return_date"):
        return rental
    updated = {**rental, "return_date": validate_date(payload.get("return_date", today_iso()), "return_date", True), "updated_at": utc_now()}
    replace_record(records, "rentals", record_id, updated)
    add_history(records, tenant_id, updated, "returned", clean_actor_id(payload.get("actor"), "system"))
    return updated


def delete_record(records: dict[str, list[dict[str, Any]]], entity: str, record_id: str) -> dict[str, Any]:
    record = find_record(records, entity, record_id)
    if entity == "instruments":
        if active_rental_for_instrument(records["rentals"], record_id):
            raise DomainError("cannot delete instrument with active rentals", 409)
    if entity == "members":
        active = [rental for rental in records["rentals"] if rental.get("member_id") == record_id and not rental.get("return_date")]
        if active:
            raise DomainError("cannot delete member with active rentals", 409)
    if entity == "history":
        raise DomainError("history is append-only", 405)
    records[entity] = [item for item in records[entity] if item["id"] != record_id]
    if entity == "instruments":
        records["service_records"] = [item for item in records["service_records"] if item.get("instrument_id") != record_id]
    return record


def find_record(records: dict[str, list[dict[str, Any]]], entity: str, record_id: str) -> dict[str, Any]:
    if entity not in ENTITY_TYPES:
        raise DomainError("unknown entity", 404)
    for item in records[entity]:
        if item.get("id") == record_id:
            return item
    raise DomainError("record not found", 404)


def replace_record(records: dict[str, list[dict[str, Any]]], entity: str, record_id: str, updated: dict[str, Any]) -> None:
    records[entity] = [updated if item["id"] == record_id else item for item in records[entity]]


def ensure_known_references(records: dict[str, list[dict[str, Any]]], instrument_id: Any, member_id: Any) -> None:
    member_ids = {item["id"] for item in records["members"]}
    ensure_known_instrument(records, instrument_id)
    if clean_text(member_id) not in member_ids:
        raise DomainError("member not found", 404)


def ensure_known_instrument(records: dict[str, list[dict[str, Any]]], instrument_id: Any) -> None:
    instrument_ids = {item["id"] for item in records["instruments"]}
    if clean_text(instrument_id) not in instrument_ids:
        raise DomainError("instrument not found", 404)


def export_package(records: dict[str, list[dict[str, Any]]], tenant_id: str) -> dict[str, Any]:
    return {
        "schema": "association-rental",
        "version": EXPORT_SCHEMA_VERSION,
        "tenant_id": tenant_id,
        "exported_at": utc_now(),
        "records": clone_records(records),
        "summary": summary(records),
    }


def import_package(payload: dict[str, Any], tenant_id: str) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        raise DomainError("import payload must be an object")
    blocked = scan_blocked_fields(payload)
    if blocked:
        raise DomainError(f"blocked PII fields found: {', '.join(blocked[:5])}")

    source_records = payload.get("records", payload)
    if not isinstance(source_records, dict):
        raise DomainError("records must be an object")

    imported = empty_records()
    id_maps: dict[str, dict[str, str]] = {"instruments": {}, "members": {}, "rentals": {}, "service_records": {}}

    for raw in source_records.get("instruments", []):
        if not isinstance(raw, dict):
            raise DomainError("instrument records must be objects")
        record = normalize_imported_record(normalize_instrument(raw, tenant_id), raw, tenant_id)
        imported["instruments"].append(record)
        id_maps["instruments"][clean_text(raw.get("id"), record["id"])] = record["id"]

    for raw in source_records.get("members", []):
        if not isinstance(raw, dict):
            raise DomainError("member records must be objects")
        record = normalize_imported_record(normalize_member(raw, tenant_id), raw, tenant_id)
        imported["members"].append(record)
        id_maps["members"][clean_text(raw.get("id"), record["id"])] = record["id"]

    for raw in source_records.get("service_records", []):
        if not isinstance(raw, dict):
            raise DomainError("service records must be objects")
        raw_service = dict(raw)
        original_instrument_id = clean_text(raw_service.get("instrument_id"))
        raw_service["instrument_id"] = id_maps["instruments"].get(original_instrument_id, original_instrument_id)
        ensure_known_instrument(imported, raw_service.get("instrument_id"))
        record = normalize_imported_record(normalize_service_record(raw_service, tenant_id), raw_service, tenant_id)
        imported["service_records"].append(record)
        id_maps["service_records"][clean_text(raw.get("id"), record["id"])] = record["id"]

    for raw in source_records.get("rentals", []):
        if not isinstance(raw, dict):
            raise DomainError("rental records must be objects")
        raw_rental = dict(raw)
        original_instrument_id = clean_text(raw_rental.get("instrument_id"))
        original_member_id = clean_text(raw_rental.get("member_id"))
        raw_rental["instrument_id"] = id_maps["instruments"].get(original_instrument_id, original_instrument_id)
        raw_rental["member_id"] = id_maps["members"].get(original_member_id, original_member_id)
        ensure_known_references(imported, raw_rental.get("instrument_id"), raw_rental.get("member_id"))
        if active_rental_for_instrument(imported["rentals"], clean_text(raw_rental.get("instrument_id"))):
            raise DomainError("import contains duplicate active rentals for an instrument", 409)
        record = normalize_imported_record(normalize_rental(raw_rental, tenant_id), raw_rental, tenant_id)
        imported["rentals"].append(record)
        id_maps["rentals"][clean_text(raw.get("id"), record["id"])] = record["id"]

    for raw in source_records.get("history", []):
        if not isinstance(raw, dict):
            raise DomainError("history records must be objects")
        imported["history"].append(normalize_history_record(raw, tenant_id, id_maps))

    return imported


def normalize_imported_record(record: dict[str, Any], raw: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DomainError("records must be objects")
    imported = dict(record)
    raw_id = clean_text(raw.get("id"))
    if raw_id:
        imported["id"] = raw_id
    imported["tenant_id"] = tenant_id
    imported["created_at"] = clean_text(raw.get("created_at"), imported["created_at"])
    imported["updated_at"] = clean_text(raw.get("updated_at"), imported["updated_at"])
    return imported


def normalize_history_record(raw: dict[str, Any], tenant_id: str, id_maps: dict[str, dict[str, str]]) -> dict[str, Any]:
    created_at = clean_text(raw.get("created_at"), utc_now())
    rental_id = clean_text(raw.get("rental_id"))
    service_record_id = clean_text(raw.get("service_record_id"))
    instrument_id = clean_text(raw.get("instrument_id"))
    member_id = clean_text(raw.get("member_id"))
    return {
        "id": clean_text(raw.get("id"), new_id("hist")),
        "tenant_id": tenant_id,
        "rental_id": id_maps["rentals"].get(rental_id, rental_id) or None,
        "service_record_id": id_maps["service_records"].get(service_record_id, service_record_id) or None,
        "instrument_id": id_maps["instruments"].get(instrument_id, instrument_id) or None,
        "instrument_name": optional_text(raw.get("instrument_name")),
        "member_id": id_maps["members"].get(member_id, member_id) or None,
        "member_name": optional_text(raw.get("member_name")),
        "start_date": validate_date(raw.get("start_date"), "start_date"),
        "due_date": validate_date(raw.get("due_date"), "due_date"),
        "return_date": validate_date(raw.get("return_date"), "return_date"),
        "service_date": validate_date(raw.get("service_date"), "service_date"),
        "next_service_date": validate_date(raw.get("next_service_date"), "next_service_date"),
        "service_condition": optional_text(raw.get("service_condition")),
        "note": optional_text(raw.get("note")),
        "action": clean_text(raw.get("action"), "imported"),
        "actor": clean_actor_id(raw.get("actor"), "import"),
        "created_at": created_at,
    }


def demo_records(tenant_id: str) -> dict[str, list[dict[str, Any]]]:
    records = empty_records()
    piano = create_record(records, tenant_id, "instruments", {
        "name": "Stage piano CP-73",
        "brand": "Yamaha",
        "type": "Keyboard",
        "serial": "CP73-001",
        "value_chf": 1850,
        "purchase_year": 2022,
        "description": "Weighted keys with sustain pedal.",
    })
    trumpet = create_record(records, tenant_id, "instruments", {
        "name": "Student trumpet",
        "brand": "Bach",
        "type": "Trumpet",
        "serial": "TR-204",
        "value_chf": 640,
        "purchase_year": 2019,
    })
    alex = create_record(records, tenant_id, "members", {
        "display_name": "Alex Meyer",
        "member_ref": "M-1042",
        "contact_hint": "contact stored in association roster",
    })
    sam = create_record(records, tenant_id, "members", {
        "display_name": "Sam Keller",
        "member_ref": "M-2198",
        "contact_hint": "ask section lead",
    })
    create_record(records, tenant_id, "rentals", {
        "instrument_id": piano["id"],
        "member_id": alex["id"],
        "start_date": today_iso(),
        "due_date": None,
        "note": "Weekly rehearsal setup.",
    })
    create_record(records, tenant_id, "rentals", {
        "instrument_id": trumpet["id"],
        "member_id": sam["id"],
        "start_date": "2024-01-10",
        "due_date": "2024-02-10",
        "note": "Youth ensemble loan.",
    })
    create_record(records, tenant_id, "service_records", {
        "instrument_id": piano["id"],
        "service_date": "2025-09-14",
        "condition": "good",
        "next_service_date": "2026-09-14",
        "job_type": "Annual check",
        "provider": "Keys & Hammers",
        "note": "Cleaned contacts, checked pedal and firmware.",
        "cost_chf": 120,
    })
    create_record(records, tenant_id, "service_records", {
        "instrument_id": trumpet["id"],
        "service_date": "2026-01-18",
        "condition": "needs_service",
        "next_service_date": "2026-03-01",
        "job_type": "Valve revision",
        "provider": "Brass Atelier",
        "note": "Second valve sticks after longer rehearsals.",
        "cost_chf": None,
    })
    return records
