"""Downloads the latest NHS IAPT monthly CSV. Placeholder URL — update
each month's filename from digital.nhs.uk publication page."""
import requests, pathlib
URL = "https://files.digital.nhs.uk/PLACEHOLDER/iapt-monthly.csv"
out = pathlib.Path("data/iapt_latest.csv")
try:
    r = requests.get(URL, timeout=60)
    r.raise_for_status()
    out.write_bytes(r.content)
    print("Downloaded", len(r.content), "bytes")
except Exception as e:
    print("Download skipped:", e)
