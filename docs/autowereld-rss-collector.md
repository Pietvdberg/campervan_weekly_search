# Raspberry Pi AutoWereld collector

The Pi 3A+ was confirmed on 16 October 2026 to receive valid RSS from all
five feeds (15 items each). Python urllib requests failed, but curl returned
real XML despite the server incorrectly declaring `text/html`. AutoWereld
individual detail requests returned HTTP 403 and must not be bypassed.

## Repeatable installation (no secrets needed)

```bash
cd ~
git clone https://github.com/Pietvdberg/campervan_weekly_search.git
cd campervan_weekly_search
bash scripts/install_autowereld_pi.sh
systemctl --user start autowereld-rss.service
journalctl --user -u autowereld-rss.service -n 40 --no-pager
python3 - <<'PY'
import json
from pathlib import Path
d=json.loads(Path("data/autowereld_rss_snapshot.json").read_text())
print("RSS entries:",len(d["entries"]),"feeds:",len(d["feeds_checked"]))
print("Example title:",d["entries"][0]["title"])
PY
```

If the repo already exists, use `cd ~/campervan_weekly_search && git
pull --ff-only` instead of cloning.

The installer writes a systemd **user** service and weekly timer, but does
not enable the timer or set up GitHub credentials. The collector downloads
five public feeds only, using curl with no retries. Failed feeds cause the
command to fail without overwriting the previous good snapshot. If collection
is permitted and the manual test passes, you can enable **local collection**
with `systemctl --user enable --now autowereld-rss.timer`. For execution
while not logged in, `loginctl enable-linger piet` may be needed; verify
the effective timer schedule with `systemctl --user list-timers`.

## Optional GitHub handoff (separate explicit approval)

Create a fine-grained PAT scoped **only** to this repository with repository
**Contents: read/write**, and short expiration. Never place it in the Git
repository, terminal history, or screenshots. Set it in a private local
environment (for example, a root-owned environment file handed to an
unprivileged service). The uploader reads `GH_RSS_TOKEN` and uses the GitHub
Contents API:

```bash
python3 autowereld_upload.py data/autowereld_rss_snapshot.json
```

This replaces only `data/autowereld_rss_snapshot.json` in `main`. It does
**not** trigger workflow_dispatch or send email, and the development
integration workflow does not currently run automatically on data-only commits.
Manual uploads/dispatch should be tested first; do not automate credentials
or enable regular mail before the user approves.

## Evidence limits

The Pi's RSS snapshot contains first-party advert URL, title, description,
publication date, source feed and collection timestamp. It is verified as
**source-reported index data**, not as an independently verified live advert.
GitHub checks domain, URL shape, source feeds, freshness (48h), and content size.
RSS-only vehicles are shown separately as **UNVERIFIED leads**, never counted
as >=90% verified matches. VAT basis, route distance, actual vehicle condition
and listing availability remain unverified.

The daily/weekly production search remains disabled.

## Confirmed operational handover

The user-supplied session handover records that the Pi collector/upload timer was
already enabled for Thursday 13:30 Europe/Amsterdam, with linger enabled and a
successful 75-entry upload on 16 October 2026. Installation instructions above
remain instructions for a new host; they do not imply the existing Pi is disabled.
This review has not remotely inspected or changed that Pi. Production GitHub
weekly emailing remains a separate, unapproved activation.
