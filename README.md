# Camper van weekly search — RDW lookup

`rdw_lookup.py` retrieves actual official RDW registration records (`m9d7-ebf2`) and recorded APK defects (`a34c-vvps`) for Dutch number plates.

## Automated handoff from ChatGPT

1. During the Thursday camper search, find candidates and independently confirm their number plates.
2. Create a new GitHub file `requests/YYYY-MM-DD.txt` containing those plates separated by spaces or newlines. If a retry is needed, use a unique suffix, such as `requests/YYYY-MM-DD-retry1.txt`.
3. A push-triggered GitHub Action runs `rdw_lookup.py`, uploads a JSON artifact, and, **only when the entire lookup succeeds**, commits `results/YYYY-MM-DD.json` (or matching suffixed filename) to the repository.
4. Read that exact results file through the GitHub connector and match records to the corresponding listing plates. Incorporate verified fields into the camper report and email.

If the results file is missing, failed, or late, never imply RDW verification succeeded. Use direct RDW queries as fallback where possible. **The GitHub workflow has not yet been verified end-to-end.**

## Local invocation

```bash
python3 rdw_lookup.py VL-034-B --output rdw_results.json
```

## Manual invocation

Go to **Actions → RDW vehicle and APK checks → Run workflow**, enter plates separated by commas or spaces, and download the resulting workflow artifact. Manual runs do not commit a result file.

**Limitations:** The script returns raw RDW records; the report must interpret the correct fields carefully. No defect records does not prove a fault-free vehicle, and APK approval does not establish service history. The repository is public, so requests and results are publicly visible; only submit public vehicle registration numbers and never secrets.
