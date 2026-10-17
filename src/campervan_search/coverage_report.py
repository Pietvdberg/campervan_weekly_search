"""Visible CI source-health summary; zero usable discovery fails
clearly.
"""

import json
import os
from pathlib import Path


def render(data):
    lines = [
        "## Core search source health: " + data["status"],
        "",
        (
            "Bounded primary-advert samples; optional RSS tips are assessed"
            " separately."
        ),
        "",
        (
            "| Source | Bound adverts | Gross prices | Routes | Consecutive"
            " zero runs | Health |"
        ),
        "|---|---:|---:|---:|---:|---|",
    ]
    optional = []
    for source, row in data["sources"].items():
        if row.get("role") == "optional_rss":
            optional.append((source, row))
            continue
        lines.append(
            f'| {source} | {row["bound"]} | {row["verified_prices"]} |'
            f' {row["verified_routes"]} | {row["zero_bound_streak"]} |'
            f' {row["severity"]} |'
        )
    lines += ["", "Core alerts:"] + [
        "- "
        + alert["source"]
        + ": "
        + alert["message"]
        + (
            " Next: " + alert["next_action"]
            if alert.get("next_action")
            else ""
        )
        for alert in data["alerts"]
    ]
    if optional:
        lines += [
            "",
            "### Optional RSS tips",
            "",
            (
                "Feed health measures freshness and complete screening, not"
                " verified inventory. Blocked primary-advert access is"
                " informational for this optional channel."
            ),
            "",
            (
                "| Source | Snapshot | RSS screened | Interesting | Feed"
                " health | Advert follow-up |"
            ),
            "|---|---|---:|---:|---|---|",
        ]
        for source, row in optional:
            lines.append(
                f'| {source} | {row.get("rss_status") or "not supplied"} |'
                f' {row.get("rss_evaluated", 0)} |'
                f' {row.get("rss_interesting", 0)} | {row["severity"]} |'
                f' {row.get("detail_status", "unverified")} |'
            )
        lines += [""]
        lines += [
            "- " + alert["source"] + ": " + alert["message"]
            for alert in data.get("optional_alerts", [])
        ]
    for source, row in data["sources"].items():
        if row.get("access_restriction"):
            reason = (
                str(row["access_restriction"])
                .replace("\n", " ")
                .replace("\r", " ")
                .replace("`", "'")
            )
            lines.append(
                "- " + source + " access diagnostic: `" + reason + "`"
            )
    return "\n".join(lines) + "\n"


def main():
    health = json.loads(Path("coverage_health.json").read_text())
    text = render(health)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write(text)
    for level, alerts in (
        ("warning", health["alerts"]),
        ("notice", health.get("optional_alerts", [])),
    ):
        for alert in alerts:
            # Only controlled source names/messages enter annotations;
            # strip
            # protocol delimiters.
            message = (
                (alert["source"] + ": " + alert["message"])
                .replace("%", "%25")
                .replace("\r", "%0D")
                .replace("\n", "%0A")
            )
            print("::" + level + "::" + message)
    return 1 if health["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
