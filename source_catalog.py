"""Shared source groups, inventory seeds, target models and screening checks."""
import re

SOURCE_DOMAINS = {
    "Marktplaats": "marktplaats.nl",
    "AutoScout24": "autoscout24.nl",
    "AutoTrack": "autotrack.nl",
    "viaBOVAG": "viabovag.nl",
    "AutoWereld": "autowereld.nl",
    "Local dealers": None,
}
# Direct category/dealer entry points. A returned page is not proof of complete inventory.
SEED_PAGES = {
    "Marktplaats": ["https://www.marktplaats.nl/l/auto-s/bestelauto-s/q/boxer+l2h2/","https://www.marktplaats.nl/l/auto-s/bestelauto-s/q/transit+l2h2/"],
    "AutoScout24": ["https://www.autoscout24.nl/lst/peugeot/boxer/ve_l2h2","https://www.autoscout24.nl/lst/peugeot/boxer","https://www.autoscout24.nl/lst/ford/transit","https://www.autoscout24.nl/lst/fiat/ducato","https://www.autoscout24.nl/lst/renault/master"],
    "AutoTrack": ["https://www.autotrack.nl/aanbod/merk/peugeot/model/boxer","https://www.autotrack.nl/aanbod/merk/ford/model/transit","https://www.autotrack.nl/aanbod/merk/citroen/model/jumper","https://www.autotrack.nl/aanbod/merk/fiat/model/ducato","https://www.autotrack.nl/aanbod/merk/renault/model/master"],
    "viaBOVAG": ["https://www.viabovag.nl/auto/merk-peugeot/model-boxer/occasion","https://www.viabovag.nl/auto/merk-ford/model-transit/occasion","https://www.viabovag.nl/"],
    "AutoWereld": ["https://www.autowereld.nl/peugeot/boxer/330-2-0-bluehdi-l2h2-premium-3-zitplaatsen-bluetooth-airco-cruise-43911117/details.html","https://www.autowereld.nl/peugeot/boxer/_energy","https://www.autowereld.nl/ford/transit/","https://www.autowereld.nl/citroen/jumper/","https://www.autowereld.nl/fiat/ducato/","https://www.autowereld.nl/aanbieder/bedrijfswagencentrum-roosendaal-b-v-6035/auto.html"],
    "Local dealers": [
        "https://www.autowereld.nl/aanbieder/bedrijfswagencentrum-roosendaal-b-v-6035/auto.html",
        "https://www.autowereld.nl/aanbieder/mana-bedrijfswagens-910447/auto.html",
        "https://www.autowereld.nl/aanbieder/louwman-mercedes-benz-bedrijfswagens-roosendaal-1306925/auto.html",
        "https://www.autowereld.nl/aanbieder/volkswagen-breda-10209/auto.html",
        "https://www.autowereld.nl/aanbieder/louwman-mercedes-benz-bedrijfswagens-goes-1306923/auto.html",
        "https://www.autowereld.nl/aanbieder/van-mossel-breda-1013023/auto.html",
        "https://www.autowereld.nl/aanbieder/auto-goes-5455/auto.html",
        "https://www.vanmossel.nl/van-mossel-bedrijfswagens/voorraad?category=van&country=nl&type=used",
        "https://www.vanmossel.nl/vestigingen/van-mossel-renault-dacia-roosendaal"],
}

VAN_MODEL = re.compile(r"\b(boxer|jumper|ducato|transit|master|movano|sprinter|crafter|daily|transporter|hi[ -]?ace|nv400)\b",re.I)

SOURCE_NAMES = tuple(SOURCE_DOMAINS)
REQUIRED_CHECKS = ("high_roof", "cab_ac", "conversion_suitable", "distance_within_100km", "price_incl_vat_within_8000")

# All configured seeds except the explicit historical advert are inventory
# entry points. Detail responses always retain strict path identity.
INVENTORY_SEEDS = frozenset(url for urls in SEED_PAGES.values() for url in urls
                            if not url.endswith("/details.html"))

# Verified against the public response's pageQuery on 17 October 2026.
# Unsupported Marktplaats/viaBOVAG query parameters are deliberately not used.
BUDGET_PAGES = {
    "AutoScout24": ["https://www.autoscout24.nl/lst/" + path + "?priceto=8000&sort=price&desc=0"
                    for path in ("peugeot/boxer", "ford/transit", "fiat/ducato", "renault/master", "citroen/jumper")],
    "AutoTrack": ["https://www.autotrack.nl/aanbod/" + path + "?priceto=8000&sort=price&desc=0"
                  for path in ("peugeot/boxer", "ford/transit", "fiat/ducato", "renault/master", "citroen/jumper")],
}
INVENTORY_SEEDS = INVENTORY_SEEDS | frozenset(url for urls in BUDGET_PAGES.values() for url in urls)

# Ranking hints only; never substitute these names for a road route.
DISCOVERY_TOWNS = ("bergen op zoom", "roosendaal", "zevenbergen", "breda", "etten-leur",
                   "halsteren", "steenbergen", "tholen", "goes", "tilburg", "dordrecht",
                   "rotterdam", "oosterhout", "hoogerheide", "rucphen")

# V2 includes compact Transporter/HiAce conversions with a viable roof solution.
# These remain bounded public inventory requests, not claims of full coverage.
for source, root in (("AutoScout24", "https://www.autoscout24.nl/lst/"),
                     ("AutoTrack", "https://www.autotrack.nl/aanbod/")):
    BUDGET_PAGES[source] += [root + model + "?priceto=8000&sort=price&desc=0"
                             for model in ("volkswagen/transporter", "toyota/hiace")]
SEED_PAGES["Marktplaats"] += ["https://www.marktplaats.nl/l/auto-s/bestelauto-s/q/" + model + "/"
                             for model in ("transporter+hefdak", "hiace")]
INVENTORY_SEEDS = INVENTORY_SEEDS | frozenset(url for urls in BUDGET_PAGES.values() for url in urls) | frozenset(SEED_PAGES["Marktplaats"])
