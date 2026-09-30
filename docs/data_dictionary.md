# Data dictionary and methodology

## Data and country coverage

Source: World Bank, World Development Indicators (WDI). Ten countries: Argentina, Brazil, Chile, Colombia, Costa Rica, Ecuador, Mexico, Panama, Peru and Uruguay.

The committed source observations span 2015–2025. This release uses 2025 as its current reference year and 2024 as a comparable baseline. The manifest records the actual source acquisition date separately from the date the analysis was rebuilt.

| Field | WDI code | Unit | Core-five weight | Historical eight-indicator weight |
|---|---|---|---:|---:|
| gdp_usd | NY.GDP.MKTP.CD | Current USD | 30.7692% | 20% |
| gdp_growth_pct | NY.GDP.MKTP.KD.ZG | Real annual growth, % | 23.0769% | 15% |
| gdp_per_capita_usd | NY.GDP.PCAP.CD | Current USD/person | 15.3846% | 10% |
| population | SP.POP.TOTL | People | 15.3846% | 10% |
| fdi_net_inflows_pct_gdp | BX.KLT.DINV.WD.GD.ZS | % of GDP | 15.3846% | 10% |
| internet_users_pct | IT.NET.USER.ZS | % of population | Excluded | 15% |
| trade_pct_gdp | NE.TRD.GNFS.ZS | Exports + imports, % of GDP | Excluded | 15% |
| inflation_pct | FP.CPI.TOTL.ZG | Annual consumer-price change, % | Excluded | 5%, inverse |

GDP per capita in current USD is an average-income proxy, not PPP purchasing power or a measure of household income distribution. Population is not a measured addressable customer base. FDI can be negative and may be affected by transactions unrelated to a specific commercial sector. GDP and population partially overlap as scale measures.

## Selection rule

For this model version, retain the five indicators with complete observations for all ten countries in both 2024 and 2025. Selection is based on coverage, not on the resulting country ranks. The five retained original weights total 0.65. Divide each by 0.65 to obtain the new weights.

The snapshot has 80/80 observations for 2024 and 68/80 for 2025. The missing 2025 observations are:

- Internet use: all ten countries.
- Inflation: Argentina.
- Trade openness: Panama.

Exclude these three indicators from every country in both years. Do not carry 2024 observations into 2025, assign zeros to missing values, fill gaps with forecasts, or renormalize the model separately for individual countries. Other 2025 inflation and trade observations remain in the raw and historical tables for inspection.

The selected five indicators supply 50/50 observations in 2025 and 100/100 across both years. If a retained indicator becomes incomplete after a future source refresh, the build fails rather than silently changing its indicator set.

## Comparable normalization

For each retained indicator:

1. Pool the twenty observations across the ten countries and the two years.
2. Calculate the pooled 5th and 95th percentiles using pandas linear quantiles.
3. Clip each observation to these bounds.
4. Calculate 100 × (clipped value − lower bound) / (upper bound − lower bound). A constant series receives 50.
5. Use the same bounds and weights for both years.

The weighted sum is the screening_score. Higher values are more favorable under this chosen model, including for FDI and GDP growth. Normalization parameters are committed in [scaling_parameters_2024_2025.json](../data/processed/scaling_parameters_2024_2025.json).

Shared bounds make the numerical difference between the two years meaningful within this specification. The score remains relative to the selected sample, and changes in data vintage or sample can alter its calibration. It is not an out-of-sample forecasting model.

## Derived fields

| Field | Meaning |
|---|---|
| year | Observation/reference year, not acquisition year |
| score_* | Normalized component, 0–100 |
| screening_score | Five-indicator weighted sum |
| rank | Rank within that year; highest score first |
| screening_score_2024 / screening_score_2025 | Values under the same core-five specification and shared scale |
| score_change_points | 2025 score minus comparable 2024 score |
| rank_change | 2024 rank minus 2025 rank; positive means an improvement |
| top3_share | Share of 2,000 weight scenarios where the country places in the top three |
| score_p10 / score_p90 | Scenario percentiles conditional on the model, not statistical confidence bounds |

Sensitivity weights are drawn from a Dirichlet distribution centered on the core weights, with concentration 100 and seed 42. This tests local weight sensitivity only. It does not test missing-variable risk, every alternative weighting strategy, commercial success or sector suitability.

## Historical model

The historical 2024 specification uses all eight indicators, its original weights, and separate 2024-only percentile bounds. It retains market_attractiveness, commercial_accessibility, opportunity_score and the original rank-based segments. These fields do not apply to the current core-five score.

The original historical filenames are preserved. The old top3_probability column name is retained for compatibility, but its meaning is scenario share, not probability of business success. See [the historical report](../reports/historical_2024.md).

The different ranking under the core-five specification reflects **model changes as well as data changes**. Compare years only with the dedicated core-five comparison table.

## Provenance and reproduction

[Source manifest](../data/raw/source_manifest.json) links each extract to its API query and checksum. This release retains the source snapshot acquired on 21 September 2026; the full refresh attempted on 30 September did not complete. No newer acquisition date is claimed. A normal offline rebuild does not modify source files or acquisition dates.

Published WDI observations may themselves be estimates or revisions by the source agencies. The project generates no synthetic observations and performs no missing-value imputation.

Code entry point: [build_analysis.py](../src/build_analysis.py). Explicit source refresh: [download_data.py](../src/download_data.py), or the --refresh option. A successful refresh saves all eight series only after every response is fetched and validated, and archives the original JSON responses.
