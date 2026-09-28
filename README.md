# LATAM Market Expansion Intelligence

Data-driven market prioritization for commercial expansion across ten Latin American economies.

![Market opportunity ranking](reports/figures/market_opportunity_ranking.png)

## Business question

> If an international company had to prioritize three Latin American markets for commercial expansion, which countries should enter the pipeline first — and why?

## Key finding

For the latest complete common year (**2024**), the model identifies **Mexico, Brazil, and Chile** as Priority Markets. Mexico has the most balanced profile; Brazil leads on market attractiveness; Chile leads on commercial accessibility. Costa Rica is the main challenger when strategic weights change.

| Rank | Market | Score | Segment | Top-3 probability* |
|---:|---|---:|---|---:|
| 1 | Mexico | 69.9 | Priority Market | 99.7% |
| 2 | Brazil | 67.6 | Priority Market | 91.1% |
| 3 | Chile | 60.7 | Priority Market | 76.9% |
| 4 | Costa Rica | 59.6 | Growth Bet | 32.3% |
| 5 | Uruguay | 48.1 | Growth Bet | 0.0% |

\*Share of 2,000 weight-sensitivity simulations in which the market appears in the top three.

![Attractiveness and accessibility matrix](reports/figures/attractiveness_accessibility_matrix.png)

## Markets and indicators

The analysis covers Argentina, Brazil, Chile, Colombia, Costa Rica, Ecuador, Mexico, Panama, Peru, and Uruguay. It uses eight public World Development Indicators:

- GDP, GDP growth, GDP per capita, and population
- Internet use and trade openness
- FDI net inflows
- Inflation (scored inversely as a risk proxy)

The [data dictionary](docs/data_dictionary.md) documents definitions, codes, units, and weights.

## Method

1. Download 2015–2025 observations directly from the World Bank API.
2. Select the latest year with complete coverage across all markets and indicators.
3. Winsorize each variable at the 5th and 95th percentiles.
4. Normalize indicators to a 0–100 scale.
5. Calculate Market Attractiveness (55%) and Commercial Accessibility (45%).
6. Create a weighted opportunity score and portfolio segments.
7. Run 2,000 alternative weight combinations to assess ranking stability.

The weights are explicit in [`src/build_analysis.py`](src/build_analysis.py). They express a general-purpose commercial expansion strategy and should be changed for a specific sector or company.

## Reproduce the analysis

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/build_analysis.py
python -m unittest discover tests
```

The pipeline caches source extracts in `data/raw`, writes analytical tables to `data/processed`, and regenerates the figures in `reports/figures`.

## Repository structure

```text
├── data/
│   ├── raw/                    # API extracts by indicator
│   └── processed/              # History, ranking, sensitivity and metadata
├── docs/data_dictionary.md
├── notebooks/executive_analysis.ipynb
├── reports/
│   ├── executive_summary.md
│   └── figures/
├── src/build_analysis.py
├── requirements.txt
└── README.md
```

## Limitations

This is a screening model, not an investment recommendation. It does not model sector demand, competition, regulation, taxes, security, route-to-market costs, or product-market fit. World Bank values may be revised. A real expansion decision should add sector-specific evidence and local commercial validation.

## Data source

[World Bank — World Development Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation). Source data was retrieved on 21 September 2026; the API reported an update date of 13 July 2026 for the tested series.

## Author

André Luiz Monte — Commercial Leadership · Business Development · Data Analytics
