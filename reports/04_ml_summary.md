# Phase 4 - Global LightGBM with demand drivers

Same rolling backtest (4 folds x 8 weeks), 5,160 series. Tweedie objective, direct multi-horizon, 28 features.

## Overall (all methods)

| method   |   WAPE |   bias |
|:---------|-------:|-------:|
| lgbm     |  0.393 | -0.05  |
| ets      |  0.425 |  0.004 |
| tsb      |  0.431 | -0.006 |
| ma8      |  0.451 | -0.008 |
| croston  |  0.461 |  0.009 |
| naive    |  0.474 | -0     |
| snaive   |  0.619 | -0.085 |
| zero     |  1     | -1     |

## WAPE by segment

| segment   |   croston |   ets |   lgbm |   ma8 |   naive |   snaive |   tsb |   zero |
|:----------|----------:|------:|-------:|------:|--------:|---------:|------:|-------:|
| AX        |     0.245 | 0.252 |  0.233 | 0.251 |   0.295 |    0.373 | 0.244 |      1 |
| AY        |     0.467 | 0.432 |  0.39  | 0.473 |   0.474 |    0.623 | 0.445 |      1 |
| AZ        |     0.773 | 0.535 |  0.543 | 0.608 |   0.545 |    0.952 | 0.585 |      1 |
| BX        |     0.327 | 0.33  |  0.317 | 0.334 |   0.405 |    0.453 | 0.327 |      1 |
| BY        |     0.527 | 0.5   |  0.473 | 0.521 |   0.573 |    0.713 | 0.502 |      1 |
| BZ        |     0.751 | 0.645 |  0.582 | 0.678 |   0.693 |    0.914 | 0.661 |      1 |
| CX        |     0.356 | 0.37  |  0.355 | 0.363 |   0.445 |    0.487 | 0.356 |      1 |
| CY        |     0.586 | 0.575 |  0.546 | 0.576 |   0.684 |    0.789 | 0.564 |      1 |
| CZ        |     0.81  | 0.703 |  0.663 | 0.706 |   0.76  |    1.006 | 0.69  |      1 |

## WAPE by horizon (weeks ahead)

|   h |   croston |   ets |   lgbm |   ma8 |   naive |   snaive |   tsb |   zero |
|----:|----------:|------:|-------:|------:|--------:|---------:|------:|-------:|
|   1 |     0.426 | 0.336 |  0.337 | 0.385 |   0.376 |    0.63  | 0.368 |      1 |
|   2 |     0.441 | 0.364 |  0.357 | 0.406 |   0.412 |    0.625 | 0.391 |      1 |
|   3 |     0.472 | 0.409 |  0.389 | 0.445 |   0.461 |    0.618 | 0.428 |      1 |
|   4 |     0.467 | 0.426 |  0.398 | 0.452 |   0.476 |    0.612 | 0.431 |      1 |
|   5 |     0.465 | 0.441 |  0.405 | 0.46  |   0.488 |    0.623 | 0.438 |      1 |
|   6 |     0.464 | 0.455 |  0.411 | 0.471 |   0.506 |    0.604 | 0.449 |      1 |
|   7 |     0.471 | 0.475 |  0.419 | 0.485 |   0.528 |    0.613 | 0.463 |      1 |
|   8 |     0.486 | 0.495 |  0.433 | 0.504 |   0.548 |    0.624 | 0.482 |      1 |

## Final recommended method per segment

| segment   | recommended   |   WAPE |   ets_WAPE |   lgbm_WAPE |   lgbm_vs_ets |   improvement_vs_baseline |   n_series |   revenue_share |
|:----------|:--------------|-------:|-----------:|------------:|--------------:|--------------------------:|-----------:|----------------:|
| AX        | lgbm          |  0.233 |      0.252 |       0.233 |         0.075 |                     0.072 |        451 |           0.225 |
| AY        | lgbm          |  0.39  |      0.432 |       0.39  |         0.097 |                     0.175 |       1433 |           0.511 |
| AZ        | ets           |  0.535 |      0.535 |       0.543 |        -0.015 |                     0.018 |        224 |           0.075 |
| BX        | lgbm          |  0.317 |      0.33  |       0.317 |         0.039 |                     0.051 |        104 |           0.009 |
| BY        | lgbm          |  0.473 |      0.5   |       0.473 |         0.054 |                     0.092 |       1299 |           0.112 |
| BZ        | lgbm          |  0.582 |      0.645 |       0.582 |         0.098 |                     0.142 |        337 |           0.027 |
| CX        | lgbm          |  0.355 |      0.37  |       0.355 |         0.041 |                     0.022 |         30 |           0.001 |
| CY        | lgbm          |  0.546 |      0.575 |       0.546 |         0.05  |                     0.052 |        659 |           0.022 |
| CZ        | lgbm          |  0.663 |      0.703 |       0.663 |         0.057 |                     0.061 |        623 |           0.017 |

## Feature importance (gain, mean over folds)

|               |   share |
|:--------------|--------:|
| rmean8        |   0.326 |
| rmean26       |   0.227 |
| rmean13       |   0.144 |
| rmean4        |   0.12  |
| dept          |   0.083 |
| lag1          |   0.039 |
| rstd26        |   0.011 |
| price_ratio   |   0.009 |
| woy           |   0.006 |
| price_change  |   0.005 |
| lag52         |   0.005 |
| h             |   0.004 |
| store         |   0.003 |
| weeks_on_sale |   0.002 |
| rzero8        |   0.002 |

## How to read this

- `lgbm_vs_ets` > 0 means the driver-aware model beats pure history in that segment.
- If price / snap / event features rank low in importance, drivers add little at store-item level and the right answer is to forecast at a higher level and disaggregate.
- WAPE by horizon shows how fast accuracy decays; that sets how far ahead a replenishment plan can be trusted (Phase 5).