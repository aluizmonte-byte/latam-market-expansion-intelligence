"""Render shareable charts and reports directly from validated model outputs."""
from __future__ import annotations
from datetime import date
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "reports/figures"
REPO = "https://github.com/aluizmonte-byte/latam-market-expansion-intelligence"
ES = {"Brazil": "Brasil", "Mexico": "México", "Chile": "Chile", "Costa Rica": "Costa Rica",
      "Argentina": "Argentina", "Colombia": "Colombia", "Ecuador": "Ecuador",
      "Panama": "Panamá", "Peru": "Perú", "Uruguay": "Uruguay"}
NAVY, TEAL, GREY, INK = "#172D46", "#087F8C", "#BBC6D2", "#24354B"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                     "axes.spines.top": False, "axes.spines.right": False})


def ranking_chart(current, comparison, metadata, spanish=False):
    fig, ax = plt.subplots(figsize=(12, 9), dpi=160)
    fig.patch.set_facecolor("#F6F8FB")
    ax.set_facecolor("#F6F8FB")
    fig.subplots_adjust(left=.17, right=.91, bottom=.22, top=.79)
    y = np.arange(len(current))
    values = current.screening_score.to_numpy()
    colors = [TEAL if r <= 3 else "#B4C2D1" for r in current["rank"]]
    ax.barh(y, values, color=colors, height=.59, zorder=2, label="2025")
    base = comparison.set_index("country_code").loc[current.country_code, "screening_score_2024"].to_numpy()
    ax.scatter(base, y, marker="D", s=40, facecolors="white", edgecolors=NAVY,
               linewidths=1.3, zorder=3, label="2024 · mismo modelo" if spanish else "2024 · same model")
    labels = [ES[n] if spanish else n for n in current.country]
    ax.set_yticks(y, [f"{i+1:02d}  {n}" for i,n in enumerate(labels)], fontsize=12, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks(range(0, 101, 20))
    ax.tick_params(axis="both", length=0, labelcolor=INK)
    ax.grid(axis="x", color="#E0E6ED", linewidth=.7, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#CFD8E2")
    for pos, value in zip(y, values):
        ax.text(max(value, base[pos])+1.6, pos, f"{value:.1f}", va="center", color=INK, fontweight="bold", fontsize=12)
    ax.set_xlabel("Puntuación macroeconómica (0–100)" if spanish else "Macroeconomic screening score (0–100)", color=INK, labelpad=11)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.015), frameon=False, fontsize=10, ncol=2)
    fig.text(.07,.925,"LATAM  /  2025", color=TEAL, fontsize=15, fontweight="bold")
    fig.text(.07,.874,"¿Dónde enfocar la expansión comercial?" if spanish else "Where to focus commercial research?",
             color=NAVY, fontsize=22, fontweight="bold")
    fig.text(.07,.835,"10 países · 5 indicadores comparables · Banco Mundial" if spanish else
             "10 countries · 5 comparable indicators · World Bank", color=INK, fontsize=12)
    fig.text(.07,.125,"Brasil, México y Costa Rica lideran el modelo de 2025." if spanish else
             "Brazil, Mexico and Costa Rica lead the 2025 model.", color=NAVY, fontsize=13, fontweight="bold")
    note = ("Comparación 2024–2025 con los mismos indicadores, pesos y escala.\n"
            "El modelo excluye inflación, apertura comercial y uso de internet por cobertura incompleta.\n"
            "Selección inicial de mercados; requiere validación sectorial y comercial."
            if spanish else
            "2024–2025 comparison uses identical indicators, weights and scale.\n"
            "Inflation, trade openness and internet use are excluded because of incomplete coverage.\n"
            "An initial market screen requiring sector and commercial validation.")
    fig.text(.07,.045,note, color="#52657A", fontsize=9, linespacing=1.7)
    retrieved = ", ".join(metadata["source_retrieval_dates"])
    fig.text(.93,.018,("Fuente: WDI · Consulta: " if spanish else "Source: WDI · Retrieved: ")+retrieved+
             "  |  André Monte", ha="right", color="#64768A", fontsize=8)
    name = "linkedin_2025_es.png" if spanish else "market_screening_2025.png"
    fig.savefig(FIGURES/name, facecolor=fig.get_facecolor())
    plt.close(fig)


