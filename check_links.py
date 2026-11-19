"""
check_links.py: finds every https link in the app and data files and checks that it still opens.

Run it every month or two, because links go out of date:   python check_links.py
It uses curl (already on Mac and Linux) so it behaves like a real browser request.
Exit code 1 means at least one link is broken.
"""

import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["app.py", "jarvis_engine.py", "jarvis_ui.py", "organisations.csv", "resources.csv"]
SKIP = ("api.postcodes.io", "www.w3.org")          # an API endpoint and XML namespaces, not pages
UA = "Mozilla/5.0 (compatible; mh-navigator-linkcheck)"


def find_links():
    links = set()
    for name in FILES:
        path = os.path.join(HERE, name)
        if os.path.exists(path):
            text = open(path, encoding="utf-8").read()
            for url in re.findall(r"https://[^\s\"'<>)\]},]+", text):
                url = url.rstrip(".;:")
                if "{" not in url and not any(s in url for s in SKIP):
                    links.add(url)
    return sorted(links)


def check(url):
    try:
        out = subprocess.run(
            ["curl", "-s", "-L", "-o", "/dev/null", "--max-time", "25", "-A", UA,
             "-w", "%{http_code} %{url_effective}", url],
            capture_output=True, text=True, timeout=40).stdout.strip()
        code, _, final = out.partition(" ")
        return url, code, final
    except Exception as err:  # curl missing or timed out
        return url, "ERR", type(err).__name__


def main():
    links = find_links()
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(check, links))
    broken = [(u, c, f) for u, c, f in results if c not in ("200", "403")]
    blocked = [(u, c, f) for u, c, f in results if c == "403"]
    print(f"Checked {len(results)} links: {len(results) - len(broken) - len(blocked)} fine, "
          f"{len(blocked)} refuse automated checks (open by hand), {len(broken)} broken.")
    for url, code, final in blocked:
        print(f"  CHECK BY HAND (403)  {url}")
    for url, code, final in broken:
        print(f"  BROKEN ({code})  {url}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
