"""Human-readable HTML digest. All detailed evidence remains in audit
JSON.
"""

from html import escape
from pathlib import Path
from string import Template

from campervan_search.camper_pipeline import (
    SOURCES,
    candidate_state,
    report_selection,
)

REPORT_TEMPLATE = Path(__file__).with_name("resources") / "report.html"


def e(value):
    return escape(str(value if value is not None else "Unknown"), quote=True)


def euro(value):
    return (
        "€{:,.2f}".format(float(value))
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
        if value is not None
        else "Niet bevestigd"
    )


def item_card(item):
    c = item["candidate"]
    from campervan_search.digest_details import details

    editorial = details(item)
    title = e(c.get("name", "Onbekende bestelbus"))
    url = str(c.get("listing_url", ""))
    link = (
        f'<a href="{e(url)}">Bekijk advertentie ↗</a>'
        if url.startswith("https://")
        else "Link niet beschikbaar"
    )
    price = euro(c.get("price_incl_vat"))
    advertised = e(c.get("price_advertised") or "onbekend")
    distance = (
        f'{e(c["distance_km"])} km'
        if c.get("distance_km") is not None
        else "Niet geverifieerd"
    )
    labels = {
        "high_roof": "bruikbare dakoplossing",
        "cab_ac": "geadverteerde cabine-airco",
        "distance_within_100km": "rijroute binnen 100 km",
        "price_incl_vat_within_8000": "totale prijs inclusief btw",
    }
    blockers = (
        "; ".join(
            labels[key]
            for key in item.get("search_assessment", {}).get("missing", [])
        )
        or "Advertentiechecks afgerond; aankoopcontroles blijven nodig"
    )
    status = {
        "SEARCH_MATCH": "Zoekmatch — keuring volgt",
        "CONDITIONAL": "Voorwaardelijke researchlead",
        "REJECTED": "Afgewezen",
    }.get(
        item.get("search_assessment", {}).get("status"), candidate_state(item)
    )
    research_html = "".join(
        '<p class="muted"><strong>Aandrijflijnonderzoek:</strong> '
        + e(" ".join(note.get("findings", [])))
        + " "
        + " ".join(
            '<a href="' + e(source["url"]) + '">Bron</a>'
            for source in note.get("sources", [])
        )
        + "</p>"
        for note in editorial["research_notes"][:2]
    )
    if not research_html:
        research_html = (
            '<p class="muted">Exacte aandrijflijn nog onvoldoende onderzocht;'
            " geen algemene betrouwbaarheidsclaim.</p>"
        )
    risks = (
        "; ".join(
            dict.fromkeys(
                [risk["message"] for risk in item.get("rdw_risks", [])]
                + [
                    reason
                    for reason in item.get("reasons", [])
                    if "RDW" in reason
                ]
            )
        )
        or "Geen gemelde RDW-signalen; technische staat blijft ongeverifieerd"
    )
    checklist_percent = e(
        item.get("search_assessment", {}).get("checklist_coverage_percent", 0)
    )
    return (
        (
            '<div class="vehicle"><h3>'
            f"{title}"
            '</h3><p class="meta">Bron: '
            f"{e(c.get('source', '?'))}"
            " · Zoekbewijs: "
            f"{checklist_percent}"
            "% · "
            f"{e(status)}"
            "</p><p><strong>Prijs incl. btw:</strong> "
            f"{price}"
            ' <span class="muted">(geadverteerd: '
            f"{advertised}"
            "; btw-status: "
            f"{e(c.get('vat_basis', 'unknown'))}"
            ")</span></p><p><strong>Rijafstand:</strong> "
            f"{distance}"
            " vanaf Bergen op Zoom</p>"
        )
        + (
            "<p><strong>Verkopersinformatie:</strong>"
            f' {e("; ".join(c.get("advertised_cautions", [])))}</p>'
            if c.get("advertised_cautions")
            else ""
        )
        + '<p class="muted"><strong>RDW-aandachtspunten:</strong>'
        f" {e(risks)}</p><p><strong>Waarom bekijken:</strong>"
        f' {e(editorial["why"])}</p><p class="muted">Categorie'
        f' {e(editorial["category"])} · {e(editorial["ranking"])} ·'
        f' {e(editorial["history"])}</p><p><strong>Vragen:</strong>'
        f' {e("; ".join(editorial["questions"]))}</p><p'
        f' class="muted">{e(editorial["purchase_actions"])}</p>'
        + research_html
        + '<p class="muted"><strong>Nog bevestigen voor de'
        f" zoekselectie:</strong> {e(blockers)}</p><p>{link}</p></div>"
    )


