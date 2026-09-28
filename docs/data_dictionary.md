# Data dictionary

All source variables come from the World Bank's World Development Indicators API.

| Field | World Bank code | Unit | Role in score | Weight |
|---|---|---:|---|---:|
| `gdp_usd` | `NY.GDP.MKTP.CD` | Current USD | Market scale | 20% |
| `gdp_growth_pct` | `NY.GDP.MKTP.KD.ZG` | Annual % | Growth momentum | 15% |
| `gdp_per_capita_usd` | `NY.GDP.PCAP.CD` | Current USD/person | Purchasing-power proxy | 10% |
| `population` | `SP.POP.TOTL` | People | Addressable-market proxy | 10% |
| `internet_users_pct` | `IT.NET.USER.ZS` | % of population | Digital reach | 15% |
| `trade_pct_gdp` | `NE.TRD.GNFS.ZS` | % of GDP | Commercial openness | 15% |
| `fdi_net_inflows_pct_gdp` | `BX.KLT.DINV.WD.GD.ZS` | % of GDP | Foreign-capital attraction | 10% |
| `inflation_pct` | `FP.CPI.TOTL.ZG` | Annual % | Macroeconomic risk (inverse) | 5% |

Derived fields:

- `score_*`: 0–100 score after 5th/95th percentile winsorization and min-max normalization.
- `market_attractiveness`: normalized weighted combination of GDP, growth, GDP per capita, and population.
- `commercial_accessibility`: normalized weighted combination of internet use, trade openness, FDI, and inverse inflation.
- `opportunity_score`: weighted sum of all eight normalized indicators.
- `rank`: descending rank by opportunity score.
- `segment`: portfolio grouping based on rank: Priority Market (1–3), Growth Bet (4–5), Selective Opportunity (6–8), or Monitor (9–10).

