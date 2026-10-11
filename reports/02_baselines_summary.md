# Phase 2 - Baseline backtest

Rolling-origin backtest: 4 folds x 8-week horizon, weekly buckets, 5,398 series.

## Overall

| method   |   WAPE |   bias |
|:---------|-------:|-------:|
| ma8      |  0.451 | -0.008 |
| naive    |  0.475 | -0.001 |
| snaive   |  0.621 | -0.086 |
| zero     |  1     | -1     |

## WAPE by ABC class

| abc   |   ma8 |   naive |   snaive |   zero |
|:------|------:|--------:|---------:|-------:|
| A     | 0.412 |   0.422 |    0.566 |      1 |
| B     | 0.529 |   0.576 |    0.722 |      1 |
| C     | 0.606 |   0.69  |    0.85  |      1 |

## WAPE by XYZ class

| xyz   |   ma8 |   naive |   snaive |   zero |
|:------|------:|--------:|---------:|-------:|
| X     | 0.26  |   0.306 |    0.381 |      1 |
| Y     | 0.492 |   0.512 |    0.656 |      1 |
| Z     | 0.655 |   0.646 |    0.959 |      1 |

## WAPE by demand pattern

| demand_pattern   |   ma8 |   naive |   snaive |   zero |
|:-----------------|------:|--------:|---------:|-------:|
| erratic          | 0.487 |   0.493 |    0.631 |      1 |
| intermittent     | 0.505 |   0.544 |    0.715 |      1 |
| lumpy            | 0.56  |   0.587 |    0.78  |      1 |
| smooth           | 0.312 |   0.326 |    0.418 |      1 |

## Best baseline per ABC x XYZ segment

| segment   | best_baseline   |   WAPE |
|:----------|:----------------|-------:|
| AX        | ma8             |  0.252 |
| AY        | ma8             |  0.473 |
| AZ        | naive           |  0.545 |
| BX        | ma8             |  0.331 |
| BY        | ma8             |  0.521 |
| BZ        | ma8             |  0.677 |
| CX        | ma8             |  0.36  |
| CY        | ma8             |  0.573 |
| CZ        | ma8             |  0.705 |

## How to read this

- WAPE = sum|forecast - actual| / sum|actual|. 0.40 means errors total 40% of demand.
- Bias > 0 = over-forecasting (excess stock); < 0 = under-forecasting (stockouts).
- Any model in later phases must beat the best baseline *in its segment*, not just overall.
- Where `zero` or `ma8` wins, the item is too lumpy for pattern-based methods; plan it with reorder points, not forecasts.