def change_chart(comparison):
    frame = comparison.sort_values("score_change_points", ascending=False)
    fig, ax = plt.subplots(figsize=(11,7.5),dpi=160)
    fig.subplots_adjust(left=.17,right=.88,top=.8,bottom=.19)
    y=np.arange(len(frame))
    values=frame.score_change_points.to_numpy()
    ax.barh(y, values, color=[TEAL if v>=0 else "#BE6B40" for v in values],height=.6)
    ax.set_yticks(y,frame.country)
    ax.invert_yaxis()
    ax.axvline(0,color=INK,linewidth=.8)
    ax.set_xlim(-10,30)
    ax.grid(axis="x",alpha=.2)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    for pos,value in zip(y,values):
        ax.text(value+(.5 if value>=0 else -.5),pos,f"{value:+.1f}",ha="left" if value>=0 else "right",va="center",fontsize=11)
    ax.set_xlabel("Change in comparable screening score (points)")
    fig.text(.07,.925,"What changed from 2024 to 2025?",fontsize=21,color=NAVY,fontweight="bold")
    fig.text(.07,.865,"Same five indicators, weights and pooled calibration for both years.",color=INK,fontsize=11)
    fig.text(.07,.07,"Score movements reflect this model, not changes in sales or investment returns.\n"
             "Argentina's rebound is visible; inflation and other operating risks are outside this score.",
             color="#52657A",fontsize=9,linespacing=1.7)
    fig.savefig(FIGURES/"score_change_2024_2025.png")
    plt.close(fig)