def render_html(data):
    results = data.get("results", [])
    selection = report_selection(data)
    qualified = selection["qualified"]
    potential = selection["potential"]
    rejected = selection["rejected_records"]
    search_count = len(selection["search_matches"])
    match_note = (
        "Er zijn voertuigen die volgens het vastgelegde bewijs aan de"
        " zoekcriteria voldoen. Controleer beschikbaarheid en technische staat"
        " voor aankoop."
        if qualified or search_count
        else (
            "Er is nog geen voertuig dat aantoonbaar aan alle eisen voldoet."
            " Dit betekent niet dat er geen geschikte bus te koop staat."
        )
    )
    cards = "".join(item_card(x) for x in qualified)
    leads = "".join(item_card(x) for x in potential)
    from campervan_search.rss_evaluation import assess_data

    rss = assess_data(data)
    rss_cards = "".join(
        f'<li><strong>{e(row["title"])}</strong><br>'
        f'Vraagprijs volgens RSS: {euro(row["advertised_price"])} · btw: '
        + (
            "onbekend"
            if row["source_reported_gross_price"] is None
            else "expliciet vermeld in feed, niet onafhankelijk bevestigd"
        )
        + "<br>Volgens feed: bouwjaar "
        + e(row.get("source_reported_year") or "onbekend")
        + " · kilometerstand "
        + e(
            row.get("source_reported_mileage_km")
            if row.get("source_reported_mileage_km") is not None
            else "onbekend"
        )
        + "<br><strong>Waarom onderzoeken:</strong> "
        + e("; ".join(row["reasons"]))
        + "<br><strong>Nog uitzoeken:</strong> "
        + e("; ".join(row["questions"]))
        + (
            "<br>Advertentietoegang momenteel geblokkeerd; dit is een"
            " vervolgonderzoekstaak."
            if row["access_restriction"]
            else ""
        )
        + f'<br><a href="{e(row["url"])}">Advertentie ↗</a></li>'
        for row in rss["shortlist"]
    )
    coverage = data.get("source_coverage", {})
    screening = data.get("source_screening", {})
    source_rows = "".join(
        (
            '<tr><th scope="row">'
            f"{e(source)}"
            "</th><td>"
            f"{e(screening.get(source, {}).get('total', 0))}"
            "</td><td>"
            f"{e(screening.get(source, {}).get('verified_prices', 0))}"
            "</td><td>"
            f"{e(screening.get(source, {}).get('verified_distances', 0))}"
            "</td><td>"
            + e(coverage.get(source, {}).get("status", "niet gecontroleerd"))
            + "</td></tr>"
        )
        for source in SOURCES
    )
    review = data.get("report_context") == "development_review"
    introduction = (
        "Ontwikkeltest: herbeoordeling van bekende voorraad, geen nieuwe"
        " advertenties. Brongegevens en RDW zijn waargenomen op "
        + str(
            data.get(
                "evidence_observed_on", data.get("generated_on", "onbekend")
            )
        )
        + "."
        if review
        else (
            "Je wekelijkse overzicht, met alleen gecontroleerde feiten als"
            " harde conclusie."
        )
    )
    template = Template(REPORT_TEMPLATE.read_text(encoding="utf-8"))
    return template.substitute(
        generated_on=e(data.get("generated_on", "")),
        introduction=e(introduction),
        search_count=search_count,
        qualified_count=len(qualified),
        screened_count=len(results),
        rejected_count=rejected,
        match_note=match_note,
        qualified_cards=cards
        or "<p>Momenteel geen voertuigen met voldoende bevestigd bewijs.</p>",
        potential_cards=leads
        or (
            "<p>Geen bruikbare individueel onderzochte advertenties "
            "in deze ronde.</p>"
        ),
        rss_status=e(
            coverage.get("AutoWereld", {}).get(
                "external_rss_snapshot_status", "niet aangeleverd"
            )
        ),
        rss_evaluated=rss["evaluated_records"],
        rss_interesting=rss["counts"]["INTERESTING"],
        rss_needs_info=rss["counts"]["NEEDS_INFO"],
        rss_excluded=rss["counts"]["EXCLUDED"],
        rss_cards=rss_cards
        or "<li>Geen relevante RSS-tips binnen de voorlopige selectie.</li>",
        health_status=e(
            data.get("coverage_health", {}).get(
                "status", "Nog geen bewaarde bronhistorie"
            )
        ),
        unchanged_count=selection["unchanged_suppressed"],
        alerts="".join(
            (
                "<li>"
                + e(
                    alert["source"]
                    + ": "
                    + alert["severity"]
                    + " — "
                    + alert["message"]
                )
                + "</li>"
                for alert in data.get("coverage_health", {}).get("alerts", [])
            )
        ),
        source_rows=source_rows,
    )
