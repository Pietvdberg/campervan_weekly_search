"""Delivery acknowledgement and recovery tests; no network or real
email.
"""

import json
import os
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from campervan_search.delivery_store import Store, empty_state
from campervan_search.send_report import compose_message
from campervan_search.weekly_delivery import prepare, send_pending
from campervan_search.weekly_schedule import CRONS, scheduled_period
from tests import test_search_history


class MemoryStore:
    mode = "development"

    def __init__(self):
        self.state = empty_state()
        self.saved = []

    def save(self, state):
        self.saved.append(deepcopy(state))
        self.state = deepcopy(state)


class WeeklyDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        env = patch.dict(os.environ, {"MAIL_MODE": "development"})
        env.start()
        self.addCleanup(env.stop)
        self.data = test_search_history.HistoryTests().data()
        self.sender = "sender@example.test"

    def prepare(self, period="2026-10-22", data=None):
        return prepare(
            self.store, data or self.data, period, self.sender, "2026-10-22"
        )

    def confirm(
        self, message, sender, password, recipients, state, checkpoint
    ):
        checkpoint(
            {"message_id": message["Message-ID"], "status": "sent_confirmed"}
        )

    def test_search_observations_do_not_suppress_first_delivery(self):
        from campervan_search.search_history import empty_state as history
        from campervan_search.search_history import update

        seen, observed = update(self.data, history(), "push-1")
        seen, observed = update(self.data, observed, "push-2")
        self.assertFalse(seen["results"][0]["history"]["show_in_digest"])
        self.prepare(data=seen)
        self.assertIn("Synthetic van", self.store.state["pending"]["text"])
        self.assertEqual(self.store.state["history"]["listings"], {})

    def test_failure_does_not_acknowledge_and_recovers_exact_frozen_content(
        self,
    ):
        self.prepare()
        frozen = deepcopy(self.store.state["pending"])

        def interrupted(
            message, sender, password, recipients, state, checkpoint
        ):
            checkpoint(
                {
                    "message_id": message["Message-ID"],
                    "status": "smtp_accepted",
                }
            )
            raise OSError("Runner lost after SMTP acceptance")

        with (
            patch(
                "campervan_search.weekly_delivery.deliver",
                side_effect=interrupted,
            ),
            self.assertRaises(OSError),
        ):
            send_pending(self.store, self.sender, "synthetic")
        self.assertEqual(self.store.state["history"]["listings"], {})
        self.assertEqual(
            self.store.state["pending"]["mail_state"]["status"],
            "smtp_accepted",
        )
        with (
            patch("campervan_search.send_report.smtplib.SMTP_SSL") as smtp,
            patch(
                "campervan_search.send_report.verify_sent", return_value=True
            ),
            patch(
                "campervan_search.weekly_delivery.render_html",
                side_effect=AssertionError("Must not rerender"),
            ),
        ):
            self.assertTrue(send_pending(self.store, self.sender, "synthetic"))
            smtp.assert_not_called()
        self.assertIsNone(self.store.state["pending"])
        self.assertTrue(self.store.state["history"]["listings"])
        self.assertFalse(self.prepare())
        self.assertEqual(
            self.store.state["delivered"][0]["message_id"],
            compose_message(
                frozen["text"],
                frozen["html"],
                frozen["date"],
                self.sender,
                frozen["mode"],
                tuple(frozen["recipients"]),
            )["Message-ID"],
        )

    def test_more_than_five_leads_only_displayed_leads_are_acknowledged(self):
        data = deepcopy(self.data)
        data["results"] = []
        for i in range(7):
            item = deepcopy(self.data["results"][0])
            item["plate"] = None
            item["candidate"].update(
                plate=None,
                plate_confirmed_from_listing=False,
                listing_url=f"https://example.test/van-{i}",
                name=f"Synthetic van {i}",
            )
            data["results"].append(item)
        self.prepare(data=data)
        with patch(
            "campervan_search.weekly_delivery.deliver",
            side_effect=self.confirm,
        ):
            send_pending(self.store, self.sender, "synthetic")
        self.assertEqual(len(self.store.state["history"]["listings"]), 5)
        self.prepare("2026-10-29", data)
        text = self.store.state["pending"]["text"]
        self.assertIn("Synthetic van 5", text)
        self.assertIn("Synthetic van 6", text)
        self.assertNotIn("  Listing: https://example.test/van-0\n", text)

    def test_checkpoint_failure_prevents_smtp_data(self):
        self.prepare()
        with (
            patch(
                "campervan_search.send_report.verify_sent", return_value=False
            ),
            patch("campervan_search.send_report.smtplib.SMTP_SSL") as smtp,
        ):
            with (
                patch.object(
                    self.store,
                    "save",
                    side_effect=OSError("GitHub unavailable"),
                ),
                self.assertRaises(OSError),
            ):
                send_pending(self.store, self.sender, "synthetic")
            connection = smtp.return_value.__enter__.return_value
            connection.send_message.assert_not_called()

    def test_definite_pre_submission_failure_can_retry(self):
        self.prepare()
        with (
            patch(
                "campervan_search.send_report.verify_sent",
                side_effect=OSError("IMAP offline"),
            ),
            self.assertRaises(OSError),
        ):
            send_pending(self.store, self.sender, "synthetic")
        self.assertIsNone(self.store.state["pending"]["mail_state"])
        with patch(
            "campervan_search.weekly_delivery.deliver",
            side_effect=self.confirm,
        ):
            send_pending(self.store, self.sender, "synthetic")
        self.assertIsNone(self.store.state["pending"])

    def test_pending_report_blocks_replacement_and_changed_audience(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "Recover"):
            self.prepare("2026-10-29")
        with (
            patch.dict(os.environ, {"MAIL_MODE": "production"}),
            patch("campervan_search.weekly_delivery.deliver") as send,
        ):
            with self.assertRaisesRegex(ValueError, "audience"):
                send_pending(self.store, self.sender, "synthetic")
            send.assert_not_called()

    def test_sent_confirmation_without_durable_ack_is_recoverable(self):
        self.prepare()
        real_save = self.store.save

        def save(state):
            if state["pending"] is None:
                raise OSError("Lost before history commit")
            real_save(state)

        with (
            patch.object(self.store, "save", side_effect=save),
            patch(
                "campervan_search.weekly_delivery.deliver",
                side_effect=self.confirm,
            ),
            self.assertRaises(OSError),
        ):
            send_pending(self.store, self.sender, "synthetic")
        self.assertEqual(
            self.store.state["pending"]["mail_state"]["status"],
            "sent_confirmed",
        )
        self.assertEqual(self.store.state["history"]["listings"], {})
        with (
            patch("campervan_search.send_report.smtplib.SMTP_SSL") as smtp,
            patch(
                "campervan_search.send_report.verify_sent", return_value=True
            ),
        ):
            send_pending(self.store, self.sender, "synthetic")
            smtp.assert_not_called()


