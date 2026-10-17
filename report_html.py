"""Human-readable HTML digest. All detailed evidence remains in audit JSON."""
from html import escape
from camper_pipeline import SOURCES, candidate_state, report_selection

def e(value):
    return escape(str(value if value is not None else "Unknown"),quote=True)

def euro(value):
    return "€{:,.2f}".format(float(value)).replace(",","X").replace(".",",").replace("X",".") if value is not None else "Niet bevestigd"

def item_card(item):
    c=item["candidate"]
    from digest_details import details
    editorial = details(item)
    title=e(c.get("name","Onbekende bestelbus"))
    url=str(c.get("listing_url",""))
    link=(f'<a href="{e(url)}">Bekijk advertentie ↗</a>' if url.startswith("https://") else "Link niet beschikbaar")
    price=euro(c.get("price_incl_vat"))
    advertised=e(c.get("price_advertised") or "onbekend")
    distance=(f'{e(c["distance_km"])} km' if c.get("distance_km") is not None else "Niet geverifieerd")
    labels = {"high_roof":"bruikbare dakoplossing", "cab_ac":"geadverteerde cabine-airco", "distance_within_100km":"rijroute binnen 100 km", "price_incl_vat_within_8000":"totale prijs inclusief btw"}
    blockers = "; ".join(labels[key] for key in item.get("search_assessment", {}).get("missing", [])) or "Advertentiechecks afgerond; aankoopcontroles blijven nodig"
    status = {"SEARCH_MATCH":"Zoekmatch — keuring volgt", "CONDITIONAL":"Voorwaardelijke researchlead", "REJECTED":"Afgewezen"}.get(item.get("search_assessment", {}).get("status"), candidate_state(item))
    research_html = "".join('<p class="muted"><strong>Aandrijflijnonderzoek:</strong> ' + e(' '.join(note.get('findings', []))) + ' ' + ' '.join('<a href="' + e(source['url']) + '">Bron</a>' for source in note.get('sources', [])) + '</p>' for note in editorial['research_notes'][:2])
    if not research_html:
        research_html = '<p class="muted">Exacte aandrijflijn nog onvoldoende onderzocht; geen algemene betrouwbaarheidsclaim.</p>'
    risks = "; ".join(dict.fromkeys([risk["message"] for risk in item.get("rdw_risks", [])] + [reason for reason in item.get("reasons", []) if "RDW" in reason])) or "Geen gemelde RDW-signalen; technische staat blijft ongeverifieerd"
    return (f'<div class="vehicle"><h3>{title}</h3><p class="meta">Bron: {e(c.get("source","?"))} · Zoekbewijs: {e(item.get("search_assessment", {}).get("checklist_coverage_percent", 0))}% · '
            f'{e(status)}</p><p><strong>Prijs incl. btw:</strong> {price} '
            f'<span class="muted">(geadverteerd: {advertised}; btw-status: {e(c.get("vat_basis","unknown"))})</span></p>'
            f'<p><strong>Rijafstand:</strong> {distance} vanaf Bergen op Zoom</p>'
            + (f'<p><strong>Verkopersinformatie:</strong> {e("; ".join(c.get("advertised_cautions", [])))}</p>' if c.get("advertised_cautions") else '') +
            f'<p class="muted"><strong>RDW-aandachtspunten:</strong> {e(risks)}</p>'
            f'<p><strong>Waarom bekijken:</strong> {e(editorial["why"])}</p>'
            f'<p class="muted">Categorie {e(editorial["category"])} · {e(editorial["ranking"])} · {e(editorial["history"])}</p>'
            f'<p><strong>Vragen:</strong> {e("; ".join(editorial["questions"]))}</p>'
            f'<p class="muted">{e(editorial["purchase_actions"])}</p>'
            + research_html + f'<p class="muted"><strong>Nog bevestigen voor de zoekselectie:</strong> {e(blockers)}</p><p>{link}</p></div>')

