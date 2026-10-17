"""Select the UTC Thursday trigger corresponding to 15:00 Amsterdam, including DST."""
from datetime import datetime, time, timezone
import json
import os
from zoneinfo import ZoneInfo

from state_store import api

CRONS = ("0 13 * * 4", "0 14 * * 4")


def scheduled_period(cron, now):
    if now.tzinfo is None:
        raise ValueError("Schedule evaluation requires an aware timestamp")
    if cron not in CRONS:
        raise ValueError("Unknown production cron")
    local = now.astimezone(ZoneInfo("Europe/Amsterdam"))
    if local.weekday() != 3:
        return None
    intended = datetime.combine(local.date(), time(15), ZoneInfo("Europe/Amsterdam"))
    expected_hour = intended.astimezone(timezone.utc).hour
    # Use the triggering cron, not a narrow wall-clock window: delayed runners work.
    return local.date().isoformat() if int(cron.split()[1]) == expected_hour else None


def main():
    with open(os.environ["GITHUB_EVENT_PATH"]) as stream:
        event = json.load(stream)
    kind = os.environ["GITHUB_EVENT_NAME"]
    if kind == "schedule":
        # created_at belongs to the original run, even if rerun on another day
        # or after a DST transition. Today's date would silently skip recovery.
        run = api(os.environ["GITHUB_REPOSITORY"], "actions/runs/" + os.environ["GITHUB_RUN_ID"])
        created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        period = scheduled_period(event["schedule"], created)
        mode = "production"
    else:
        period = "development-" + os.environ["GITHUB_RUN_ID"]
        mode = "development"
    output = "enabled=" + str(period is not None).lower() + "\nmode=" + mode + "\nperiod=" + (period or "") + "\n"
    with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
        stream.write(output)
    print(output, end="")


if __name__ == "__main__":
    main()
