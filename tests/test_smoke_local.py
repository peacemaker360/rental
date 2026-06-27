import unittest

from scripts import smoke_local


class LocalSmokeTests(unittest.TestCase):
    def test_local_smoke_script_is_importable(self):
        self.assertTrue(callable(smoke_local.run_smoke))


if __name__ == "__main__":
    unittest.main()
