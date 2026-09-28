"""Download World Bank data and build the LATAM opportunity ranking."""
from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "reports" / "figures"

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

WEIGHTS = {
    "gdp_usd": 0.20,
    "gdp_growth_pct": 0.15,
    "gdp_per_capita_usd": 0.10,
    "population": 0.10,
    "internet_users_pct": 0.15,
    "trade_pct_gdp": 0.15,
    "fdi_net_inflows_pct_gdp": 0.10,
    "inflation_pct": 0.05,
}


def fetch_indicator(code: str, slug: str) -> pd.DataFrame:
    cache = RAW / f"{slug}.csv"
    if cache.exists():
        return pd.read_csv(cache)
    params = urlencode({"format": "json", "per_page": 2000, "date": "2015:2025"})
    url = f"https://api.worldbank.org/v2/country/{';'.join(COUNTRIES)}/indicator/{code}?{params}"
    last_error = None
    for attempt in range(4):
        try:
            with urlopen(url, timeout=90) as response:
                payload = json.load(response)
            break
        except (TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    else:
        raise RuntimeError(f"World Bank API failed for {code}") from last_error
    rows = payload[1] or []
    data = pd.DataFrame({
        "country_code": r["countryiso3code"],
        "country": COUNTRIES[r["countryiso3code"]],
        "year": int(r["date"]),
        "indicator": slug,
        "indicator_code": code,
        "value": r["value"],
    } for r in rows if r["countryiso3code"] in COUNTRIES)
    data.to_csv(cache, index=False)
    return data


def winsorized_minmax(series: pd.Series, inverse: bool = False) -> pd.Series:
    lo, hi = series.quantile([0.05, 0.95])
    clipped = series.clip(lo, hi)
    span = clipped.max() - clipped.min()
    score = pd.Series(50.0, index=series.index) if span == 0 else 100 * (clipped - clipped.min()) / span
    return 100 - score if inverse else score


def main() -> None:
    for folder in (RAW, PROCESSED, FIGURES):
        folder.mkdir(parents=True, exist_ok=True)

    history = pd.concat([fetch_indicator(code, slug) for slug, code in INDICATORS.items()])
    history.to_csv(PROCESSED / "indicator_history_2015_2025.csv", index=False)

    # Latest year with complete coverage across every country and indicator.
    coverage = (history.dropna(subset=["value"])
                .groupby("year").agg(countries=("country_code", "nunique"), indicators=("indicator", "nunique"), rows=("value", "size")))
    complete = coverage[(coverage.countries == len(COUNTRIES)) &
                        (coverage.indicators == len(INDICATORS)) &
                        (coverage.rows == len(COUNTRIES) * len(INDICATORS))]
    if complete.empty:
        raise RuntimeError("No common complete year across all countries and indicators.")
    reference_year = int(complete.index.max())

    snapshot = (history[history.year == reference_year]
                .pivot(index=["country_code", "country"], columns="indicator", values="value")
                .reset_index())
    for indicator in INDICATORS:
        snapshot[f"score_{indicator}"] = winsorized_minmax(
            snapshot[indicator], inverse=(indicator == "inflation_pct")
        )

    snapshot["market_attractiveness"] = (
        0.20 * snapshot.score_gdp_usd +
        0.15 * snapshot.score_gdp_growth_pct +
        0.10 * snapshot.score_gdp_per_capita_usd +
        0.10 * snapshot.score_population
    ) / 0.55
    snapshot["commercial_accessibility"] = (
        0.15 * snapshot.score_internet_users_pct +
        0.15 * snapshot.score_trade_pct_gdp +
        0.10 * snapshot.score_fdi_net_inflows_pct_gdp +
        0.05 * snapshot.score_inflation_pct
    ) / 0.45
    snapshot["opportunity_score"] = sum(
        WEIGHTS[k] * snapshot[f"score_{k}"] for k in WEIGHTS
    )
    snapshot["rank"] = snapshot.opportunity_score.rank(ascending=False, method="min").astype(int)
    snapshot = snapshot.sort_values("rank")
    snapshot["segment"] = pd.cut(
        snapshot["rank"], bins=[0, 3, 5, 8, 10],
        labels=["Priority Market", "Growth Bet", "Selective Opportunity", "Monitor"]
    ).astype(str)
    snapshot.to_csv(PROCESSED / "market_opportunity_ranking.csv", index=False)

    # Weight sensitivity: 2,000 Dirichlet draws centered around the documented weights.
    rng = np.random.default_rng(42)
    keys = list(WEIGHTS)
    draws = rng.dirichlet(np.array(list(WEIGHTS.values())) * 100, size=2000)
    matrix = snapshot[[f"score_{k}" for k in keys]].to_numpy()
    simulated = matrix @ draws.T
    sensitivity = pd.DataFrame({
        "country": snapshot.country,
        "base_rank": snapshot["rank"],
        "mean_score": simulated.mean(axis=1),
        "score_p10": np.quantile(simulated, 0.10, axis=1),
        "score_p90": np.quantile(simulated, 0.90, axis=1),
        "top3_probability": (simulated.argsort(axis=0).argsort(axis=0) >= len(snapshot) - 3).mean(axis=1),
    }).sort_values("base_rank")
    sensitivity.to_csv(PROCESSED / "weight_sensitivity.csv", index=False)

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(10, 6))
    plot = snapshot.sort_values("opportunity_score")
    sns.barplot(data=plot, x="opportunity_score", y="country", hue="segment", dodge=False, ax=ax)
    ax.set(title=f"LATAM Market Opportunity Ranking ({reference_year})", xlabel="Opportunity score (0–100)", ylabel="")
    ax.legend(title="Segment", loc="lower right")
    fig.tight_layout()
    fig.savefig(FIGURES / "market_opportunity_ranking.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 7))
    palette = {"Priority Market": "#2463A7", "Growth Bet": "#E07A3F",
               "Selective Opportunity": "#3A9D5D", "Monitor": "#C64040"}
    size = 80 + 820 * snapshot.gdp_usd / snapshot.gdp_usd.max()
    for segment, group in snapshot.groupby("segment", sort=False):
        ax.scatter(group.commercial_accessibility, group.market_attractiveness,
                   s=size.loc[group.index], color=palette[segment], alpha=0.88,
                   edgecolor="white", linewidth=0.8, label=segment)
    for row in snapshot.itertuples():
        ax.annotate(row.country, (row.commercial_accessibility, row.market_attractiveness),
                    xytext=(5, 4), textcoords="offset points", fontsize=8)
    ax.axvline(snapshot.commercial_accessibility.median(), color="grey", linestyle="--", linewidth=1)
    ax.axhline(snapshot.market_attractiveness.median(), color="grey", linestyle="--", linewidth=1)
    ax.set(title=f"Market Attractiveness × Commercial Accessibility ({reference_year})",
           xlabel="Commercial accessibility (0–100)", ylabel="Market attractiveness (0–100)")
    ax.legend(title="Segment", loc="lower right", frameon=True)
    fig.tight_layout()
    fig.savefig(FIGURES / "attractiveness_accessibility_matrix.png", dpi=180)
    plt.close(fig)

    metadata = {
        "reference_year": reference_year,
        "data_retrieved_on": str(pd.Timestamp.today().date()),
        "countries": COUNTRIES,
        "indicators": INDICATORS,
        "weights": WEIGHTS,
        "method": "5th/95th percentile winsorization, min-max normalization, weighted sum",
    }
    (PROCESSED / "analysis_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(snapshot[["rank", "country", "opportunity_score", "segment"]].to_string(index=False))
    print(f"\nReference year: {reference_year}")


if __name__ == "__main__":
    main()
