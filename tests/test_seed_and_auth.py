import os
import tempfile
import unittest

from db import connect
from seed import hash_password, seed


class SeedAndAuthTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        seed(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_seed_creates_expected_users(self):
        with connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        self.assertEqual(count, 4)

    def test_hash_password_is_deterministic(self):
        self.assertEqual(hash_password("abc123"), hash_password("abc123"))
        self.assertNotEqual(hash_password("abc123"), hash_password("abc124"))


if __name__ == "__main__":
    unittest.main()
