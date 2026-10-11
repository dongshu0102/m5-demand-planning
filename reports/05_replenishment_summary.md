# Phase 5 - Replenishment plan and service trade-off

Policy: periodic review every 1 wk, order-up-to, lead time 2 wk, holding cost 25%/yr. Safety stock sized from each series' own backtest RMSE of the recommended forecast method.

Simulated over the last 8 weeks of real demand (5,748 series), lost-sales.

## Plan by segment (service targets A 98% / B 95% / C 90%)

| segment   |    n |   service_target |   forecast_8wk |   actual_8wk |   safety_stock_units |   safety_stock_value |   fill_rate |   ss_weeks_of_demand |   revenue_share |   ss_value_share |
|:----------|-----:|-----------------:|---------------:|-------------:|---------------------:|---------------------:|------------:|---------------------:|----------------:|-----------------:|
| AX        |  453 |             0.98 |       134562   |       136605 |             17747    |             44915.9  |        1    |                 1.04 |           0.222 |            0.129 |
| AY        | 1443 |             0.98 |       274598   |       284358 |             59143.1  |            160900    |        1    |                 1.66 |           0.504 |            0.461 |
| AZ        |  224 |             0.98 |        30383.6 |        35226 |              9747.96 |             41687.8  |        0.99 |                 2.21 |           0.074 |            0.12  |
| BX        |  118 |             0.95 |        12768.6 |        13176 |              1701.46 |              4100.03 |        1    |                 1.03 |           0.01  |            0.012 |
| BY        | 1342 |             0.95 |        89069.7 |        95059 |             18569.8  |             46475.5  |        0.99 |                 1.56 |           0.113 |            0.133 |
| BZ        |  343 |             0.95 |        18793.4 |        21575 |              5169.79 |             15756.6  |        0.98 |                 1.92 |           0.027 |            0.045 |
| CX        |  102 |             0.9  |         9159.8 |         9424 |              1095.54 |              2270.21 |        1    |                 0.93 |           0.003 |            0.007 |
| CY        |  993 |             0.9  |        42723.6 |        45468 |              7959.05 |             18542.6  |        0.99 |                 1.4  |           0.028 |            0.053 |
| CZ        |  730 |             0.9  |        19710.5 |        24539 |              5042.3  |             14066.5  |        0.94 |                 1.64 |           0.019 |            0.04  |

## Service level vs inventory (uniform service level swept, then the ABC mix)

| service_level      |   fill_rate |   avg_on_hand_units |   avg_on_hand_value |   holding_cost_8wk |   share_series_stockout |   safety_stock_value |
|:-------------------|------------:|--------------------:|--------------------:|-------------------:|------------------------:|---------------------:|
| 0.8                |      0.9766 |              144989 |              381115 |              14658 |                   0.238 |               158272 |
| 0.85               |      0.9821 |              157557 |              415376 |              15976 |                   0.195 |               194908 |
| 0.9                |      0.9874 |              173608 |              459189 |              17661 |                   0.151 |               241004 |
| 0.95               |      0.9927 |              197779 |              525249 |              20202 |                   0.096 |               309326 |
| 0.98               |      0.9961 |              225349 |              600717 |              23104 |                   0.054 |               386221 |
| 0.99               |      0.9975 |              243860 |              651430 |              25055 |                   0.038 |               437485 |
| ABC mix (98/95/90) |      0.9931 |              210969 |              564373 |              21707 |                   0.11  |               348715 |

## How to read this

- `ss_weeks_of_demand`: safety stock expressed in weeks of average demand. Z segments need far more cover per unit of demand than X segments - that is the cost of unpredictability, and the argument for improving forecasts where revenue is.
- `ss_value_share` vs `revenue_share`: if a low-revenue segment eats a large share of safety stock dollars, lower its service target.
- The trade-off table is the conversation with finance: each step up in service level costs a known amount of inventory. The ABC mix row shows that differentiating targets gets most of the fill rate for less stock than a uniform high target.
- Simulated fill rate will land below the service target: the target is per replenishment cycle, the simulation counts every lost unit, and 8 weeks is a small sample.