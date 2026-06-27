import unittest

from worker.domain import (
    DomainError,
    create_record,
    delete_record,
    empty_records,
    hydrate,
    return_rental,
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


if __name__ == "__main__":
    unittest.main()
