"""Second-pass triage of every public RSS advert; never verified
inventory.

Only facts in each feed item are used. Publication dates, towns and
price labels
remain source claims. Actual road distance and physical condition
stay
unknown.
"""

import re
from decimal import ROUND_HALF_UP, Decimal
from html import escape, unescape

from campervan_search.autowereld_snapshot import valid_advert
from campervan_search.listing_evidence import parse_amount, price_evidence
from campervan_search.source_catalog import DISCOVERY_TOWNS
from campervan_search.vehicle_risks import auction_evidence, mechanical_failure


def plain(value):
    value = re.sub(
        r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>",
        " ",
        str(value or ""),
        flags=re.I | re.S,
    )
    return " ".join(unescape(re.sub(r"<[^>]*>", " ", value)).split())


def evaluate_leads(leads, evaluated_urls=(), access_restriction=None):
    from campervan_search.discover_listings import AC, ROOF, advertised_feature

    evaluated = set(evaluated_urls)
    records = []
    seen = set()
    for lead in leads:
        url = str(lead.get("url") or "")
        title = plain(lead.get("title"))[:220]
        description = plain(lead.get("description"))[:1800]
        text = title + " " + description
        reasons, questions, exclusions = [], [], []
        if not valid_advert(url, title):
            exclusions.append(
                "Geen geldige individuele AutoWereld-advertentielink"
            )
        duplicate = url in seen
        seen.add(url)
        # Feed descriptions label the purchase amount; image URLs/model
        # years
        # must never become a price. Reject ambiguous multiple asking
        # prices.
        amounts = [
            parse_amount(m)
            for m in re.findall(
                r"vraagprijs\s*:\s*(?:€|EUR)\s*([\d.,]+)", description, re.I
            )
        ]
        amounts = {amount for amount in amounts if amount is not None}
        advertised = next(iter(amounts)) if len(amounts) == 1 else None
        vat = price_evidence("<p>" + escape(text) + "</p>", [])
        gross = vat.get("amount_incl_vat") if len(amounts) == 1 else None
        # The VAT statement must apply to the asking price, not another
        # amount.
        if gross is not None and vat.get("advertised_amount") != float(
            advertised
        ):
            gross = None
        year = re.search(r"\bbouwjaar\s*:\s*(\d{4})\b", description, re.I)
        mileage = re.search(
            r"\bkilometerstand\s*:\s*([\d.]+)\s*km\b", description, re.I
        )
        ac = advertised_feature(text, AC)
        roof = advertised_feature(text, ROOF)
        low_roof = bool(re.search(r"\bL[1-4][ -]*H1\b", title, re.I))
        inappropriate = re.compile(
            r"\b(?:open laadbak|pick[ -]?up|chassis"
            r" cabine|kipper|hoogwerker)\b",
            re.I,
        )
        if advertised_feature(title, inappropriate) is True:
            exclusions.append(
                "Geadverteerde carrosserie past niet bij de gezochte bestelbus"
            )
        failure = mechanical_failure(text)
        if failure:
            exclusions.append(
                "Actueel defect/storingssignaal geadverteerd: " + failure
            )
        if auction_evidence(title):
            exclusions.append("Veilingaanbod")
        if ac is False:
            exclusions.append("Expliciet geen cabine-airco geadverteerd")
        if (advertised is not None and advertised > 8000) or (
            gross is not None and gross > 8000
        ):
            exclusions.append(
                "Minimale of totale vraagprijs overschrijdt EUR 8.000"
            )
        if ac is True:
            reasons.append("Cabine-airco geadverteerd")
        else:
            questions.append(
                "Is cabine-airco aanwezig? Een advertentievermelding is"
                " voldoende voor deze zoekcheck."
            )
        if roof is True:
            reasons.append("Hoger dak of hefdak geadverteerd")
        else:
            questions.append(
                "Meet bruikbare stahoogte; controleer haalbaarheid en kosten"
                " van een hefdak" + (" bij deze H1" if low_roof else "") + "."
            )
        if advertised is not None:
            reasons.append("Vraagprijs in de feed: EUR " + str(advertised))
        else:
            questions.append("Bevestig de eenduidige totale vraagprijs.")
        if gross is None:
            questions.append(
                "Wat is de totale consumentenprijs inclusief btw en verplichte"
                " kosten?"
            )
        places = [
            place
            for place in DISCOVERY_TOWNS
            if re.search(r"\b" + re.escape(place) + r"\b", text, re.I)
        ]
        questions.append(
            "Bevestig het volledige ophaaladres en bereken de rijroute vanaf"
            " Bergen op Zoom; een plaatsnaam is geen routebewijs."
        )
        questions.append(
            "Controleer actuele beschikbaarheid, kenteken, onderhoud en"
            " inrichting/gewichten via de individuele advertentie en een"
            " aankoopkeuring."
        )
        status = (
            "EXCLUDED"
            if exclusions
            else (
                "DUPLICATE"
                if duplicate
                else (
                    "ALREADY_EVALUATED"
                    if url in evaluated
                    else (
                        "INTERESTING"
                        if advertised is not None and ac is True
                        else "NEEDS_INFO"
                    )
                )
            )
        )
        extra_vat = (
            float(
                (advertised * Decimal("1.21")).quantize(
                    Decimal(".01"), rounding=ROUND_HALF_UP
                )
            )
            if advertised is not None and gross is None
            else None
        )
        if extra_vat is not None and extra_vat > 8000 and advertised <= 8000:
            questions.insert(
                0,
                "Btw is bepalend: als dit een nettoprijs is, wordt het EUR "
                + str(extra_vat)
                + " en valt de bus buiten budget.",
            )
        records.append(
            {
                "url": url,
                "title": title,
                "status": status,
                "reasons": exclusions or reasons,
                "questions": questions,
                "advertised_price": (
                    float(advertised) if advertised is not None else None
                ),
                "source_reported_gross_price": gross,
                "gross_if_21_percent_added": extra_vat,
                "advertised_cab_ac": ac,
                "advertised_roof_solution": roof,
                "low_roof_mentioned": low_roof,
                "place_hints_not_routes": places,
                "distance_km": None,
                "source_reported_year": int(year.group(1)) if year else None,
                "source_reported_mileage_km": (
                    int(mileage.group(1).replace(".", ""))
                    if mileage and mileage.group(1).replace(".", "").isdigit()
                    else None
                ),
                "publication_date_reported": lead.get("pub_date"),
                "followup_status": (
                    "source_access_blocked"
                    if access_restriction
                    else "individual_advert_review_needed"
                ),
                "access_restriction": access_restriction,
                "evidence": (
                    "RSS-only assessment; not a verified search match or"
                    " purchase recommendation"
                ),
            }
        )

    def priority(row):
        price = row["source_reported_gross_price"] or row["advertised_price"]
        return (
            row["status"] == "INTERESTING",
            row["advertised_roof_solution"] is True,
            row["source_reported_gross_price"] is not None,
            row["gross_if_21_percent_added"] is None
            or row["gross_if_21_percent_added"] <= 8000,
            bool(row["place_hints_not_routes"]),
            -(price or 1000000),
        )

    ranked = sorted(
        (r for r in records if r["status"] in ("INTERESTING", "NEEDS_INFO")),
        key=priority,
        reverse=True,
    )
    return {
        "version": 1,
        "evaluated_records": len(records),
        "counts": {
            status: sum(r["status"] == status for r in records)
            for status in (
                "INTERESTING",
                "NEEDS_INFO",
                "EXCLUDED",
                "ALREADY_EVALUATED",
                "DUPLICATE",
            )
        },
        "shortlist": ranked[:5],
        "results": records,
        "note": (
            "All supplied RSS records are screened separately; no"
            " bound-advert, gross-price or road-route verification is created"
            " by this process."
        ),
    }


