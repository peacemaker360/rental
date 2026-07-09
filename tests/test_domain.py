import unittest
from unittest.mock import patch

from worker.domain import (
    DomainError,
    create_record,
    delete_record,
    empty_records,
    export_package,
    hydrate,
    import_package,
    rental_status,
    return_rental,
    service_due_status,
    summary,
    update_record,
)


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.tenant_id = "test-association"
        self.records = empty_records()
        self.instrument = create_record(self.records, self.tenant_id, "instruments", {
            "name": "Tenor saxophone",
            "brand": "Selmer",
            "type": "Saxophone",
            "serial": "SX-1",
        })
        self.member = create_record(self.records, self.tenant_id, "members", {
            "display_name": "Jamie Example",
            "member_ref": "M-1",
        })

    def test_rental_status_uses_date_only_due_boundary(self):
        with patch("worker.domain.today_iso", return_value="2026-07-02"):
            self.assertEqual(rental_status({"due_date": "2026-07-01"}), "overdue")
            self.assertEqual(rental_status({"due_date": "2026-07-02"}), "active")
            self.assertEqual(rental_status({"due_date": "2026-07-03"}), "active")
            self.assertEqual(rental_status({"due_date": "2026-07-01", "return_date": "2026-07-02"}), "returned")

    def test_service_due_status_uses_thirty_day_date_boundary(self):
        with patch("worker.domain.today_iso", return_value="2026-07-02"):
            self.assertEqual(service_due_status(None), "ok")
            self.assertEqual(service_due_status("2026-07-01"), "overdue")
            self.assertEqual(service_due_status("2026-08-01"), "due_soon")
            self.assertEqual(service_due_status("2026-08-02"), "ok")

    def test_rental_makes_instrument_unavailable(self):
        create_record(self.records, self.tenant_id, "rentals", {
            "instrument_id": self.instrument["id"],
            "member_id": self.member["id"],
            "start_date": "2026-01-01",
        })

        hydrated = hydrate(self.records)

        self.assertEqual(hydrated["instruments"][0]["status"], "rented")
        self.assertEqual(summary(self.records)["active_rentals"], 1)

    def test_cannot_double_rent_active_instrument(self):
        create_record(self.records, self.tenant_id, "rentals", {
            "instrument_id": self.instrument["id"],
            "member_id": self.member["id"],
            "start_date": "2026-01-01",
        })

        with self.assertRaises(DomainError):
            create_record(self.records, self.tenant_id, "rentals", {
                "instrument_id": self.instrument["id"],
                "member_id": self.member["id"],
                "start_date": "2026-01-02",
            })

    def test_returned_rental_releases_instrument(self):
        rental = create_record(self.records, self.tenant_id, "rentals", {
            "instrument_id": self.instrument["id"],
            "member_id": self.member["id"],
            "start_date": "2026-01-01",
        })

        return_rental(self.records, self.tenant_id, rental["id"], {"return_date": "2026-01-03"})

        self.assertEqual(hydrate(self.records)["instruments"][0]["status"], "available")

    def test_prevent_deleting_member_with_active_rental(self):
        create_record(self.records, self.tenant_id, "rentals", {
            "instrument_id": self.instrument["id"],
            "member_id": self.member["id"],
            "start_date": "2026-01-01",
        })

        with self.assertRaises(DomainError):
            delete_record(self.records, "members", self.member["id"])

    def test_rental_update_validates_references(self):
        rental = create_record(self.records, self.tenant_id, "rentals", {
            "instrument_id": self.instrument["id"],
            "member_id": self.member["id"],
            "start_date": "2026-01-01",
        })

        with self.assertRaises(DomainError):
            update_record(self.records, self.tenant_id, "rentals", rental["id"], {
                "instrument_id": "missing",
            })

    def test_rental_update_can_clear_nullable_dates(self):
        rental = create_record(self.records, self.tenant_id, "rentals", {
            "instrument_id": self.instrument["id"],
            "member_id": self.member["id"],
            "start_date": "2026-01-01",
            "due_date": "2026-02-01",
            "return_date": "2026-01-20",
        })

        updated = update_record(self.records, self.tenant_id, "rentals", rental["id"], {
            "due_date": "",
            "return_date": "",
        })

        self.assertIsNone(updated["due_date"])
        self.assertIsNone(updated["return_date"])

    def test_service_record_updates_instrument_condition(self):
        service = create_record(self.records, self.tenant_id, "service_records", {
            "instrument_id": self.instrument["id"],
            "service_date": "2026-02-03",
            "condition": "needs_service",
            "next_service_date": "2026-07-03",
            "job_type": "Pad revision",
            "note": "Lower keys need adjustment",
        })

        hydrated = hydrate(self.records)

        self.assertEqual(service["condition"], "needs_service")
        self.assertEqual(service["next_service_date"], "2026-07-03")
        self.assertEqual(hydrated["instruments"][0]["service_condition"], "needs_service")
        self.assertEqual(hydrated["instruments"][0]["next_service_date"], "2026-07-03")
        self.assertEqual(hydrated["instruments"][0]["service_record_count"], 1)
        self.assertEqual(summary(self.records)["service_attention"], 1)
        self.assertEqual(self.records["history"][-1]["service_record_id"], service["id"])
        self.assertEqual(self.records["history"][-1]["service_condition"], "needs_service")

    def test_due_service_date_counts_as_service_attention(self):
        create_record(self.records, self.tenant_id, "service_records", {
            "instrument_id": self.instrument["id"],
            "service_date": "2026-02-03",
            "condition": "good",
            "next_service_date": "2000-01-01",
            "job_type": "General check",
        })

        hydrated = hydrate(self.records)

        self.assertEqual(hydrated["instruments"][0]["service_condition"], "good")
        self.assertEqual(hydrated["instruments"][0]["service_due_status"], "overdue")
        self.assertEqual(summary(self.records)["service_attention"], 1)

    def test_service_record_history_uses_service_context(self):
        service = create_record(self.records, self.tenant_id, "service_records", {
            "instrument_id": self.instrument["id"],
            "service_date": "2026-02-03",
            "condition": "watch",
            "job_type": "General check",
            "actor": "service-team",
        })

        created = self.records["history"][-1]
        self.assertEqual(created["action"], "created")
        self.assertEqual(created["actor"], "service-team")
        self.assertEqual(created["service_record_id"], service["id"])
        self.assertEqual(created["instrument_name"], "Tenor saxophone")

        update_record(self.records, self.tenant_id, "service_records", service["id"], {
            "condition": "good",
            "service_date": "2026-02-04",
            "actor": "workshop",
        })

        updated = self.records["history"][-1]
        self.assertEqual(updated["action"], "updated")
        self.assertEqual(updated["actor"], "workshop")
        self.assertEqual(updated["service_condition"], "good")
        self.assertEqual(updated["service_date"], "2026-02-04")

    def test_service_record_requires_known_instrument(self):
        with self.assertRaises(DomainError):
            create_record(self.records, self.tenant_id, "service_records", {
                "instrument_id": "missing",
                "condition": "good",
                "service_date": "2026-02-03",
            })

    def test_invalid_service_condition_is_rejected(self):
        with self.assertRaises(DomainError):
            create_record(self.records, self.tenant_id, "service_records", {
                "instrument_id": self.instrument["id"],
                "condition": "broken",
                "service_date": "2026-02-03",
            })

    def test_service_record_rejects_contact_like_notes(self):
        with self.assertRaisesRegex(DomainError, "provider must not contain email"):
            create_record(self.records, self.tenant_id, "service_records", {
                "instrument_id": self.instrument["id"],
                "service_date": "2026-02-03",
                "condition": "good",
                "provider": "workshop@example.test",
            })
        with self.assertRaisesRegex(DomainError, "note must not contain phone"):
            create_record(self.records, self.tenant_id, "service_records", {
                "instrument_id": self.instrument["id"],
                "service_date": "2026-02-03",
                "condition": "good",
                "note": "Call +41 44 000 00 00 after inspection",
            })

    def test_rental_note_rejects_contact_like_values(self):
        with self.assertRaisesRegex(DomainError, "note must not contain email"):
            create_record(self.records, self.tenant_id, "rentals", {
                "instrument_id": self.instrument["id"],
                "member_id": self.member["id"],
                "start_date": "2026-01-01",
                "note": "Contact person@example.test before pickup",
            })

    def test_instrument_description_rejects_contact_like_values(self):
        with self.assertRaisesRegex(DomainError, "description must not contain phone"):
            update_record(self.records, self.tenant_id, "instruments", self.instrument["id"], {
                "description": "Previous owner +41 44 000 00 00",
            })

    def test_export_import_preserves_service_records(self):
        create_record(self.records, self.tenant_id, "service_records", {
            "instrument_id": self.instrument["id"],
            "service_date": "2026-02-03",
            "condition": "watch",
            "next_service_date": "2026-08-03",
            "job_type": "General check",
        })

        package = export_package(self.records, self.tenant_id)
        imported = import_package(package, "next-association")

        self.assertEqual(len(imported["service_records"]), 1)
        self.assertEqual(imported["service_records"][0]["tenant_id"], "next-association")
        self.assertEqual(imported["service_records"][0]["instrument_id"], imported["instruments"][0]["id"])
        self.assertEqual(imported["service_records"][0]["next_service_date"], "2026-08-03")
        self.assertEqual(imported["history"][0]["service_record_id"], imported["service_records"][0]["id"])
        self.assertEqual(imported["history"][0]["service_condition"], "watch")

    def test_import_rejects_contact_like_history_actor(self):
        create_record(self.records, self.tenant_id, "rentals", {
            "instrument_id": self.instrument["id"],
            "member_id": self.member["id"],
            "start_date": "2026-01-01",
        })
        package = export_package(self.records, self.tenant_id)
        package["records"]["history"][0]["actor"] = "person@example.test"

        with self.assertRaisesRegex(DomainError, "actor must be opaque"):
            import_package(package, "next-association")

    def test_history_creation_rejects_contact_like_actor(self):
        with self.assertRaisesRegex(DomainError, "actor must be opaque"):
            create_record(self.records, self.tenant_id, "rentals", {
                "instrument_id": self.instrument["id"],
                "member_id": self.member["id"],
                "start_date": "2026-01-01",
                "actor": "+41 44 000 00 00",
            })

    def test_member_crud_rejects_blocked_contact_fields(self):
        with self.assertRaisesRegex(DomainError, "blocked PII fields"):
            create_record(self.records, self.tenant_id, "members", {
                "display_name": "Private Member",
                "email": "private@example.test",
            })

    def test_member_crud_rejects_email_and_phone_like_hints(self):
        with self.assertRaisesRegex(DomainError, "member_ref must not contain email"):
            create_record(self.records, self.tenant_id, "members", {
                "display_name": "Private Member",
                "member_ref": "private@example.test",
            })
        with self.assertRaisesRegex(DomainError, "contact_hint must not contain phone"):
            update_record(self.records, self.tenant_id, "members", self.member["id"], {
                "contact_hint": "+41 44 000 00 00",
            })


if __name__ == "__main__":
    unittest.main()
