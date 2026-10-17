"""Visible CI source-health summary; zero usable discovery fails clearly."""
import json
import os
from pathlib import Path


def render(data):
    lines = ["## Search source health: " + data["status"], "", "Bounded samples; RSS-only stock is not validated inventory.", "",
             "| Source | Bound adverts | Gross prices | Routes | RSS screened / interesting | Consecutive zero runs | Health |", "|---|---:|---:|---:|---:|---:|---|"]
    for source, row in data["sources"].items():
        rss = str(row.get("rss_evaluated", 0)) + ' / ' + str(row.get("rss_interesting", 0)) if source == "AutoWereld" else '—'
        lines.append(f'| {source} | {row["bound"]} | {row["verified_prices"]} | {row["verified_routes"]} | {rss} | {row["zero_bound_streak"]} | {row["severity"]} |')
    lines += ["", "Alerts:"] + ["- " + alert["source"] + ": " + alert["message"] + (" Next: " + alert["next_action"] if alert.get("next_action") else "") for alert in data["alerts"]]
    for source, row in data["sources"].items():
        if row.get("access_restriction"):
            reason = str(row["access_restriction"]).replace("\n", " ").replace("\r", " ").replace("`", "'")
            lines.append("- " + source + " access diagnostic: `" + reason + "`")
    return "\n".join(lines) + "\n"


def main():
    health = json.loads(Path("coverage_health.json").read_text())
    text = render(health)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write(text)
    for alert in health["alerts"]:
        # Only controlled source names/messages enter annotations; strip protocol delimiters.
        message = (alert["source"] + ": " + alert["message"]).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print("::warning::" + message)
    return 1 if health["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