class DeliveryStoreTests(unittest.TestCase):
    def test_failed_compare_and_swap_never_updates_local_head(self):
        def request(repo, path, method="GET", data=None):
            if path.startswith("git/ref/"):
                raise HTTPError("test", 404, "missing", {}, None)
            if path == "git/refs":
                raise HTTPError("test", 422, "another writer won", {}, None)
            return {"sha": "created"}

        store = Store("owner/repo", "production", request)
        with self.assertRaises(HTTPError):
            store.save(empty_state())
        self.assertIsNone(store.head)

    def test_existing_broken_branch_is_not_reset(self):
        def request(repo, path, *args):
            if path.startswith("git/ref/"):
                return {"object": {"sha": "head"}}
            if path.startswith("git/commits/"):
                return {"tree": {"sha": "tree"}}
            return {"tree": []}

        with self.assertRaisesRegex(ValueError, "unique state"):
            Store("owner/repo", "production", request)

    def test_other_writer_is_not_overwritten(self):
        def request(repo, path, *args):
            raise HTTPError("test", 404, "missing", {}, None)

        store = Store("owner/repo", "production", request)
        store.request = lambda *args: {"object": {"sha": "other"}}
        with self.assertRaisesRegex(ValueError, "advanced"):
            store.save(empty_state())


class ScheduleTests(unittest.TestCase):
    def test_both_sides_of_dst_and_delayed_start(self):
        for date, expected in (
            ("2026-03-26", CRONS[1]),
            ("2026-04-02", CRONS[0]),
            ("2026-10-22", CRONS[0]),
            ("2026-10-29", CRONS[1]),
        ):
            now = datetime.fromisoformat(date + "T18:30:00+00:00")
            self.assertEqual(scheduled_period(expected, now), date)
            other = next(cron for cron in CRONS if cron != expected)
            self.assertIsNone(scheduled_period(other, now))

    def test_invalid_time_and_non_thursday_are_not_production_runs(self):
        self.assertIsNone(
            scheduled_period(
                CRONS[0], datetime.fromisoformat("2026-10-17T13:00:00+00:00")
            )
        )
        with self.assertRaises(ValueError):
            scheduled_period(
                "unreviewed cron",
                datetime.fromisoformat("2026-10-22T13:00:00+00:00"),
            )
        with self.assertRaises(ValueError):
            scheduled_period(CRONS[0], datetime(2026, 10, 22))

    def plan(self, kind, event):
        from campervan_search import weekly_schedule

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls.fromisoformat(
                    "2026-10-29T15:02:00+00:00"
                ).astimezone(tz)

        with tempfile.TemporaryDirectory() as folder:
            event_file, output_file = Path(folder, "event.json"), Path(
                folder, "output"
            )
            event_file.write_text(json.dumps(event))
            with (
                patch.dict(
                    os.environ,
                    {
                        "GITHUB_EVENT_NAME": kind,
                        "GITHUB_EVENT_PATH": str(event_file),
                        "GITHUB_OUTPUT": str(output_file),
                        "GITHUB_RUN_ID": "123",
                        "GITHUB_REPOSITORY": "owner/repo",
                    },
                ),
                patch.object(weekly_schedule, "datetime", Clock),
                patch.object(
                    weekly_schedule,
                    "api",
                    return_value={"created_at": "2026-10-22T13:00:00Z"},
                ),
            ):
                weekly_schedule.main()
            return dict(
                line.split("=", 1)
                for line in output_file.read_text().splitlines()
            )

    def test_scheduled_rerun_after_dst_preserves_original_production_period(
        self,
    ):
        self.assertEqual(
            self.plan("schedule", {"schedule": CRONS[0]}),
            {"enabled": "true", "mode": "production", "period": "2026-10-22"},
        )

    def test_other_dst_trigger_disables_delivery(self):
        self.assertEqual(
            self.plan("schedule", {"schedule": CRONS[1]})["enabled"], "false"
        )

    def test_manual_event_cannot_select_production_audience(self):
        self.assertEqual(
            self.plan("workflow_dispatch", {"inputs": {"mode": "production"}}),
            {
                "enabled": "true",
                "mode": "development",
                "period": "development-123",
            },
        )
