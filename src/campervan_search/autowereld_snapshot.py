"""Opt-in, offline AutoWereld RSS collector and validated index-only
handoff.

Run on a computer where the *public* RSS works, if permitted by
AutoWereld.
No authentication, proxies, CAPTCHA solving, or access-control
circumvention.
A snapshot contains only public advert links and titles; it is never
proof of
listing availability, VAT basis, driving distance, or mechanical
condition.
"""

import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

from campervan_search.source_catalog import VAN_MODEL as MODEL

FEEDS = (
    "https://www.autowereld.nl/rss/peugeot/boxer/",
    "https://www.autowereld.nl/rss/ford/transit/",
    "https://www.autowereld.nl/rss/citroen/jumper/",
    "https://www.autowereld.nl/rss/fiat/ducato/",
    "https://www.autowereld.nl/rss/renault/master/",
)
DETAIL = re.compile(
    r"/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+-\d+/details\.html$", re.I
)

MAX_ITEMS = 250
MAX_AGE = timedelta(hours=48)


def valid_advert(url, title=""):
    p = urlparse(url)
    return (
        p.scheme == "https"
        and p.hostname in ("autowereld.nl", "www.autowereld.nl")
        and not p.query
        and not p.fragment
        and bool(DETAIL.fullmatch(p.path))
        and bool(MODEL.search(title + " " + p.path.replace("-", " ")))
    )


def parse_rss(xml):
    root = ElementTree.fromstring(xml)
    if root.tag.lower() != "rss":
        raise ValueError("AutoWereld returned non-RSS; cannot create snapshot")
    result = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()[:220]
        link = (item.findtext("link") or "").strip()
        if valid_advert(link, title):
            description = (item.findtext("description") or "").strip()[:1800]
            result.append(
                {
                    "url": link,
                    "title": title,
                    "description": description,
                    "pub_date": (item.findtext("pubDate") or "")[:100],
                }
            )
    return result


def collect(fetcher=None, now=None):
    if fetcher is None:

        def fetcher(url):
            # curl receives genuine RSS on the tested Raspberry Pi;
            # urllib did
            # not.
            # One bounded request per public feed, without retries or
            # access
            # bypass.
            cmd = [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--location",
                "--max-time",
                "20",
                "--max-filesize",
                "1048576",
                "--header",
                "Accept: application/rss+xml,application/xml,text/html",
                url,
            ]
            return subprocess.run(
                cmd, capture_output=True, check=True, timeout=25
            ).stdout.decode("utf-8", errors="replace")

    collected = {}
    failures = {}
    for url in FEEDS:
        try:
            collected[url] = parse_rss(fetcher(url))
        except (
            ValueError,
            ElementTree.ParseError,
            OSError,
            TimeoutError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ) as exc:
            failures[url] = str(exc)[:120]
    # Never publish an empty/broken snapshot as if it were complete
    # inventory.
    if failures:
        raise ValueError("RSS collection incomplete: " + str(failures))
    now = now or datetime.now(timezone.utc)
    seen = set()
    entries = []
    for feed, items in collected.items():
        for item in items:
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            entries.append(dict(item, feed=feed))
            if len(entries) >= MAX_ITEMS:
                break
    if not entries:
        raise ValueError("No real AutoWereld adverts obtained")
    return {
        "version": 2,
        "collected_at": now.isoformat(),
        "source": "AutoWereld public RSS",
        "feeds_checked": list(FEEDS),
        "entries": entries,
    }


def read_snapshot_records(path, now=None):
    """Return validated, *unverified* public RSS leads and snapshot
    status.
    """
    file = Path(path)
    if not file.is_file():
        return [], "not_supplied"
    if file.stat().st_size > 300000:
        return [], "oversized"
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
        if (
            data.get("version") not in (1, 2)
            or data.get("source") != "AutoWereld public RSS"
        ):
            return [], "invalid_format"
        if data.get("feeds_checked") != list(FEEDS):
            return [], "incomplete_feed_set"
        timestamp = datetime.fromisoformat(data["collected_at"])
        if timestamp.tzinfo is None:
            return [], "no_timezone"
        age = (now or datetime.now(timezone.utc)) - timestamp
        if age < timedelta(minutes=-5) or age > MAX_AGE:
            return [], "stale_or_future"
        entries = data["entries"]
        if not isinstance(entries, list) or not 0 < len(entries) <= MAX_ITEMS:
            return [], "invalid_items"
        validated = {}
        for row in entries:
            if not isinstance(row, dict) or row.get("feed") not in FEEDS:
                return [], "invalid_source"
            url = row.get("url")
            title = row.get("title", "")
            description = row.get("description", "")
            pub_date = row.get("pub_date", "")
            if (
                not isinstance(url, str)
                or not isinstance(title, str)
                or not isinstance(description, str)
                or not isinstance(pub_date, str)
                or len(title) > 220
                or len(description) > 1800
                or len(pub_date) > 100
                or not valid_advert(url, title)
            ):
                return [], "invalid_url"
            validated.setdefault(
                url,
                {
                    "url": url,
                    "title": title,
                    "description": description,
                    "pub_date": pub_date,
                    "evidence": "unverified RSS advertisement only",
                },
            )
        return list(validated.values()), "fresh_index_only"
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return [], "invalid_json"


def read_snapshot(path, now=None):
    records, status = read_snapshot_records(path, now)
    return [(x["url"], x["title"]) for x in records], status


def main():
    p = argparse.ArgumentParser(
        description=(
            "Collect only public AutoWereld RSS; run outside GitHub Actions on"
            " an authorized computer."
        )
    )
    p.add_argument("--output", default="data/autowereld_rss_snapshot.json")
    args = p.parse_args()
    data = collect()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        "Created index-only snapshot of",
        len(data["entries"]),
        "public adverts:",
        out,
    )


if __name__ == "__main__":
    main()
