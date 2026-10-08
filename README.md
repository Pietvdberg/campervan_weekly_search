# Camper van weekly search — RDW lookup

The Python script `rdw_lookup.py` checks official RDW registration (`m9d7-ebf2`) and recorded APK defects (`a34c-vvps`) for **confirmed plates found in the current camper search**.

## Run locally

```bash
python3 rdw_lookup.py VL-034-B --output rdw_results.json
```

## GitHub Actions

Use **Actions → RDW vehicle and APK checks → Run workflow** and supply the current week's confirmed plates separated by spaces or commas. Download the `rdw-results-<run-id>` artifact and examine the JSON records.

The workflow is **on-demand only**: it no longer checks a stale static list on Thursdays. To automate the full discovery → dispatch → artifact → email chain, the orchestrator needs permission to invoke GitHub's `workflow_dispatch` API and retrieve the corresponding artifact. The currently connected ChatGPT GitHub tools can read workflow artifacts but do **not** expose a workflow dispatch operation, so the GitHub Action cannot yet be automatically triggered from the scheduled ChatGPT task.

The scheduled ChatGPT camper search should query the same public RDW endpoints directly for confirmed plates where possible. Never claim the script ran or an APK history was checked unless vehicle-specific data was actually retrieved. An empty defects list is not proof of full maintenance history.
