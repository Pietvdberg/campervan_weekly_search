# AutoWereld RSS collector — opt-in research handoff

AutoWereld serves public RSS feeds, but the GitHub-hosted runner has repeatedly
received fallback HTML instead. The provider's [FAQ](https://www.autowereld.nl/faq.php)
says new API access is not offered. Do **not** try to circumvent an access
restriction, solve challenges, rotate proxies or impersonate credentials.

## Permitted collector candidates

A local computer or Raspberry Pi running Python 3 is technically sufficient **if**
AutoWereld permits the requests and the machine actually receives RSS XML.
Do not register a self-hosted GitHub Actions runner on a public repository merely
for this: it exposes a home machine to code from untrusted pull requests.
Use a standalone, unprivileged script instead. A managed server is an option
only after its access and service terms are verified. Neither collector has
been tested on the user's network.

## Validate manually (no GitHub token required)

1. On the intended authorized machine, verify that
   `https://www.autowereld.nl/rss/peugeot/boxer/` returns XML with
   `<rss>`, `<item>`, and individual first-party listing URLs.
2. Run `python3 autowereld_snapshot.py --output data/autowereld_rss_snapshot.json`.
   It downloads each of the five model feeds once, with a response size limit.
   Collection **fails** if any feed is inaccessible or malformed, or there are
   no valid vehicle advertisements. No fallback HTML is converted into fake XML.
3. Inspect the file: it contains only public URLs, titles, publication dates,
   source feeds and collection timestamp. It is **not** a purchase recommendation.
4. For a controlled end-to-end test, manually commit this JSON to the repo and
   run the **development-only** marketplace integration workflow while the
   snapshot is under 48 hours old. It is not an automatic uploader.
5. Remove stale snapshots once tested; a missing or expired snapshot is ignored
   with an explicit status in the discovery coverage report.

GitHub's workflow accepts `data/autowereld_rss_snapshot.json`, or a file path
provided using `AUTOWERELD_RSS_SNAPSHOT`. The reader enforces the exact five
feeds, first-party HTTPS individual advert URLs, model relevance, 250-entry
maximum, <=48-hour age and a bounded file size. No third-party data or
arbitrary URLs are fetched through this handoff.

**Important limitation:** GitHub currently receives fallback HTML for
individual AutoWereld listing pages too. A successful snapshot can improve
`detail_urls_discovered`, but does **not** necessarily increase
`individual_pages_fetched`. To verify a vehicle, the original listing still
must be fetched successfully and subjected to the ordinary evidence checks.
Developing an authenticated or independently trusted detail-page evidence
handoff would require separate review and consent.

Production scheduling stays disabled; manual development email routing
remains Hotmail-only.
