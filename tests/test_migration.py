import unittest

from worker.domain import import_package
from worker.migration import legacy_to_package


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


if __name__ == "__main__":
    unittest.main()
