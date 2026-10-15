"""Ensure development runs never address the production-only recipient."""
import os
import unittest
from unittest.mock import patch
from send_report import configured_recipients

class MailRoutingTests(unittest.TestCase):
    def test_default_only_hotmail(self):
        with patch.dict(os.environ, {}, clear=True):
            mode, recipients = configured_recipients()
        self.assertEqual(mode, "development")
        self.assertEqual(recipients, ("piet.v.d.berg@hotmail.com",))

    def test_explicit_development_only_hotmail(self):
        with patch.dict(os.environ, {"MAIL_MODE": "development"}):
            _, recipients = configured_recipients()
        self.assertEqual(recipients, ("piet.v.d.berg@hotmail.com",))

    def test_explicit_production_has_both(self):
        with patch.dict(os.environ, {"MAIL_MODE": "production"}):
            _, recipients = configured_recipients()
        self.assertEqual(recipients, ("piet.v.d.berg@hotmail.com", "hagenaars.danielle@gmail.com"))

    def test_invalid_mode_fails_closed(self):
        with patch.dict(os.environ, {"MAIL_MODE": "prod"}):
            with self.assertRaises(ValueError):
                configured_recipients()

if __name__ == "__main__":
    unittest.main()
