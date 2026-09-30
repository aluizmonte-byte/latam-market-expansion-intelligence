"""Reproduce the core-five 2025 screening and its comparable 2024 baseline.

Run offline from committed extracts by default; --refresh downloads official WDI data.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
import pandas as pd
from download_data import COUNTRIES, INDICATORS

ROOT = Path(__file__).resolve().parents[1]
RAW, PROCESSED, FIGURES = ROOT / "data/raw", ROOT / "data/processed", ROOT / "reports/figures"
BASE_YEAR, CURRENT_YEAR = 2024, 2025
MODEL_ID = "core5-pooled-2024-2025-v1"
WEIGHTS = {
    "gdp_usd": .20, "gdp_growth_pct": .15, "gdp_per_capita_usd": .10,
    "population": .10, "internet_users_pct": .15, "trade_pct_gdp": .15,
    "fdi_net_inflows_pct_gdp": .10, "inflation_pct": .05,
}
CORE_KEYS = ("gdp_usd", "gdp_growth_pct", "gdp_per_capita_usd", "population", "fdi_net_inflows_pct_gdp")
CORE_WEIGHTS = {k: WEIGHTS[k] / sum(WEIGHTS[v] for v in CORE_KEYS) for k in CORE_KEYS}


def validate_history(history: pd.DataFrame) -> None:
    keys = ["country_code", "indicator", "year"]
    if history.duplicated(keys).any():
        raise ValueError("Duplicate country/indicator/year observations.")
    expected = pd.MultiIndex.from_product([list(COUNTRIES), list(INDICATORS), range(2015, 2026)], names=keys)
    actual = pd.MultiIndex.from_frame(history[keys])
    if len(expected.difference(actual)) or len(actual.difference(expected)):
        raise ValueError("Expected every source key, including explicit null observations.")
    for row in history[["country_code", "country", "indicator", "indicator_code"]].drop_duplicates().itertuples():
        if COUNTRIES[row.country_code] != row.country or INDICATORS[row.indicator] != row.indicator_code:
            raise ValueError("Source identifiers do not match the documented dictionary.")
    if not np.isfinite(history.value.dropna().to_numpy()).all():
        raise ValueError("Non-finite source values.")


def load_sources() -> tuple[pd.DataFrame, dict]:
    manifest = json.loads((RAW / "source_manifest.json").read_text(encoding="utf-8"))
    for key in INDICATORS:
        if sha256((RAW / f"{key}.csv").read_bytes()).hexdigest() != manifest["sources"][key]["csv_sha256"]:
            raise ValueError(f"Source checksum mismatch: {key}")
    history = pd.concat([pd.read_csv(RAW / f"{key}.csv") for key in INDICATORS], ignore_index=True)
    validate_history(history)
    return history, manifest


def scale(series: pd.Series, lo: float, hi: float, inverse: bool = False) -> pd.Series:
    if series.isna().any():
        raise ValueError("Missing observations cannot be scored.")
    score = pd.Series(50.0, index=series.index) if hi == lo else 100 * (series.clip(lo, hi) - lo) / (hi - lo)
    return 100 - score if inverse else score


def sensitivity(frame: pd.DataFrame, weights: dict, score_column: str) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    draws = rng.dirichlet(np.array(list(weights.values())) * 100, size=2000)
    simulated = frame[[f"score_{key}" for key in weights]].to_numpy() @ draws.T
    return pd.DataFrame({
        "country_code": frame.country_code.to_numpy(), "country": frame.country.to_numpy(),
        "base_rank": frame["rank"].to_numpy(), "base_score": frame[score_column].to_numpy(),
        "mean_score": simulated.mean(axis=1),
        "score_p10": np.quantile(simulated, .10, axis=1),
        "score_p90": np.quantile(simulated, .90, axis=1),
        "top3_share": (simulated.argsort(axis=0).argsort(axis=0) >= len(frame) - 3).mean(axis=1),
    }).sort_values("base_rank")


def coverage_table(history: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year in (BASE_YEAR, CURRENT_YEAR):
        for key in INDICATORS:
            part = history.loc[history.year.eq(year) & history.indicator.eq(key)]
            rows.append({
                "year": year, "indicator": key, "indicator_code": INDICATORS[key],
                "available": int(part.value.notna().sum()), "expected": len(COUNTRIES),
                "missing_country_codes": ";".join(part.loc[part.value.isna(), "country_code"].sort_values()),
                "included_in_core5": key in CORE_KEYS,
            })
    return pd.DataFrame(rows)


def build_current(history: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    chosen = history.loc[history.year.isin([BASE_YEAR, CURRENT_YEAR]) & history.indicator.isin(CORE_KEYS)]
    panel = chosen.pivot(index=["year", "country_code", "country"], columns="indicator", values="value").reset_index()
    if len(panel) != 20 or panel[list(CORE_KEYS)].isna().any().any():
        raise ValueError("The core model requires all 100 observations across the two years.")
    parameters = {}
    for key in CORE_KEYS:
        # Identical ruler for both years, fitted on the pooled twenty observations.
        lo, hi = panel[key].quantile([.05, .95])
        parameters[key] = {"p05": float(lo), "p95": float(hi), "weight": CORE_WEIGHTS[key]}
        panel[f"score_{key}"] = scale(panel[key], lo, hi)
    panel["screening_score"] = sum(CORE_WEIGHTS[k] * panel[f"score_{k}"] for k in CORE_KEYS)
    panel["rank"] = panel.groupby("year")["screening_score"].rank(ascending=False, method="min").astype(int)
    panel = panel.sort_values(["year", "rank", "country_code"])
    current = panel.loc[panel.year.eq(CURRENT_YEAR)].copy()
    base = panel.loc[panel.year.eq(BASE_YEAR), ["country_code", "rank", "screening_score"]]
    comparison = base.merge(current[["country_code", "country", "rank", "screening_score"]],
                            on="country_code", validate="one_to_one", suffixes=("_2024", "_2025"))
    comparison["score_change_points"] = comparison.screening_score_2025 - comparison.screening_score_2024
    comparison["rank_change"] = comparison["rank_2024"] - comparison["rank_2025"]
    return panel, current, comparison.sort_values("rank_2025"), parameters


def build_legacy(history: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    snapshot = history.loc[history.year.eq(BASE_YEAR)].pivot(
        index=["country_code", "country"], columns="indicator", values="value").reset_index()
    if snapshot[list(INDICATORS)].isna().any().any():
        raise ValueError("The eight-indicator historical model needs complete 2024 observations.")
    for key in INDICATORS:
        lo, hi = snapshot[key].quantile([.05, .95])
        snapshot[f"score_{key}"] = scale(snapshot[key], lo, hi, inverse=(key == "inflation_pct"))
    snapshot["market_attractiveness"] = sum(WEIGHTS[k] * snapshot[f"score_{k}"] for k in CORE_KEYS[:4]) / .55
    access = ("internet_users_pct", "trade_pct_gdp", "fdi_net_inflows_pct_gdp", "inflation_pct")
    snapshot["commercial_accessibility"] = sum(WEIGHTS[k] * snapshot[f"score_{k}"] for k in access) / .45
    snapshot["opportunity_score"] = sum(WEIGHTS[k] * snapshot[f"score_{k}"] for k in WEIGHTS)
    snapshot["rank"] = snapshot.opportunity_score.rank(ascending=False, method="min").astype(int)
    snapshot = snapshot.sort_values("rank")
    snapshot["segment"] = pd.cut(snapshot["rank"], [0, 3, 5, 8, 10],
        labels=["Priority Market", "Growth Bet", "Selective Opportunity", "Monitor"]).astype(str)
    old_sensitivity = sensitivity(snapshot, WEIGHTS, "opportunity_score").rename(columns={"top3_share": "top3_probability"})
    return snapshot, old_sensitivity


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Download official WDI sources first.")
    args = parser.parse_args()
    if args.refresh:
        from download_data import main as refresh
        refresh()
    for folder in (PROCESSED, FIGURES):
        folder.mkdir(parents=True, exist_ok=True)
    history, manifest = load_sources()
    panel, current, comparison, parameters = build_current(history)
    coverage = coverage_table(history)
    current_sensitivity = sensitivity(current, CORE_WEIGHTS, "screening_score")
    legacy, legacy_sensitivity = build_legacy(history)
    outputs = {
        "indicator_history_2015_2025.csv": history,
        "data_coverage_2024_2025.csv": coverage,
        "market_screening_panel_2024_2025.csv": panel,
        "market_screening_2025.csv": current,
        "market_screening_comparison_2024_2025.csv": comparison,
        "weight_sensitivity_2025.csv": current_sensitivity,
        "market_opportunity_ranking.csv": legacy,
        "weight_sensitivity.csv": legacy_sensitivity,
    }
    for name, frame in outputs.items():
        frame.to_csv(PROCESSED / name, index=False)
    (PROCESSED / "scaling_parameters_2024_2025.json").write_text(json.dumps(parameters, indent=2) + "\n", encoding="utf-8")
    dates = sorted({s.get("retrieved_on") or s["retrieved_at_utc"][:10] for s in manifest["sources"].values()})
    metadata = {
        "model_id": MODEL_ID, "reference_year": CURRENT_YEAR, "comparison_year": BASE_YEAR,
        "analysis_updated_on": str(datetime.now(timezone.utc).date()),
        "source_retrieval_dates": dates,
        "source_api_last_updated": sorted({s["api_last_updated"] for s in manifest["sources"].values()}),
        "countries": COUNTRIES, "core_indicators": {k: INDICATORS[k] for k in CORE_KEYS},
        "core_weights": CORE_WEIGHTS,
        "excluded_from_current_score": [k for k in INDICATORS if k not in CORE_KEYS],
        "scaling": "Pooled 5th/95th percentiles across 10 countries x 2 years; identical bounds and weights for 2024 and 2025.",
        "imputation": "None. No forward fill, synthetic observations, or project forecasts.",
        "sensitivity": {"draws": 2000, "seed": 42, "dirichlet_concentration": 100,
            "interpretation": "Scenario share conditional on weights and model; not business-success probability."},
        "legacy_model": {"reference_year": BASE_YEAR, "indicators": INDICATORS, "weights": WEIGHTS,
            "ranking_file": "market_opportunity_ranking.csv",
            "note": "Eight-indicator historical model; scores and ranks are not directly comparable to core5."},
    }
    (PROCESSED / "analysis_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    from render_reports import render_all
    render_all(current, comparison, current_sensitivity, legacy, metadata, coverage)
    print(current[["rank", "country", "screening_score"]].to_string(index=False))
    print("\nLike-for-like comparison:\n", comparison.to_string(index=False))
    print("\nSource retrieval dates:", ", ".join(dates))


if __name__ == "__main__":
    main()
