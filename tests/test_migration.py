import unittest

from worker.domain import empty_records, import_package
from worker.migration import (
    hitobito_members_to_records,
    instrument_export_package,
    legacy_to_package,
    merge_hitobito_members,
    merge_instruments,
)


class LegacyMigrationTests(unittest.TestCase):
    def test_legacy_customer_pii_is_omitted_and_package_is_importable(self):
        package = legacy_to_package({
            "instruments": [{
                "id": 10,
                "Name": "Concert flute",
                "Brand": "Yamaha",
                "Type": "Flute",
                "Serial": "FL-10",
                "Price": "1200",
            }],
            "customers": [{
                "id": 20,
                "firstname": "Riley",
                "lastname": "Example",
                "email": "riley@example.test",
                "phone": "+41 00 000 00 00",
                "external_id": "M-20",
            }],
            "rentals": [{
                "id": 30,
                "Instrument ID": 10,
                "Customer ID": 20,
                "Start Date": "2026-01-01",
                "End Date": "2026-02-01",
                "Description": "Legacy loan",
            }],
        }, "tenant-new")

        self.assertEqual(package["schema"], "association-rental")
        self.assertEqual(package["summary"]["instruments"], 1)
        self.assertEqual(package["records"]["members"][0]["display_name"], "Riley Example")
        self.assertNotIn("email", package["records"]["members"][0])
        self.assertNotIn("phone", package["records"]["members"][0])
        self.assertEqual(package["records"]["rentals"][0]["instrument_id"], "inst_legacy_10")
        self.assertEqual(package["records"]["rentals"][0]["member_id"], "mem_legacy_20")
        self.assertEqual(package["migration"]["pii_fields_omitted"], [
            {"field": "email", "count": 1},
            {"field": "phone", "count": 1},
        ])

        imported = import_package(package, "tenant-new")
        self.assertEqual(imported["members"][0]["tenant_id"], "tenant-new")

    def test_legacy_rental_with_unknown_reference_fails(self):
        with self.assertRaisesRegex(Exception, "unknown member"):
            legacy_to_package({
                "instruments": [{"id": 1, "name": "Horn", "serial": "H-1"}],
                "customers": [],
                "rentals": [{
                    "id": 3,
                    "instrument_id": 1,
                    "customer_id": 99,
                    "start_date": "2026-01-01",
                }],
            }, "tenant-new")

    def test_legacy_rental_contact_note_is_omitted_and_package_is_importable(self):
        package = legacy_to_package({
            "instruments": [{"id": 10, "name": "Concert flute", "serial": "FL-10"}],
            "customers": [{"id": 20, "display_name": "Riley Example"}],
            "rentals": [{
                "id": 30,
                "instrument_id": 10,
                "customer_id": 20,
                "start_date": "2026-01-01",
                "description": "Call +41 44 000 00 00 before pickup",
            }],
        }, "tenant-new")

        self.assertIsNone(package["records"]["rentals"][0]["note"])
        self.assertIn({"field": "rental_note_contact", "count": 1}, package["migration"]["pii_fields_omitted"])

        imported = import_package(package, "tenant-new")
        self.assertIsNone(imported["rentals"][0]["note"])

    def test_legacy_instrument_contact_description_is_omitted(self):
        package = legacy_to_package({
            "instruments": [{
                "id": 10,
                "name": "Concert flute",
                "serial": "FL-10",
                "description": "Donated by person@example.test",
            }],
            "customers": [],
            "rentals": [],
        }, "tenant-new")

        self.assertIsNone(package["records"]["instruments"][0]["description"])
        self.assertIn(
            {"field": "instrument_description_contact", "count": 1},
            package["migration"]["pii_fields_omitted"],
        )

    def test_hitobito_json_api_members_are_low_pii_records(self):
        members, report = hitobito_members_to_records({
            "data": [{
                "id": "123",
                "attributes": {
                    "first_name": "Jamie",
                    "last_name": "Example",
                    "email": "jamie@example.test",
                    "phone": "+41 00 000 00 00",
                    "status": "active",
                },
                "relationships": {
                    "groups": {"data": [{"id": "brass"}, {"id": "committee"}]}
                },
            }]
        }, "tenant-new")

        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]["display_name"], "Jamie Example")
        self.assertEqual(members[0]["member_ref"], "hitobito:123")
        self.assertEqual(members[0]["groups"], ["brass", "committee"])
        self.assertNotIn("email", members[0])
        self.assertNotIn("phone", members[0])
        self.assertEqual(report["pii_fields_omitted"], [
            {"field": "email", "count": 1},
            {"field": "phone", "count": 1},
        ])

    def test_hitobito_merge_updates_by_member_ref_and_preserves_id(self):
        records = empty_records()
        records["members"].append({
            "id": "mem_existing",
            "tenant_id": "tenant-new",
            "display_name": "Old Name",
            "given_name": "Old",
            "family_name": "Name",
            "member_ref": "hitobito:123",
            "contact_hint": "old roster",
            "groups": [],
            "is_active": True,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        })

        report = merge_hitobito_members(records, "tenant-new", {
            "people": [
                {"id": "123", "first_name": "New", "last_name": "Name", "groups": ["woodwind"]},
                {"id": "456", "display_name": "Fresh Member", "state": "archived"},
            ]
        })

        self.assertEqual(report["created"], 1)
        self.assertEqual(report["updated"], 1)
        self.assertEqual(records["members"][0]["id"], "mem_existing")
        self.assertEqual(records["members"][0]["display_name"], "New Name")
        self.assertEqual(records["members"][0]["groups"], ["woodwind"])
        self.assertEqual(records["members"][1]["member_ref"], "hitobito:456")
        self.assertFalse(records["members"][1]["is_active"])

    def test_instrument_export_package_contains_inventory_only(self):
        records = empty_records()
        records["instruments"].append({
            "id": "inst_1",
            "tenant_id": "tenant-new",
            "name": "Concert Flute",
            "brand": "Yamaha",
            "type": "Flute",
            "serial": "FL-1",
            "description": None,
            "value_chf": 1200.0,
            "purchase_year": 2020,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        })
        records["members"].append({"id": "mem_1", "tenant_id": "tenant-new", "display_name": "Hidden Member"})

        package = instrument_export_package(records, "tenant-new")

        self.assertEqual(package["schema"], "association-rental-instruments")
        self.assertEqual(package["summary"]["instruments"], 1)
        self.assertEqual([item["serial"] for item in package["records"]["instruments"]], ["FL-1"])
        self.assertNotIn("members", package["records"])

    def test_instrument_merge_updates_by_serial_and_preserves_id(self):
        records = empty_records()
        records["instruments"].append({
            "id": "inst_existing",
            "tenant_id": "tenant-new",
            "name": "Old Flute",
            "brand": "Yamaha",
            "type": "Flute",
            "serial": "FL-1",
            "description": None,
            "value_chf": 1000.0,
            "purchase_year": 2019,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        })

        report = merge_instruments(records, "tenant-new", {
            "records": {
                "instruments": [
                    {"name": "Updated Flute", "brand": "Yamaha", "type": "Flute", "serial": "FL-1", "value_chf": 1400},
                    {"name": "New Trumpet", "brand": "Bach", "type": "Trumpet", "serial": "TR-9"},
                ]
            }
        })

        self.assertEqual(report["created"], 1)
        self.assertEqual(report["updated"], 1)
        self.assertEqual(records["instruments"][0]["id"], "inst_existing")
        self.assertEqual(records["instruments"][0]["name"], "Updated Flute")
        self.assertEqual(records["instruments"][0]["value_chf"], 1400.0)
        self.assertEqual(records["instruments"][1]["serial"], "TR-9")

    def test_instrument_merge_rejects_contact_pii_fields(self):
        records = empty_records()

        with self.assertRaisesRegex(Exception, "blocked PII fields"):
            merge_instruments(records, "tenant-new", {
                "instruments": [{
                    "name": "Private Donation Clarinet",
                    "serial": "CL-1",
                    "email": "donor@example.test",
                }]
            })


if __name__ == "__main__":
    unittest.main()
