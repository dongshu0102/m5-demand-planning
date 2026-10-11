# Demand planning on M5: executive summary

**Scope.** 5,748 item-store series (Walmart, California, FOODS), 2011-2016 daily sales
aggregated to weeks. Objective: build a forecasting and replenishment approach a planning team
could run, and quantify what forecast accuracy is worth in inventory.

## 1. The assortment is mostly noise, and value is concentrated

- Median series has **51% zero-demand days**; **86%** of series are
  intermittent or lumpy by the Syntetos-Boylan test.
- Segment AY (high value, moderate variability) is **1,433 series carrying
  50% of revenue**. Every modelling and inventory decision was prioritised by
  revenue share x achievable improvement, not by series count.

## 2. Forecasting: simple methods set a hard bar; a global model clears it

- Rolling-origin backtest, 4 folds x 8 weeks. Seasonal naive never beat an 8-week moving average at
  store-item level: recent level matters more than last year's pattern.
- Per-series statistical models (ETS, Croston, TSB) improved on baselines by only 1-7%.
- A single global gradient-boosted model (LightGBM, Tweedie loss) trained across all series beat
  the best baseline by **18% on AY** and by **12%
  revenue-weighted** overall. Feature importance shows the gain comes from pooling (rolling-mean
  features), not from price, SNAP or event drivers, which contributed under 2% - those matter at
  aggregate levels, not here.
- One segment (AZ) remained best served by ETS; it is planned with wider buffers instead.

## 3. Inventory: forecast error priced in dollars

- Safety stock sized per series from the recommended model's own backtest RMSE, with ABC
  service targets (A 98 / B 95 / C 90). Total safety stock in the subset: **$348,715**.
- Z-class items hold roughly twice the weeks of safety cover of X-class items - the measurable
  cost of unpredictability, and the business case for forecast work on erratic, high-value items.
- Replaying the last 8 weeks of real demand: fill rate is saturated. A uniform 95% target delivered
  99.3% fill at $525,249 on hand; 98% delivered
  99.6% at $600,717. Lowering the A target to 95% changed
  fill by -0.16 points and on-hand value by $-48,529.
- The plan under-forecast every segment in the final period. A segment-level bias correction
  changed lost sales by $-1,048 and on-hand by
  $+30,740 - fixing the forecast is cheaper than stocking against it.

## 4. Resilience: what breaks the plan

| Scenario | Fill rate | Lost sales | On-hand value |
|---|---|---|---|
| Base plan | 99.3% | $12,351 | $564,374 |
| One-off 2-week shipment delay | 98.6% | $26,979 | $510,465 |
| Lead time 2 -> 4 wk, plan unchanged | 89.2% | $191,475 | $324,588 |
| Lead time 4 wk, plan re-sized | 98.5% | $27,217 | $776,293 |
| Demand +30% for 4 weeks | 98.6% | $29,367 | $501,652 |
| Combined: 4-wk lead time + demand +30% | 81.4% | $382,035 | $283,680 |

Safety stock absorbs one-off disruptions; it does not absorb a structural lead-time change unless
the plan is re-sized. The combined case is the one to size dual-sourcing or expedite budgets against.

## 5. Recommendations

1. Run the global model for A and B segments; use simple reorder rules for C - the error reduction
   there is not worth the maintenance.
2. Apply a bias correction from the rolling backtest before sizing stock.
3. Reset service targets from the trade-off curve rather than by class convention; the marginal
   fill above 95% is expensive.
4. Treat lead-time stability as a planning input: a supplier moving from 2 to 4 weeks costs more
   than any forecast improvement recovers.
5. Items introduced in the last two years were excluded from modelling (0
   series); new-item forecasting needs an analog-based method and is the natural next phase.

## Assumptions

Lead time 2 weeks, weekly review, order-up-to policy, lost sales, 25% annual holding cost.
M5 contains no supply-side data; all supply parameters are stated assumptions, chosen to be
conservative and easy to change in `src/06_replenishment.py`.
