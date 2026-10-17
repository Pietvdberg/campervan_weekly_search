# Marketplace discovery and RDW integration

Manual development workflow only. It queries public Bing RSS indexes for nine categories, attempts to fetch individual listing pages, screens conservative evidence, then queries RDW only for plates explicitly extracted from individual listings. Source coverage reports failures and partial discovery. It also performs an independent live RDW connectivity probe using historical plate V-706-SG, without claiming the vehicle is currently listed.

Unknown road distance, VAT, actual A/C operation, mechanical condition, and payload must not be scored as verified. Indexed results are incomplete and sometimes stale; a source listed as checked does not mean its whole inventory was checked. This is a best-effort index search, not a marketplace API.

Workflow emails only the Hotmail test recipient, saves artifacts and does not enable production scheduling. A green run does not certify complete marketplace coverage.

Discovery now shares per-host access state across every source group and phase.
An HTTP 403 or 429 stops subsequent underlying fetches to that host for the run,
including when AutoWereld is encountered again through local-dealer seeds.
Independent dealer hosts can continue. Each host has a 100-request run budget;
coverage records the host counts, HTTP restriction reasons and budget stops.
Errors are classified by HTTP status, not by digits in an exception message.
