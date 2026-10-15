# Listing evidence and browser fallback

The pipeline extracts conservative listing evidence and ranks only independently supported facts.

## Evidence extraction
- Supports JSON-LD and embedded Next.js JSON data present in the returned HTML.
- Parses Dutch monetary formats and identifies explicit **incl. btw**, **excl. btw (21%)**, and **marge**. Without an explicit price basis, VAT-inclusive eligibility stays **unknown**.
- Extracts structured coordinates where present and checks driving distance to approximate Bergen op Zoom city centre using an OSRM routing endpoint. Missing coordinates or routing errors yield **unknown**, not within-range.
- Air conditioning and high-roof declarations remain seller statements. Conversion suitability stays unknown until payload/dimensions are independently checked.
- RDW is queried only for registration plates found on individual listing pages. RDW registration does not prove a vehicle is still for sale.

## Browser-rendered marketplace pages
Optional `browser_render.py` performs read-only Chromium rendering on the configured marketplace domains. It is **off by default** and used only when an inventory HTML response has no links, or an individual Next.js shell lacks extractable model content. It does not log in, solve captchas or bypass access controls.

To enable in an isolated verification runner:

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
ENABLE_BROWSER_RENDER=1 python3 discover_listings.py
```

Avoid turning this on indiscriminately; check each site's access policies and rate limits. Browser rendering may still be blocked.

## Driving distance
`OSRM_BASE_URL` may point at a self-hosted routing endpoint. By default the code can use the public OSRM demonstration router, **which is not a production SLA-backed service**; for reliable operation deploy a dedicated approved routing service. The origin is an approximate city-centre coordinate, not the user's street address. Route distance is a screening estimate.

## Source coverage
Direct marketplace/dealer seed URLs are not complete marketplace inventories; some may become stale or be blocked. Reports must separate unreachable, indexed, fetched and fully validated candidate counts. The source catalogue does not prove "most dealers within 100 km" are covered; that requires independently maintaining a geolocated dealer inventory and testing each endpoint.

## Production gate
The development verification workflow still runs after code merges without emailing both recipients. Production sending and scheduling remain intentionally disabled until live listings, reliable source coverage and RDW-linked candidates are demonstrated.
