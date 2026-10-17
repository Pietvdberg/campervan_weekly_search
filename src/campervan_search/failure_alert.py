"""Send owner-only failure alerts; create a GitHub issue if email is
unavailable.
"""

import argparse
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from campervan_search.send_report import (
    DEV_RECIPIENTS,
    compose_message,
    deliver,
)
from campervan_search.state_store import api


def notify(repo, run_id, sender, password, test=False, request=api):
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}"
    title = (
        (
            "Recovery notification test"
            if test
            else "Weekly camper search failed"
        )
        + " — run "
        + run_id
    )
    text = (
        (
            "This is the expected production-readiness alert test. The search"
            " report was recovered after a deliberate post-SMTP interruption."
            if test
            else (
                "The weekly camper search or report delivery failed. Review"
                " this run before assuming a report was delivered. Pending"
                " reports remain saved; rerun the failed workflow to recover"
                " them."
            )
        )
        + "\n\n"
        + run_url
        + "\n"
    )
    date = (
        datetime.now(ZoneInfo("Europe/Amsterdam")).date().isoformat()
        + " — "
        + title
    )
    try:
        message = compose_message(
            text, None, date, sender, "development", DEV_RECIPIENTS
        )
        deliver(message, sender, password, DEV_RECIPIENTS)
        print("Owner-only alert confirmed in Gmail Sent:", run_url)
        return "email"
    except Exception as exc:
        print(
            "::warning::Failure alert email unavailable; creating a GitHub"
            " issue (" + type(exc).__name__ + ")"
        )
        # Same-run reruns should not open multiple failure issues.
        issues = request(repo, "issues?state=open&per_page=100")
        existing = next(
            (issue for issue in issues if issue.get("title") == title), None
        )
        if existing is None:
            request(repo, "issues", "POST", {"title": title, "body": text})
        print("Failure recorded as a GitHub issue:", run_url)
        if test:
            raise RuntimeError(
                "Notification email acceptance failed; fallback issue created"
            ) from exc
        return "issue"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    notify(
        os.environ["GITHUB_REPOSITORY"],
        os.environ["GITHUB_RUN_ID"],
        os.environ.get("GMAIL_SENDER", ""),
        os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", ""),
        args.test,
    )


if __name__ == "__main__":
    main()