def render_html(data):
    results=data.get("results",[])
    selection = report_selection(data)
    qualified = selection["qualified"]
    potential = selection["potential"]
    rejected = selection["rejected_records"]
    search_count = len(selection["search_matches"])
    match_note = ("Er zijn voertuigen die volgens het vastgelegde bewijs aan de zoekcriteria voldoen. Controleer beschikbaarheid en technische staat voor aankoop."
                  if qualified or search_count else "Er is nog geen voertuig dat aantoonbaar aan alle eisen voldoet. Dit betekent niet dat er geen geschikte bus te koop staat.")
    cards="".join(item_card(x) for x in qualified)
    leads="".join(item_card(x) for x in potential)
    from rss_evaluation import assess_data
    rss = assess_data(data)
    rss_cards = ''.join(
        f'<li><strong>{e(row["title"])}</strong><br>'
        f'Vraagprijs volgens RSS: {euro(row["advertised_price"])} · btw: '
        + ('onbekend' if row['source_reported_gross_price'] is None else 'expliciet vermeld in feed, niet onafhankelijk bevestigd')
        + '<br>Volgens feed: bouwjaar ' + e(row.get('source_reported_year') or 'onbekend')
        + ' · kilometerstand ' + e(row.get('source_reported_mileage_km') if row.get('source_reported_mileage_km') is not None else 'onbekend')
        + '<br><strong>Waarom onderzoeken:</strong> ' + e('; '.join(row['reasons']))
        + '<br><strong>Nog uitzoeken:</strong> ' + e('; '.join(row['questions']))
        + ('<br>Advertentietoegang momenteel geblokkeerd; dit is een vervolgonderzoekstaak.' if row['access_restriction'] else '')
        + f'<br><a href="{e(row["url"])}">Advertentie ↗</a></li>' for row in rss['shortlist'])
    coverage=data.get("source_coverage",{})
    screening=data.get("source_screening",{})
    source_rows="".join(
        f'<tr><th scope="row">{e(source)}</th><td>{e(screening.get(source,{}).get("total",0))}</td>'
        f'<td>{e(screening.get(source,{}).get("verified_prices",0))}</td>'
        f'<td>{e(screening.get(source,{}).get("verified_distances",0))}</td>'
        f'<td>{e(coverage.get(source,{}).get("status","niet gecontroleerd"))}</td></tr>'
        for source in SOURCES)
    review = data.get("report_context") == "development_review"
    introduction = ("Ontwikkeltest: herbeoordeling van bekende voorraad, geen nieuwe advertenties. Brongegevens en RDW zijn waargenomen op " + str(data.get("evidence_observed_on", data.get("generated_on", "onbekend"))) + "."
                    if review else "Je wekelijkse overzicht, met alleen gecontroleerde feiten als harde conclusie.")
    return f"""<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{font:15px/1.55 Arial,Helvetica,sans-serif;color:#253345;background:#f3f6f9;margin:0;padding:20px}}
main {{max-width:720px;margin:auto;background:white;padding:28px;border-radius:12px;overflow-wrap:anywhere}}
h1 {{font-size:25px;line-height:1.3;margin:0 0 8px;color:#173451}}
h2 {{font-size:19px;margin:30px 0 12px;color:#173451;border-bottom:1px solid #dce3e9;padding-bottom:8px}}
h3 {{font-size:16px;margin:0 0 5px}}
p {{margin:8px 0}}.muted,.meta {{color:#566675;font-size:13px}}
.vehicle {{border:1px solid #dce3e9;border-radius:9px;padding:16px;margin:12px 0}}
.stats {{background:#eaf1f6;padding:14px;border-radius:9px}}
a {{color:#165ba5}} table {{width:100%;border-collapse:collapse;font-size:12px}}
td,th {{border-bottom:1px solid #e5eaf0;padding:8px 5px;text-align:left;vertical-align:top}}
li {{margin:12px 0}}.note {{background:#fff5e3;padding:12px;border-radius:7px}}
@media(max-width:520px) {{body {{padding:8px}} main {{padding:14px}} .vehicle {{padding:12px}} td,th {{padding:6px 2px;font-size:11px}} h1 {{font-size:22px}}}}
</style></head><body style="margin:0;background:#f3f6f9;font-family:Arial,Helvetica,sans-serif;color:#253345"><main style="max-width:720px;margin:auto;background:white;overflow-wrap:anywhere">
<h1>Camperzoektocht · {e(data.get("generated_on",""))}</h1>
<p>{e(introduction)}</p>
<div class="stats"><strong>{search_count} zoekmatches</strong> · {len(qualified)} bevestigde matches voor aankoop · {len(results)} advertenties bekeken · {rejected} afgewezen</div>
<p class="note">{match_note}</p>
<h2>✓ Volledig beoordeeld voor aankoop</h2>
{cards or "<p>Momenteel geen voertuigen met voldoende bevestigd bewijs.</p>"}
<h2>🔎 Zoekshortlist — aankoopkeuring volgt</h2>
<p class="muted">Zoekmatches voldoen aan de advertentie-, btw-prijs- en rijroutechecks. Voorwaardelijke leads missen nog advertentiebewijs. Geen van beide is een technische aankoopkeuring.</p>
{leads or "<p>Geen bruikbare individueel onderzochte advertenties in deze ronde.</p>"}
<h2>📰 AutoWereld · optionele extra tips (RSS)</h2>
<p class="muted">Deze advertenties komen uitsluitend uit de externe RSS-index. Alle aangeleverde feeditems zijn apart beoordeeld op zoekinteresse; de individuele advertentie, rijroute en actuele staat blijven onbevestigd. Tellen nooit mee als bevestigde match.</p>
<p class="muted">Optionele bron · feedstatus: {e(coverage.get("AutoWereld", {}).get("external_rss_snapshot_status", "niet aangeleverd"))}. Beperkte advertentietoegang is geen kritieke storing van de kernzoekopdracht.</p>
<p>{rss["evaluated_records"]} feeditems beoordeeld · {rss["counts"]["INTERESTING"]} interessant om te onderzoeken · {rss["counts"]["NEEDS_INFO"]} missen informatie · {rss["counts"]["EXCLUDED"]} uitgesloten.</p>
<ul>{rss_cards or "<li>Geen relevante RSS-tips binnen de voorlopige selectie.</li>"}</ul>
<h2>Waar ontbreekt bewijs?</h2>
<p>{e(data.get("coverage_health", {}).get("status", "Nog geen bewaarde bronhistorie"))} · {selection["unchanged_suppressed"]} ongewijzigde/herplaatste records niet opnieuw getoond.</p>
<ul>{"".join('<li>' + e(alert["source"] + ': ' + alert["severity"] + ' — ' + alert["message"]) + '</li>' for alert in data.get("coverage_health", {}).get("alerts", []))}</ul>
<table><thead><tr><th>Bron</th><th>Bekeken</th><th>Prijs incl. btw</th><th>Rijroute</th><th>Toegang</th></tr></thead>
<tbody>{source_rows}</tbody></table>
<p class="muted">Tellers geven gevonden bewijs weer, geen garantie dat alle advertenties of voorraad zijn onderzocht.</p>
<h2>Mijn advies voor de volgende stap</h2>
<p>Bekijk eerst de interessante advertenties. Vraag de verkoper om de totale consumentenprijs inclusief btw, het kenteken, de exacte ophaallocatie, afmetingen, laadvermogen en onderhoudshistorie. Controleer de technische staat via een onafhankelijke aankoopkeuring.</p>
<p class="muted">APK ≠ technische aankoopkeuring. Afgewezen advertenties en RDW/APK-details staan in het GitHub Actions-auditbestand. Dit bericht bevat geen onbevestigde aanbevelingen.</p>
</main></body></html>"""
