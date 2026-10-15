"""Optional read-only browser rendering for public JavaScript listings.

Requires pip install playwright and playwright install chromium.
No captcha-solving, login, stealth behavior or anti-bot circumvention.
"""
from urllib.parse import urlparse

ALLOWED_DOMAINS=(
 "marktplaats.nl","gaspedaal.nl","wijkopenautos.nl","autoscout24.nl",
 "autotrack.nl","viabovag.nl","autowereld.nl","bedrijfsauto.nl",
 "trucksnl.com","vanmossel.nl"
)

def render(url,timeout_ms=12000):
    p=urlparse(url)
    host=(p.hostname or "").lower()
    if p.scheme!="https" or not any(host==d or host.endswith("."+d) for d in ALLOWED_DOMAINS):
        raise ValueError("Browser rendering restricted to configured public marketplaces")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Optional Playwright browser not installed") from exc
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True)
        try:
            page=browser.new_page()
            response=page.goto(url,wait_until="domcontentloaded",timeout=timeout_ms)
            if response is None or response.status>=400:
                raise RuntimeError("Browser listing unavailable or blocked")
            page.wait_for_timeout(900)
            content=page.content()
            # Do not treat anti-bot or consent blocks as a listing.
            if any(marker in content.lower() for marker in
                   ("captcha","verify you are human","access denied","toegang geweigerd")):
                raise RuntimeError("Access challenge encountered; not bypassing")
            return content,"text/html"
        finally:
            browser.close()
