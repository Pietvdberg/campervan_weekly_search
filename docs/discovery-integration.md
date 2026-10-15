# Marketplace discovery and RDW integration

Manual development workflow only. It queries public Bing RSS indexes for nine categories, attempts to fetch individual listing pages, screens conservative evidence, then queries RDW only for plates explicitly extracted from individual listings. Source coverage reports failures and partial discovery. It also performs an independent live RDW connectivity probe using historical plate V-706-SG, without claiming the vehicle is currently listed.

Unknown road distance, VAT, actual A/C operation, mechanical condition, and payload must not be scored as verified. Indexed results are incomplete and sometimes stale; a source listed as checked does not mean its whole inventory was checked. This is a best-effort index search, not a marketplace API.

Workflow emails only the Hotmail test recipient, saves artifacts and does not enable production scheduling. A green run does not certify complete marketplace coverage.
