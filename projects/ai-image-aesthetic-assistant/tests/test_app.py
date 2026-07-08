import unittest

from app import application


class AppTests(unittest.TestCase):
    def test_exports_wsgi_application(self):
        self.assertTrue(callable(application))


if __name__ == "__main__":
    unittest.main()
