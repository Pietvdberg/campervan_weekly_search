# Camper van weekly search

Official RDW checks for camper-van candidates with confirmed Dutch registration plates.

## Vehicle and APK lookup

`rdw_lookup.py` queries two public RDW datasets: vehicle registration (`m9d7-ebf2`) and recorded APK defects (`a34c-vvps`). Requires Python 3 and internet access; no packages to install.

```bash
python3 rdw_lookup.py VL-034-B --output rdw_results.json
```

## GitHub Actions

Open **Actions → RDW vehicle and APK checks → Run workflow** and enter one or more registration plates separated by spaces or commas. After completion, download the `rdw-results-<run-id>` JSON artifact.

For scheduled Thursday checks, set repository variable `RDW_PLATES` in **Settings → Secrets and variables → Actions → Variables** to a space-separated list of confirmed plates. The workflow runs Thursdays at 12:30 UTC (14:30 during Dutch summer time, 13:30 during winter time). With no configured plates, it skips the lookup.

The GitHub Action does **not** automatically discover new listing plates, transfer its results into the ChatGPT camper search, or send email. The existing Thursday 15:00 ChatGPT search and email delivery are separate. A future integration must retrieve the real JSON artifact or directly query RDW for each newly discovered confirmed plate.

Never infer missing APK records or interpret an empty defects response as evidence of full maintenance history. Do not commit credentials or private data.
