"""Freeze, submit and acknowledge a digest independently of search observations."""
import argparse
from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from camper_pipeline import report, report_selection
from delivery_store import Store
from report_html import render_html
from search_history import update
from send_report import compose_message, configured_recipients, deliver


def prepare(store, screening, period, sender, date=None):
    if store.state["pending"] is not None:
        raise ValueError("Recover the pending report before preparing another")
    if any(row["period"] == period for row in store.state["delivered"]):
        return False
    mode, recipients = configured_recipients()
    if mode != store.mode:
        raise ValueError("Delivery store audience differs from mail mode")
    date = date or datetime.now(ZoneInfo("Europe/Amsterdam")).date().isoformat()
    data = deepcopy(screening)
    data.pop("report_context", None)
    data["generated_on"] = date
    data, _ = update(data, store.state["history"], period)
    # Health describes observations, not how many leads fit in the delivered email.
    data["coverage_health"] = screening.get("coverage_health", data.get("coverage_health", {}))
    selection = report_selection(data)
    shown = selection["qualified"] + selection["potential"]
    _, acknowledged = update({**data, "results": shown}, store.state["history"], period)
    state = deepcopy(store.state)
    state["pending"] = {"period": period, "date": date, "sender": sender, "mode": mode,
        "recipients": list(recipients), "text": report(data), "html": render_html(data),
        "history": acknowledged, "mail_state": None}
    store.save(state)
    return True


def send_pending(store, sender, password, audit_directory=None):
    pending = store.state["pending"]
    if pending is None:
        return False
    mode, recipients = configured_recipients()
    if pending["mode"] != mode or mode != store.mode or pending["sender"] != sender or pending["recipients"] != list(recipients):
        raise ValueError("Frozen report audience changed; refusing submission")
    message = compose_message(pending["text"], pending["html"], pending["date"], sender, mode, recipients)
    if audit_directory is not None:
        Path(audit_directory, "delivery_report.txt").write_text(pending["text"], encoding="utf-8")
        Path(audit_directory, "delivery_report.html").write_text(pending["html"], encoding="utf-8")

    def checkpoint(mail_state):
        state = deepcopy(store.state)
        state["pending"]["mail_state"] = mail_state
        store.save(state)

    deliver(message, sender, password, recipients, pending["mail_state"], checkpoint)
    confirmed = store.state["pending"]["mail_state"]
    if confirmed is None or confirmed["status"] != "sent_confirmed":
        raise RuntimeError("Cannot acknowledge an unconfirmed report")
    state = deepcopy(store.state)
    state["history"] = state["pending"]["history"]
    state["delivered"] = (state["delivered"] + [{"period": pending["period"],
        "message_id": confirmed["message_id"], "confirmed_at": datetime.now(ZoneInfo("UTC")).isoformat()}])[-60:]
    state["pending"] = None
    store.save(state)
    if audit_directory is not None:
        Path(audit_directory, "delivery_receipt.json").write_text(json.dumps(state["delivered"][-1], indent=2) + "\n")
    print("Report confirmed; displayed listings acknowledged for", pending["period"], flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("recover", "send"))
    parser.add_argument("--repo", required=True)
    parser.add_argument("--period", required=True)
    parser.add_argument("--screening", default="screening_results.json")
    args = parser.parse_args()
    mode, _ = configured_recipients()
    store = Store(args.repo, mode)
    sender = os.environ["GMAIL_SENDER"]
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    if args.action == "recover":
        send_pending(store, sender, password, audit_directory=".")
        completed = any(row["period"] == args.period for row in store.state["delivered"])
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as output:
                output.write("already-delivered=" + str(completed).lower() + "\n")
        return
    # A different workflow/run may have left an outbox; always recover it first.
    send_pending(store, sender, password, audit_directory=".")
    if any(row["period"] == args.period for row in store.state["delivered"]):
        print("This reporting period was already delivered; no resend")
        return
    if prepare(store, json.loads(Path(args.screening).read_text()), args.period, sender):
        send_pending(store, sender, password, audit_directory=".")
    else:
        print("This reporting period was already delivered; no resend")


if __name__ == "__main__":
    main()
