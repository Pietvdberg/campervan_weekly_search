"""Shared per-host access stops and bounded request budgets for discovery."""
from urllib.error import HTTPError
from urllib.parse import urlparse
from listing_identity import ExternalRedirect


class SourceStopped(RuntimeError):
    pass


def host_key(url):
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


class SourceFetch:
    def __init__(self, fetcher, maximum_per_host=100):
        self.fetcher = fetcher
        self.maximum_per_host = maximum_per_host
        self.counts = {}
        self.stops = {}

    def __call__(self, url):
        host = host_key(url)
        if host in self.stops:
            raise SourceStopped(self.stops[host]["reason"])
        count = self.counts.get(host, 0)
        if count >= self.maximum_per_host:
            self.stops[host] = {"reason": "Host request budget exhausted", "http_status": None}
            raise SourceStopped(self.stops[host]["reason"])
        self.counts[host] = count + 1
        try:
            return self.fetcher(url)
        except ExternalRedirect as exc:
            self.stops[host] = {"reason": str(exc), "http_status": None}
            raise
        except HTTPError as exc:
            if exc.code in (403, 429):
                self.stops[host] = {"reason": f"HTTP {exc.code}: source access stopped", "http_status": exc.code}
            raise

    def restrictions(self, urls):
        hosts = {host_key(url) for url in urls}
        return {host: self.stops[host] for host in sorted(hosts) if host in self.stops}
