# Pipeline verification scope

This development workflow **does not implement live listing discovery** and is not a production weekly search.

* Unit tests exercise candidate screening, missing specifications, unconfirmed plates, RDW successful records and RDW errors using synthetic fixtures.
* The workflow processes `candidates.json`, which initially contains no real candidates and honestly declares all nine sources unverified.
* Live RDW calls are made only for a plate explicitly linked to a current individual listing and confirmed by a separate verification step. They are not called on guessed plates.
* The message goes only to `piet.v.d.berg@hotmail.com`. Production mode is not exposed in this workflow.
* To complete production deployment, implement lawful, stable live discovery for each requested marketplace and local dealer; independent listing/plate verification; actual source-coverage reporting; a production schedule; and end-to-end checks against real, verified candidates.

Do not interpret a green run of this workflow as confirmation that the complete weekly production search has been implemented.
