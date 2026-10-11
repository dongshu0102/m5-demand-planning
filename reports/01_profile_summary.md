# Phase 1 - Demand profile summary

- Series analysed: **5,748**
- Date range: 2011-01-29 to 2016-05-22
- Median share of zero-demand days: **51%**

## ABC (revenue concentration)

| abc   |   series |
|:------|---------:|
| A     |     2120 |
| B     |     1803 |
| C     |     1825 |

## XYZ (weekly demand variability)

| xyz   |   series |
|:------|---------:|
| X     |      673 |
| Y     |     3778 |
| Z     |     1297 |

## ABC x XYZ matrix

| abc   |   X |    Y |   Z |
|:------|----:|-----:|----:|
| A     | 453 | 1443 | 224 |
| B     | 118 | 1342 | 343 |
| C     | 102 |  993 | 730 |

## Demand pattern (Syntetos-Boylan)

| demand_pattern   |   series |
|:-----------------|---------:|
| intermittent     |     3348 |
| lumpy            |     1585 |
| smooth           |      539 |
| erratic          |      276 |

## What this means for forecasting

- **AX / BX**: high value, stable -> statistical methods (ETS) with tight safety stock.
- **AZ / BZ**: high value, erratic -> need promo/price drivers or ML; hold more buffer.
- **CZ**: low value, erratic -> do not over-engineer; simple reorder-point rules.
- **Intermittent / lumpy**: use Croston / TSB, not ETS or ARIMA.