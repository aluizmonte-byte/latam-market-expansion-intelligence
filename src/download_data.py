"""Refresh the eight official WDI series and record source provenance."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
COUNTRIES = {
    "ARG": "Argentina", "BRA": "Brazil", "CHL": "Chile", "COL": "Colombia",
    "CRI": "Costa Rica", "ECU": "Ecuador", "MEX": "Mexico", "PAN": "Panama",
    "PER": "Peru", "URY": "Uruguay",
}
INDICATORS = {
    "gdp_usd": "NY.GDP.MKTP.CD",
    "gdp_growth_pct": "NY.GDP.MKTP.KD.ZG",
    "gdp_per_capita_usd": "NY.GDP.PCAP.CD",
    "population": "SP.POP.TOTL",
    "internet_users_pct": "IT.NET.USER.ZS",
    "trade_pct_gdp": "NE.TRD.GNFS.ZS",
    "fdi_net_inflows_pct_gdp": "BX.KLT.DINV.WD.GD.ZS",
    "inflation_pct": "FP.CPI.TOTL.ZG",
}


def download_series(item: tuple[str, str]) -> tuple[str, pd.DataFrame, dict, str]:
    slug, code = item
    query = urlencode({"format": "json", "per_page": 2000, "date": "2015:2025"})
    url = f"https://api.worldbank.org/v2/country/{';'.join(COUNTRIES)}/indicator/{code}?{query}"
    with urlopen(url, timeout=45) as response:
        payload = json.load(response)
    if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[0], dict):
        raise ValueError(f"Unexpected API response for {code}")
    if int(payload[0].get("pages", 0)) != 1:
        raise ValueError(f"Incomplete pagination for {code}")
    data = pd.DataFrame({
        "country_code": r["countryiso3code"],
        "country": COUNTRIES[r["countryiso3code"]],
        "year": int(r["date"]),
        "indicator": slug,
        "indicator_code": code,
        "value": r["value"],
    } for r in payload[1] if r["countryiso3code"] in COUNTRIES)
    if len(data) != 110 or data.duplicated(["country_code", "year"]).any():
        raise ValueError(f"Expected 10 countries x 11 years for {code}")
    provenance = {
        "indicator_code": code,
        "url": url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "retrieved_on": str(datetime.now(timezone.utc).date()),
        "api_last_updated": payload[0].get("lastupdated"),
        "rows": len(data),
        "non_null_2025": int(data.loc[data.year.eq(2025), "value"].notna().sum()),
    }
    return slug, data, provenance, json.dumps(payload, ensure_ascii=False, indent=2)


def main() -> None:
    # Fetch every response before replacing any committed extract.
    with ThreadPoolExecutor(max_workers=4) as executor:
        downloaded = list(executor.map(download_series, INDICATORS.items()))
    (RAW / "api_responses").mkdir(parents=True, exist_ok=True)
    sources = {}
    for slug, frame, provenance, payload in downloaded:
        path = RAW / f"{slug}.csv"
        frame.to_csv(path, index=False)
        provenance["csv_sha256"] = sha256(path.read_bytes()).hexdigest()
        (RAW / "api_responses" / f"{slug}.json").write_text(payload + "\n", encoding="utf-8")
        sources[slug] = provenance
    manifest = {
        "provider": "World Bank — World Development Indicators",
        "observation_window": "2015:2025",
        "sources": sources,
        "note": "Published source observations; these may include official estimates and revisions. No project-generated forecasts or gap filling.",
    }
    (RAW / "source_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for slug, _, provenance, _ in downloaded:
        print(f"{slug}: {provenance['non_null_2025']}/10 available for 2025; API updated {provenance['api_last_updated']}")


if __name__ == "__main__":
    main()
