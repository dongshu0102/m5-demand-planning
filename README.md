# Demand forecasting and replenishment planning on M5 (Walmart)

An end-to-end demand planning project built the way a supply planner would run it:
segment the assortment, forecast each segment with the right method, convert forecasts
into safety stock and replenishment decisions, and stress-test the plan against
supply disruptions.

**Data:** [M5 Forecasting - Accuracy](https://www.kaggle.com/competitions/m5-forecasting-accuracy)
(Walmart daily unit sales, 2011-2016, with prices and calendar events).
This project uses a subset — California, FOODS category (~1,400 item-store series) —
to keep it reproducible on a laptop.

## Project phases

| Phase | What | Status |
|---|---|---|
| 1 | Load, subset, profile demand; ABC / XYZ / intermittency segmentation | done |
| 2 | Baselines (naive, seasonal naive) and backtest harness (WAPE, bias) | next |
| 3 | Statistical models per segment (ETS, Croston / TSB for intermittent) | |
| 4 | ML model (LightGBM) with price, SNAP, and event features; compare vs statistical | |
| 5 | Safety stock, reorder points, 12-week replenishment plan; cost vs fill-rate trade-off | |
| 6 | Scenarios: supplier delay, demand shock; executive summary | |

## Setup

```bash
pip install -r requirements.txt
```

1. Download from Kaggle into `data/raw/`:
   `sales_train_evaluation.csv`, `calendar.csv`, `sell_prices.csv`
2. Run phase 1:

```bash
python src/01_load_subset.py      # -> data/processed/sales_long.parquet
python src/02_profile_segment.py  # -> data/processed/sku_profile.csv, reports/01_profile_summary.md
```

To change the subset, edit `STATE`, `CATEGORY`, `STORES` at the top of `01_load_subset.py`.

## Structure

```
data/raw/         Kaggle files (not committed - see .gitignore)
data/processed/   intermediate outputs
src/              numbered scripts, one per step
notebooks/        exploration and figures
reports/          plain-English findings, one per phase
```

## Key findings

_Filled in as each phase completes. Phase 1 summary: see `reports/01_profile_summary.md`._
