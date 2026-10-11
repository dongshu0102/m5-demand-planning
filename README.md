# Demand forecasting and replenishment planning on M5 (Walmart)

This project builds the full demand planning chain on Walmart's M5 dataset — not just a forecast, but what the forecast is worth. Using 5,748 California grocery item-store series, it segments the assortment by value and variability, backtests six forecasting methods on identical rolling folds, picks the best method per segment, sizes safety stock from each method's measured error, and replays eight weeks of real demand under an order-up-to policy to show the inventory cost of every service-level choice.

The main findings: value is concentrated (1,433 series carry half the revenue); a single global model beats per-series methods by learning across items, not from price or promotion signals; A-class service targets above 95% buy almost nothing; and a two-week slip in supplier lead time costs more than every forecasting gain combined. Full narrative in [`reports/EXECUTIVE_SUMMARY.md`](reports/EXECUTIVE_SUMMARY.md); everything reproduces from the three Kaggle files with seven numbered scripts.

**Data:** [M5 Forecasting - Accuracy](https://www.kaggle.com/competitions/m5-forecasting-accuracy) (Walmart daily unit sales, 2011–2016, with prices and calendar events). Subset: California × FOODS = 1,437 items × 4 stores = 5,748 series, aggregated to weeks.

## Key findings

- **Most of the assortment is noise.** Median series has 51% zero-demand days. 1,433 AY series (high value, moderate variability) carry 50% of revenue; effort was prioritised by revenue share × achievable improvement.
- **Simple baselines are a hard bar.** In a 4-fold × 8-week rolling backtest, seasonal naive never beat an 8-week moving average at store-item level. Per-series ETS / Croston / TSB improved on baselines by only 1–7%.
- **A global model clears it — through pooling, not drivers.** LightGBM (Tweedie, direct multi-horizon) trained across all series cut WAPE 18% on AY and 12% revenue-weighted. Price, SNAP and event features contributed under 2% of gain; rolling-mean features over 80%.
- **Forecast error priced in inventory.** Safety stock sized from each method's backtest RMSE totals $349k in the subset. Z-class items need about twice the weeks of safety cover of X-class items.
- **Service targets were set too high.** Fill rate is saturated: lowering the A-class target from 98% to 95% cost 0.16 points of fill and released $48k of inventory. A bias correction applied alone added $31k of stock for $1k less lost sales — it must be paired with re-sized safety stock.
- **Lead time matters more than accuracy.** A supplier moving from 2 to 4 weeks costs ~$190k in lost sales (plan unchanged) or ~$210k in added inventory (plan re-sized) per 8 weeks. No forecasting gain in this study comes close.

## Pipeline

| Phase | Script | What it does | Report |
|---|---|---|---|
| 1 | `01_load_subset.py`, `02_profile_segment.py` | Load, subset, profile; ABC / XYZ / Syntetos-Boylan segmentation | `01_profile_summary.md` |
| 2 | `03_backtest_baselines.py` | Weekly series; rolling-origin backtest; naive, seasonal naive, MA8, zero baselines; WAPE and bias | `02_baselines_summary.md` |
| 3 | `04_stat_models.py` | AutoETS, Croston, TSB on the same folds; method-per-segment recommendation | `03_stat_models_summary.md` |
| 4 | `05_ml_model.py` | Global LightGBM with lag, rolling, price, SNAP, event features; final method per segment; feature importance | `04_ml_summary.md` |
| 5 | `06_replenishment.py` | Safety stock from backtest RMSE; ABC service targets; order-up-to plan; 8-week simulation; service-vs-inventory trade-off | `05_replenishment_summary.md` |
| 6 | `07_scenarios.py` | Shipment delay, lead-time change, demand shocks, bias correction; executive summary | `06_scenarios_summary.md`, `EXECUTIVE_SUMMARY.md` |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# macOS only, for LightGBM: brew install libomp
```

1. Download `sales_train_evaluation.csv`, `calendar.csv`, `sell_prices.csv` from Kaggle into `data/raw/`.
2. Run the scripts in order:

```bash
python src/01_load_subset.py
python src/02_profile_segment.py
python src/03_backtest_baselines.py
python src/04_stat_models.py
python src/05_ml_model.py
python src/06_replenishment.py
python src/07_scenarios.py
```

Phases 1–2 take a few minutes; Phase 3 and 4 take 5–15 minutes each on a laptop. To change the subset, edit `STATE`, `CATEGORY`, `STORES` at the top of `01_load_subset.py`.

## Structure

```
data/raw/         Kaggle files (not committed)
data/processed/   intermediate outputs (not committed)
src/              numbered scripts, one per phase
reports/          plain-English findings, one per phase, plus the executive summary
```

## Assumptions

M5 has no supply-side data. Lead time (2 weeks), review period (1 week), holding cost (25%/yr) and service targets (A 98 / B 95 / C 90) are stated parameters at the top of `src/06_replenishment.py`, chosen to be conservative and easy to change. Simulation uses lost sales, not backorders. 581 series with under two years of history were excluded from per-series statistical models (the global model covered them); new-item forecasting is the natural next phase.

## Tools

Python · pandas · statsforecast (Nixtla) · LightGBM · scipy
