# Phase 3 - Statistical models vs baselines

Same rolling backtest as Phase 2 (4 folds x 8 weeks), 5,160 series.

## Overall (all methods)

| method   |   WAPE |   bias |
|:---------|-------:|-------:|
| ets      |  0.425 |  0.004 |
| tsb      |  0.431 | -0.006 |
| ma8      |  0.451 | -0.008 |
| croston  |  0.461 |  0.009 |
| naive    |  0.474 | -0     |
| snaive   |  0.619 | -0.085 |
| zero     |  1     | -1     |

## WAPE by segment

| segment   |   croston |   ets |   ma8 |   naive |   snaive |   tsb |   zero |
|:----------|----------:|------:|------:|--------:|---------:|------:|-------:|
| AX        |     0.245 | 0.252 | 0.251 |   0.295 |    0.373 | 0.244 |      1 |
| AY        |     0.467 | 0.432 | 0.473 |   0.474 |    0.623 | 0.445 |      1 |
| AZ        |     0.773 | 0.535 | 0.608 |   0.545 |    0.952 | 0.585 |      1 |
| BX        |     0.327 | 0.33  | 0.334 |   0.405 |    0.453 | 0.327 |      1 |
| BY        |     0.527 | 0.5   | 0.521 |   0.573 |    0.713 | 0.502 |      1 |
| BZ        |     0.751 | 0.645 | 0.678 |   0.693 |    0.914 | 0.661 |      1 |
| CX        |     0.356 | 0.37  | 0.363 |   0.445 |    0.487 | 0.356 |      1 |
| CY        |     0.586 | 0.575 | 0.576 |   0.684 |    0.789 | 0.564 |      1 |
| CZ        |     0.81  | 0.703 | 0.706 |   0.76  |    1.006 | 0.69  |      1 |

## WAPE by demand pattern

| demand_pattern   |   croston |   ets |   ma8 |   naive |   snaive |   tsb |   zero |
|:-----------------|----------:|------:|------:|--------:|---------:|------:|-------:|
| erratic          |     0.458 | 0.461 | 0.486 |   0.493 |    0.631 | 0.46  |      1 |
| intermittent     |     0.554 | 0.477 | 0.506 |   0.544 |    0.713 | 0.487 |      1 |
| lumpy            |     0.58  | 0.53  | 0.56  |   0.587 |    0.779 | 0.54  |      1 |
| smooth           |     0.298 | 0.29  | 0.311 |   0.326 |    0.418 | 0.293 |      1 |

## Recommended method per segment

| segment   | recommended   |   WAPE |   best_baseline_WAPE |   improvement_vs_baseline |   n_series |   revenue_share |
|:----------|:--------------|-------:|---------------------:|--------------------------:|-----------:|----------------:|
| AX        | tsb           |  0.244 |                0.251 |                     0.028 |        451 |           0.225 |
| AY        | ets           |  0.432 |                0.473 |                     0.087 |       1433 |           0.511 |
| AZ        | ets           |  0.535 |                0.545 |                     0.018 |        224 |           0.075 |
| BX        | croston       |  0.327 |                0.334 |                     0.021 |        104 |           0.009 |
| BY        | ets           |  0.5   |                0.521 |                     0.04  |       1299 |           0.112 |
| BZ        | ets           |  0.645 |                0.678 |                     0.049 |        337 |           0.027 |
| CX        | croston       |  0.356 |                0.363 |                     0.019 |         30 |           0.001 |
| CY        | tsb           |  0.564 |                0.576 |                     0.021 |        659 |           0.022 |
| CZ        | tsb           |  0.69  |                0.706 |                     0.023 |        623 |           0.017 |

## How to read this

- `improvement_vs_baseline` is the relative WAPE reduction over the best simple baseline. A segment where it is near zero is not worth modelling - plan it with reorder points.
- `revenue_share` says where accuracy is worth money. Prioritise effort by revenue_share x improvement, not by WAPE alone.
- ETS is non-seasonal on purpose: Phase 2 showed the 52-week seasonal naive never won.
- Croston/TSB should win on intermittent and lumpy items; if ETS wins there too, the intermittency threshold (ADI 1.32) may be too loose for weekly data.