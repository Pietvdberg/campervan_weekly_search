"""Human-readable HTML digest. All detailed evidence remains in audit JSON."""
from html import escape
from camper_pipeline import SOURCES, candidate_state, unique_report_items, rss_shortlist, rss_price, clearly_over_budget_title

def e(value):
    return escape(str(value if value is not None else "Unknown"),quote=True)

def euro(value):
    return "€{:,.2f}".format(float(value)).replace(",","X").replace(".",",").replace("X",".") if value is not None else "Niet bevestigd"

def item_card(item):
    c=item["candidate"]
    title=e(c.get("name","Onbekende bestelbus"))
    url=str(c.get("listing_url",""))
    link=(f'<a href="{e(url)}">Bekijk advertentie ↗</a>' if url.startswith("https://") else "Link niet beschikbaar")
    price=euro(c.get("price_incl_vat"))
    advertised=e(c.get("price_advertised") or "onbekend")
    distance=(f'{e(c["distance_km"])} km' if c.get("distance_km") is not None else "Niet geverifieerd")
    missing=[k.replace("_"," ") for k,v in c.get("checks",{}).items() if v is not True]
    blockers=", ".join(missing) if missing else "Geen inhoudelijke controles open"
    return (f'<div class="vehicle"><h3>{title}</h3><p class="meta">Bron: {e(c.get("source","?"))} · Bewijs: {e(item["score"])}% · '
            f'{e(candidate_state(item))}</p><p><strong>Prijs incl. btw:</strong> {price} '
            f'<span class="muted">(geadverteerd: {advertised}; btw-status: {e(c.get("vat_basis","unknown"))})</span></p>'
            f'<p><strong>Rijafstand:</strong> {distance} vanaf Bergen op Zoom</p>'
            f'<p class="muted"><strong>Nog controleren:</strong> {e(blockers)}</p><p>{link}</p></div>')

def render_html(data):
    results=data.get("results",[])
    unique=list(unique_report_items(results))
    qualified=[x for x in unique if candidate_state(x)=="QUALIFIED"]
    potential=[x for x in unique if candidate_state(x)=="POTENTIAL MATCH — UNVERIFIED"
               and x["candidate"].get("checks",{}).get("high_roof") is True
               and x["candidate"].get("checks",{}).get("cab_ac") is True
               and not clearly_over_budget_title(x["candidate"])]
    def priority(x):
        c=x["candidate"]; checks=c.get("checks",{})
        return (checks.get("price_incl_vat_within_8000") is True,
                checks.get("distance_within_100km") is True,
                checks.get("high_roof") is True and checks.get("cab_ac") is True,
                bool(x.get("plate")),x["score"])
    potential.sort(key=priority,reverse=True)
    potential=potential[:5]
    rejected=sum(candidate_state(x)=="REJECTED" for x in results)
    cards="".join(item_card(x) for x in qualified)
    leads="".join(item_card(x) for x in potential)
    rss=rss_shortlist(data.get("unverified_rss_leads",[]),
                      (x["candidate"].get("listing_url") for x in results))
    rss_cards="".join(
        f'<li><strong>{e(x.get("title",""))}</strong><br>'
        f'Geadverteerd: {euro(rss_price(x.get("description")))} (btw onbekend) · '
        f'<a href="{e(x["url"])}">Advertentie ↗</a></li>' for x in rss)
    coverage=data.get("source_coverage",{})
    screening=data.get("source_screening",{})
    source_rows="".join(
        f'<tr><th scope="row">{e(source)}</th><td>{e(screening.get(source,{}).get("total",0))}</td>'
        f'<td>{e(screening.get(source,{}).get("verified_prices",0))}</td>'
        f'<td>{e(screening.get(source,{}).get("verified_distances",0))}</td>'
        f'<td>{e(coverage.get(source,{}).get("status","niet gecontroleerd"))}</td></tr>'
        for source in SOURCES)
    return f"""<!doctype html><html lang="nl"><head><meta charset="utf-8">
<style>
body {{font:15px/1.55 Arial,Helvetica,sans-serif;color:#253345;background:#f3f6f9;margin:0;padding:20px}}
main {{max-width:720px;margin:auto;background:white;padding:28px;border-radius:12px}}
h1 {{font-size:25px;line-height:1.3;margin:0 0 8px;color:#173451}}
h2 {{font-size:19px;margin:30px 0 12px;color:#173451;border-bottom:1px solid #dce3e9;padding-bottom:8px}}
h3 {{font-size:16px;margin:0 0 5px}}
p {{margin:8px 0}}.muted,.meta {{color:#566675;font-size:13px}}
.vehicle {{border:1px solid #dce3e9;border-radius:9px;padding:16px;margin:12px 0}}
.stats {{background:#eaf1f6;padding:14px;border-radius:9px}}
a {{color:#165ba5}} table {{width:100%;border-collapse:collapse;font-size:12px}}
td,th {{border-bottom:1px solid #e5eaf0;padding:8px 5px;text-align:left;vertical-align:top}}
li {{margin:12px 0}}.note {{background:#fff5e3;padding:12px;border-radius:7px}}
</style></head><body><main>
<h1>Camperzoektocht · {e(data.get("generated_on",""))}</h1>
<p>Je wekelijkse overzicht, met alleen gecontroleerde feiten als harde conclusie.</p>
<div class="stats"><strong>{len(qualified)} bevestigde matches</strong> · {len(results)} advertenties bekeken · {rejected} afgewezen</div>
<p class="note">Er is nog geen voertuig dat aantoonbaar aan alle eisen voldoet. Dit betekent niet dat er geen geschikte bus te koop staat.</p>
<h2>✓ Bevestigde kandidaten</h2>
{cards or "<p>Momenteel geen voertuigen met voldoende bevestigd bewijs.</p>"}
<h2>🔎 Interessant, maar nog niet geverifieerd</h2>
<p class="muted">Voorselectie op dakhoogte en airco; de resterende controles zijn geen automatische goedkeuring.</p>
{leads or "<p>Geen bruikbare individueel onderzochte advertenties in deze ronde.</p>"}
<h2>📰 AutoWereld · extra tips (RSS)</h2>
<p class="muted">Deze advertenties komen uitsluitend uit de externe RSS-index. Niet geopend of onafhankelijk gecontroleerd; tellen nooit mee als bevestigde match.</p>
<ul>{rss_cards or "<li>Geen relevante RSS-tips binnen de voorlopige selectie.</li>"}</ul>
<h2>Waar ontbreekt bewijs?</h2>
<table><thead><tr><th>Bron</th><th>Bekeken</th><th>Prijs incl. btw</th><th>Rijroute</th><th>Toegang</th></tr></thead>
<tbody>{source_rows}</tbody></table>
<p class="muted">Tellers geven gevonden bewijs weer, geen garantie dat alle advertenties of voorraad zijn onderzocht.</p>
<h2>Mijn advies voor de volgende stap</h2>
<p>Bekijk eerst de interessante advertenties. Vraag de verkoper om de totale consumentenprijs inclusief btw, het kenteken, de exacte ophaallocatie, afmetingen, laadvermogen en onderhoudshistorie. Controleer de technische staat via een onafhankelijke aankoopkeuring.</p>
<p class="muted">APK ≠ technische aankoopkeuring. Afgewezen advertenties en RDW/APK-details staan in het GitHub Actions-auditbestand. Dit bericht bevat geen onbevestigde aanbevelingen.</p>
</main></body></html>"""
