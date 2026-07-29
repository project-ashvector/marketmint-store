#!/usr/bin/env python3
import argparse
import json
import urllib.parse
import urllib.request
from html.parser import HTMLParser


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ("href", "src"):
            if values.get(key):
                self.links.append(values[key])


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "MarketMint-Site-Health/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return int(getattr(response, "status", 200)), response.read(3_000_000), str(response.headers.get("Content-Type") or "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    args = parser.parse_args()
    base = args.url.rstrip("/")
    failures = []
    checked = []
    for path in ("/", "/mobile-build.json", "/sitemap.xml", "/fallback-products.json"):
        try:
            status, body, content_type = fetch(base + path)
            checked.append({"path": path, "status": status, "bytes": len(body), "content_type": content_type})
            if status != 200 or not body:
                failures.append(f"{path} returned {status} or an empty response")
        except Exception as exc:
            failures.append(f"{path}: {exc}")
    try:
        _, body, _ = fetch(base + "/")
        page = body.decode("utf-8", errors="ignore")
        if "viewport" not in page:
            failures.append("Homepage is missing mobile viewport metadata")
        parser2 = Links()
        parser2.feed(page)
        if any("index.html" in value for value in parser2.links):
            failures.append("Homepage contains an index.html link")
        internal = []
        for value in parser2.links:
            if value.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
                continue
            url = urllib.parse.urljoin(base + "/", value)
            if urllib.parse.urlparse(url).hostname == urllib.parse.urlparse(base).hostname and url not in internal:
                internal.append(url)
        for url in internal[:40]:
            try:
                status, _, _ = fetch(url)
                if status >= 400:
                    failures.append(f"Broken internal URL: {url} ({status})")
            except Exception as exc:
                failures.append(f"Broken internal URL: {url} ({exc})")
    except Exception as exc:
        failures.append(f"Homepage inspection failed: {exc}")
    report = {"ok": not failures, "base": base, "checked": checked, "failures": failures}
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
