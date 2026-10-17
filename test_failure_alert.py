import unittest
from unittest.mock import Mock, patch

from failure_alert import notify
from send_report import DEV_RECIPIENTS


class AlertTests(unittest.TestCase):
    def test_alert_uses_only_owner_and_contains_run_link(self):
        with patch("failure_alert.deliver") as send:
            self.assertEqual(notify("owner/repo", "123", "sender@example.test", "synthetic"), "email")
        message, sender, password, recipients = send.call_args.args
        self.assertEqual(recipients, DEV_RECIPIENTS)
        self.assertIn("https://github.com/owner/repo/actions/runs/123", message.get_content())

    def test_email_failure_creates_issue_once(self):
        request = Mock(return_value=[])
        with patch("failure_alert.deliver", side_effect=OSError("SMTP unavailable")):
            self.assertEqual(notify("owner/repo", "123", "sender@example.test", "synthetic", request=request), "issue")
        self.assertEqual(request.call_count, 2)
        body = request.call_args.args[3]
        self.assertIn("123", body["title"])
        request.reset_mock()
        request.return_value = [body]
        with patch("failure_alert.deliver", side_effect=OSError("SMTP unavailable")):
            notify("owner/repo", "123", "sender@example.test", "synthetic", request=request)
        request.assert_called_once()

    def test_email_acceptance_cannot_pass_using_issue_fallback(self):
        with patch("failure_alert.deliver", side_effect=OSError("SMTP unavailable")), self.assertRaisesRegex(RuntimeError, "acceptance failed"):
            notify("owner/repo", "123", "sender@example.test", "synthetic", test=True, request=Mock(return_value=[]))
