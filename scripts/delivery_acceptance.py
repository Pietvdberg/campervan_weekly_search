"""Release-only live development check: interrupt after SMTP acceptance, then recover."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from delivery_store import Store
from send_report import deliver
from weekly_delivery import prepare, send_pending


class ExpectedInterruption(Exception):
    pass


def main():
    if os.environ.get("MAIL_MODE") != "development":
        raise RuntimeError("Acceptance test is development-only")
    repo, period = os.environ["GITHUB_REPOSITORY"], os.environ["DELIVERY_PERIOD"]
    sender = os.environ["GMAIL_SENDER"]
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    store = Store(repo, "development")
    if any(row["period"] == period for row in store.state["delivered"]):
        print("Acceptance report already confirmed; no resend")
        return
    if store.state["pending"]:
        send_pending(store, sender, password)
    if any(row["period"] == period for row in store.state["delivered"]):
        return
    prepare(store, json.loads(Path("screening_results.json").read_text()), period, sender)
    before = deepcopy(store.state["history"])
    frozen = deepcopy(store.state["pending"])
    Path("delivery_report.txt").write_text(frozen["text"], encoding="utf-8")
    Path("delivery_report.html").write_text(frozen["html"], encoding="utf-8")

    def interrupt_after_acceptance(message, sender, password, recipients, state, checkpoint):
        def durable_checkpoint(value):
            checkpoint(value)
            if value["status"] == "smtp_accepted":
                raise ExpectedInterruption("Deliberate interruption after durable SMTP acceptance")
        return deliver(message, sender, password, recipients, state, durable_checkpoint)

    with patch("weekly_delivery.deliver", side_effect=interrupt_after_acceptance):
        try:
            send_pending(store, sender, password)
        except ExpectedInterruption:
            print("Expected post-SMTP interruption observed; recovering from durable state")
        else:
            raise AssertionError("Expected fresh SMTP acceptance and interruption")
    if store.state["history"] != before:
        raise AssertionError("Unconfirmed email advanced delivery history")
    # A new object reloads remote state, just like another runner/run attempt.
    recovered = Store(repo, "development")
    if recovered.state["pending"]["mail_state"]["status"] != "smtp_accepted":
        raise AssertionError("SMTP checkpoint was not durably restored")
    with patch("send_report.smtplib.SMTP_SSL", side_effect=AssertionError("Recovery must never resubmit SMTP")):
        send_pending(recovered, sender, password)
        if prepare(recovered, {"results": []}, period, sender):
            raise AssertionError("Confirmed period was prepared again")
    receipt = recovered.state["delivered"][-1]
    Path("delivery_receipt.json").write_text(json.dumps({**receipt,
        "post_smtp_interruption_recovered": True, "second_smtp_submission": False,
        "audience": "development-only Hotmail"}, indent=2) + "\n")
    print("Live delivery acceptance passed:", json.dumps(receipt))


if __name__ == "__main__":
    main()