def render_all(current, comparison, sens, legacy, metadata, coverage):
    ranking_chart(current,comparison,metadata)
    ranking_chart(current,comparison,metadata,spanish=True)
    change_chart(comparison)
    merged = comparison.merge(sens[["country_code","top3_share"]],on="country_code",validate="one_to_one")
    rows = "\n".join(
        f"| {int(r.rank_2025)} | {r.country} | {r.screening_score_2025:.1f} | {r.screening_score_2024:.1f} | {r.score_change_points:+.1f} | {r.top3_share:.1%} |"
        for r in merged.itertuples())
    table = "| Rank 2025 | Market | Score 2025 | Comparable score 2024 | Change (pts) | Top-3 scenario share |\n|---:|---|---:|---:|---:|---:|\n"+rows
    retrieved = ", ".join(metadata["source_retrieval_dates"])
    source_updated = ", ".join(metadata["source_api_last_updated"])
    cover_rows = "\n".join(f"| {r.indicator} | {r.available}/10 | {'Included' if r.included_in_core5 else 'Excluded uniformly'} | {r.missing_country_codes or 'None'} |"
        for r in coverage.loc[coverage.year.eq(2025)].itertuples())
    coverage_text = "| Indicator | 2025 coverage | Core model | Missing country codes |\n|---|---:|---|---|\n"+cover_rows
    body = f"""# LATAM Market Expansion Intelligence — 2025 update

Macroeconomic screening of ten Latin American markets, with a like-for-like 2024 comparison.

**Reference year: 2025 · Source retrieved: {retrieved} · Analysis updated: {metadata['analysis_updated_on']}**

![2025 market screening](reports/figures/market_screening_2025.png)

## Business question

Which markets should enter the first stage of commercial expansion research, based on comparable public data?

## What the updated model says

**Brazil, Mexico and Costa Rica lead the five-indicator 2025 screening.** They also occupy the top three places in the comparable five-indicator 2024 baseline. The original eight-indicator 2024 model remains available as a historical view.

{table}

Top-3 scenario share is the proportion of 2,000 alternative weight combinations that put a country in the top three. It is **not** the probability of business success.

## Why this update uses five indicators

The eight-series source extract contains 68 of the 80 possible observations for 2025. Five indicators have full coverage for every country in both 2024 and 2025:

| Indicator | Role | Weight |
|---|---|---:|
| GDP, current USD | Economic scale | 30.77% |
| Real GDP growth | Growth momentum | 23.08% |
| GDP per capita, current USD | Average-income proxy | 15.38% |
| Population | Population scale | 15.38% |
| FDI net inflows / GDP | Foreign-capital flows | 15.38% |

Weights are the original weights renormalized from a retained total of 65%; rounding accounts for any displayed sum discrepancy. No country is scored with a different set of variables. No gaps are filled with earlier-year values.

{coverage_text}

Inflation, trade openness and internet use remain in the source data and coverage audit. They are excluded from **both** years of the comparable score. Accordingly, this version is a narrower macroeconomic screen, and it does not measure commercial accessibility or price stability.

## A fair comparison across years

Both years use the same five indicators, weights and normalization bounds. The bounds are the 5th and 95th percentiles of the pooled 20 country-year observations (10 markets × 2 years). Values are clipped to those bounds and scaled to 0–100.

![Change in comparable score](reports/figures/score_change_2024_2025.png)

The five-indicator 2024 score was recalculated for this comparison. **Do not compare the new 2025 scores directly with the original eight-indicator 2024 scores.** Differences between those models also reflect the indicator selection, weights and normalization.

## Commercial interpretation

- **Brazil** leads in this model, with economic and population scale contributing strongly.
- **Mexico** remains second, while its comparable score declines; the recorded real GDP growth rate falls from 1.35% in 2024 to 0.56% in 2025.
- **Costa Rica** remains third under the common five-indicator specification; growth and FDI relative to GDP support its position.
- **Argentina** moves from ninth to fourth in the comparable model as recorded GDP growth rebounds from -1.34% to 4.37%. Inflation is excluded from this score, so the improvement is not a conclusion about operating risk.

These are prompts for sector and customer research, not a market-entry recommendation.

## Reproduce

Python 3.11+ is required by the pinned NumPy version. Validated with Python 3.12.

```bash
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt

# Offline: use the committed, checksummed source snapshot
python src/build_analysis.py
python -m unittest discover tests -v

# Optional: explicitly download a new official source snapshot
python src/build_analysis.py --refresh
```

The default build never changes the source retrieval date. The source manifest stores the acquisition date, source URL and CSV checksum for each series. This release uses the previously committed source snapshot from 21 September 2026. A fresh batch download attempted on 30 September timed out, so it did not replace that snapshot. The public WDI release listing was checked on 30 September and still listed the 13 July 2026 update. A successful future refresh also archives the raw JSON responses and exact acquisition timestamps.

The release is fixed to 2024–2025. A later reference year requires an explicit methodology update and coverage check.

## Files to explore

- [Executive summary](reports/executive_summary.md)
- [Method, weights and data dictionary](docs/data_dictionary.md)
- [2025 ranking](data/processed/market_screening_2025.csv)
- [Comparable 2024–2025 results](data/processed/market_screening_comparison_2024_2025.csv)
- [Coverage audit](data/processed/data_coverage_2024_2025.csv)
- [Source manifest](data/raw/source_manifest.json)
- [Review notebook](notebooks/executive_analysis.ipynb)
- [Spanish LinkedIn image](reports/figures/linkedin_2025_es.png)
- [Spanish LinkedIn text and publishing steps](docs/linkedin_post_es.md)
- [Historical eight-indicator model](reports/historical_2024.md)

## Limits

This is a relative screening model for the ten selected countries. It excludes sector demand, competition, regulation, taxes, security, route-to-market costs and product-market fit. The current score also excludes inflation, trade openness and digital reach. GDP and population overlap as scale proxies; these weights reflect a strategy choice. GDP and GDP per capita in current USD are affected by exchange rates and prices, and should not be read as real growth or purchasing-power parity.

Published WDI observations can contain official estimates and may be revised. This project adds no invented data, forecasts or missing-value imputations. The sensitivity analysis varies weights within the chosen model; it does not test all possible indicator sets or quantify statistical confidence. Pooled scaling is for retrospective comparison, not an out-of-sample forecast.

## Source

[World Bank — WDI API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation).
Source retrieved: **{retrieved}**. API-reported dataset update: **{source_updated}**.
[Official July 2026 release note](https://datatopics.worldbank.org/world-development-indicators/release-note/jul-2026.html) confirms publication of 2025 national-accounts and population data.

Code: MIT license. World Bank source data remain subject to their [dataset terms](https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators).

## Author

André Luiz Monte — Commercial Leadership · Business Development · Data Analytics
"""
    (ROOT/"README.md").write_text(body,encoding="utf-8")
    summary=f"""# Executive summary — 2025 update

## Decision context

This is an initial macroeconomic screen for commercial expansion across ten Latin American countries. Source retrieved {retrieved}; observations refer to 2025.

**Brazil, Mexico and Costa Rica lead the 2025 five-indicator model.** The same countries lead the comparable 2024 model.

{table}

## Reading the result

Brazil's scale contributes strongly to its lead. Mexico remains second despite slower reported GDP growth (1.35% to 0.56%). Costa Rica remains third, supported by growth and FDI relative to GDP.

Argentina moves from ninth to fourth under this same five-indicator model, with GDP growth rebounding from -1.34% to 4.37%. Because inflation is excluded, this is not an assessment of macroeconomic stability or business-entry risk.

These country positions should organize the next research step: validate sector demand, target customers, competition and routes to market. The score does not estimate revenues, conversion rates or return on investment.

## What changed in the method

The current model uses GDP, real GDP growth, GDP per capita, population and FDI/GDP. All five have complete observations for all ten countries in 2024 and 2025. Their original weights were renormalized from 65% to 100%. The same pooled normalization is applied to both years.

Internet use has no 2025 observations for these countries, inflation is missing for Argentina, and trade openness is missing for Panama in this source snapshot. All three variables are excluded uniformly, rather than filling gaps or using different models by country.

The old 2024 eight-indicator ranking (Mexico, Brazil, Chile) is a different model. Its difference from the new ranking must not be attributed entirely to economic changes over time.

## Robustness and limits

The top-three shares describe 2,000 alternative weight scenarios (Dirichlet concentration 100, seed 42), not business-success probabilities or confidence levels. The analysis does not include sector demand, competition, regulation, taxes, security, local distribution costs or product-market fit. It also omits inflation, trade openness and digital reach from the current score.

See the [methodology](../docs/data_dictionary.md), [coverage audit](../data/processed/data_coverage_2024_2025.csv), and [source manifest](../data/raw/source_manifest.json).
"""
    (ROOT/"reports/executive_summary.md").write_text(summary,encoding="utf-8")
    legacy_rows="\n".join(f"| {int(r.rank)} | {r.country} | {r.opportunity_score:.1f} |" for r in legacy.itertuples())
    historical=f"""# Historical reference — 2024 eight-indicator model

This is the original model specification, retained for transparency. It uses eight indicators and year-specific 2024 normalization. It is **not directly comparable** to the five-indicator 2025 model or its recalculated 2024 baseline.

| Rank | Country | Original model score |
|---:|---|---:|
{legacy_rows}

![Historical ranking](figures/market_opportunity_ranking.png)
![Historical attractiveness and accessibility](figures/attractiveness_accessibility_matrix.png)

The historical outputs remain at [market_opportunity_ranking.csv](../data/processed/market_opportunity_ranking.csv) and [weight_sensitivity.csv](../data/processed/weight_sensitivity.csv). In the historical schema, top3_probability means the share of weight scenarios, not probability of commercial success.

The current source snapshot may revise historical values. The original September 2026 release is also preserved in Git history.
"""
    (ROOT/"reports/historical_2024.md").write_text(historical,encoding="utf-8")
