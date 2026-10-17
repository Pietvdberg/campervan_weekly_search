import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import send_report


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.report = Path(self.temp.name) / "report.txt"
        self.report.write_text("Synthetic delivery test; no real email")
        self.state = self.report.with_name("mail_delivery_state.json")
        for target, value in (("sys.argv", ["send_report.py", str(self.report)]),):
            mock = patch(target, value)
            mock.start()
            self.addCleanup(mock.stop)
        env = patch.dict(os.environ, {"GMAIL_SENDER": "sender@example.test", "GMAIL_APP_PASSWORD": "synthetic", "REPORT_DATE": "2026-10-17", "MAIL_MODE": "development", "MAIL_DELIVERY_STATE": str(self.state)})
        env.start()
        self.addCleanup(env.stop)
        self.smtp_patch = patch("send_report.smtplib.SMTP_SSL")
        self.smtp = self.smtp_patch.start()
        self.smtp.return_value.__enter__.return_value.send_message.return_value = {}
        self.addCleanup(self.smtp_patch.stop)
        sleeper = patch("send_report.time.sleep")
        sleeper.start()
        self.addCleanup(sleeper.stop)
        output = patch("sys.stdout", new_callable=io.StringIO)
        output.start()
        self.addCleanup(output.stop)

    def test_new_message_persists_submission_and_confirmation(self):
        with patch("send_report.verify_sent", side_effect=[False, True]):
            self.assertEqual(send_report.main(), 0)
        self.assertEqual(json.loads(self.state.read_text())["status"], "sent_confirmed")
        self.smtp.assert_called_once()

    def test_accepted_but_unconfirmed_rerun_never_resends(self):
        with patch("send_report.verify_sent", return_value=False), self.assertRaises(RuntimeError):
            send_report.main()
        self.assertEqual(json.loads(self.state.read_text())["status"], "smtp_accepted")
        self.smtp.reset_mock()
        with patch("send_report.verify_sent", return_value=False), self.assertRaises(RuntimeError):
            send_report.main()
        self.smtp.assert_not_called()

    def test_ambiguous_smtp_exception_never_resends(self):
        self.smtp.return_value.__enter__.return_value.send_message.side_effect = OSError("connection lost after DATA")
        with patch("send_report.verify_sent", return_value=False), self.assertRaises(OSError):
            send_report.main()
        self.assertEqual(json.loads(self.state.read_text())["status"], "submitting")
        self.smtp.reset_mock()
        with patch("send_report.verify_sent", side_effect=[False, True]):
            self.assertEqual(send_report.main(), 0)
        self.smtp.assert_not_called()

    def test_existing_sent_message_prevents_new_submission(self):
        with patch("send_report.verify_sent", return_value=True):
            self.assertEqual(send_report.main(), 0)
        self.smtp.assert_not_called()

    def test_changed_content_with_restored_state_is_blocked(self):
        with patch("send_report.verify_sent", return_value=True):
            send_report.main()
        self.report.write_text("Different report")
        with patch("send_report.verify_sent"), self.assertRaisesRegex(RuntimeError, "different report"):
            send_report.main()
        self.smtp.assert_not_called()

    def test_imap_unavailable_does_not_trigger_smtp(self):
        with patch("send_report.verify_sent", side_effect=OSError("IMAP unavailable")), self.assertRaises(OSError):
            send_report.main()
        self.smtp.assert_not_called()

    def test_sent_folder_found_by_special_use_flag(self):
        self.assertEqual(send_report.sent_folder_from_list([b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Verzonden"']), "[Gmail]/Verzonden")
