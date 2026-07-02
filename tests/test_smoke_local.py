import unittest

from scripts import smoke_local


class LocalSmokeTests(unittest.TestCase):
    def test_local_smoke_script_is_importable(self):
        self.assertTrue(callable(smoke_local.run_smoke))
        self.assertTrue(callable(smoke_local.run_signed_smoke))

    def test_local_smoke_flow_passes(self):
        try:
            smoke_local.run_smoke()
        except PermissionError as exc:
            self.skipTest(f"local socket unavailable in this test sandbox: {exc}")

    def test_signed_local_smoke_flow_passes(self):
        try:
            smoke_local.run_signed_smoke()
        except PermissionError as exc:
            self.skipTest(f"local socket unavailable in this test sandbox: {exc}")


if __name__ == "__main__":
    unittest.main()