def assess_data(data):
    existing = data.get("rss_evaluation")
    if isinstance(existing, dict):
        return existing
    candidates = (
        [item["candidate"] for item in data.get("results", [])]
        if "results" in data
        else data.get("candidates", [])
    )
    return evaluate_leads(
        data.get("unverified_rss_leads", []),
        (
            candidate.get("listing_url")
            for candidate in candidates
            if candidate.get("individual_listing_confirmed") is True
        ),
        data.get("source_coverage", {})
        .get("AutoWereld", {})
        .get("source_block_reason"),
    )


def main():
    import argparse
    import json
    import os
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="discovered_candidates.json")
    parser.add_argument(
        "--output", default="campervan_search.rss_evaluation.json"
    )
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    assessment = assess_data(data)
    Path(args.output).write_text(
        json.dumps(assessment, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    counts = assessment["counts"]
    summary = (
        f"## Pi RSS lead assessment\n\n{assessment['evaluated_records']} feed"
        f" items assessed: {counts['INTERESTING']} interesting,"
        f" {counts['NEEDS_INFO']} need more information, {counts['EXCLUDED']}"
        f" excluded, {counts['ALREADY_EVALUATED']} already covered by parsed"
        f" adverts, {counts['DUPLICATE']} duplicates.\n\nThese are unverified"
        " research leads, not validated inventory or purchase"
        " recommendations.\n"
    )
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(
            os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8"
        ) as output:
            output.write(summary)


if __name__ == "__main__":
    main()
