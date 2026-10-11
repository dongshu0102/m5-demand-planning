"""
Phase 2 - Backtest harness and baseline forecasts.

Input : data/processed/sales_long.parquet
        data/processed/sku_profile.csv
Output: data/processed/sales_weekly.parquet     one row per series-week (used by all later phases)
        data/processed/backtest_baselines.csv   forecast vs actual per series, fold, week, method
        reports/02_baselines_summary.md         WAPE and bias by method and segment

Design choices a planner would recognise:
  - Weekly buckets. Daily M5 data is too noisy to plan replenishment on, and
    most retail S&OP cycles are weekly.
  - Rolling-origin backtest: N_FOLDS cut-off points, each forecasting HORIZON weeks
    ahead using only data before the cut-off. One holdout is luck; several is evidence.
  - Metrics: WAPE (weighted absolute % error - robust to zeros, weights big movers)
    and bias (are we systematically over/under?). MAPE is avoided because it explodes
    on zero actuals, which dominate this dataset.
  - Baselines are the bar every later model must clear:
      naive          last observed week
      snaive         same week one year ago (52 weeks)
      ma8            mean of last 8 weeks
      zero           forecast nothing (surprisingly hard to beat on lumpy items)
"""

from pathlib import Path
import numpy as np
import pandas as pd

LONG = Path("data/processed/sales_long.parquet")
PROFILE = Path("data/processed/sku_profile.csv")
WEEKLY = Path("data/processed/sales_weekly.parquet")
OUT_CSV = Path("data/processed/backtest_baselines.csv")
OUT_MD = Path("reports/02_baselines_summary.md")

HORIZON = 8          # weeks ahead to forecast in each fold
N_FOLDS = 4          # rolling cut-off points
SEASON = 52


def build_weekly() -> pd.DataFrame:
    df = pd.read_parquet(LONG, columns=["id", "wm_yr_wk", "date", "units",
                                        "sell_price", "on_sale", "snap"])
    wk = (df.groupby(["id", "wm_yr_wk"])
            .agg(week_start=("date", "min"),
                 units=("units", "sum"),
                 sell_price=("sell_price", "mean"),
                 on_sale=("on_sale", "max"),
                 snap_days=("snap", "sum"),
                 n_days=("date", "size"))
            .reset_index())
    # Drop partial weeks (M5 ends mid-week); a 2-day "week" would look like a demand collapse
    wk = wk[wk["n_days"] == 7].drop(columns="n_days")
    # Drop weeks before an item first went on sale in that store
    first = wk[wk["on_sale"] == 1].groupby("id")["wm_yr_wk"].min().rename("first_wk")
    wk = wk.merge(first, on="id").query("wm_yr_wk >= first_wk").drop(columns="first_wk")
    wk = wk.sort_values(["id", "wm_yr_wk"]).reset_index(drop=True)
    wk.to_parquet(WEEKLY, index=False)
    print(f"Weekly series: {wk['id'].nunique():,} ids, {len(wk):,} rows -> {WEEKLY}")
    return wk


def make_folds(weeks: np.ndarray):
    """Return list of (train_end_index) positions so that each fold has HORIZON weeks after it."""
    n = len(weeks)
    cutoffs = [n - HORIZON * (k + 1) for k in range(N_FOLDS)][::-1]
    return [c for c in cutoffs if c > SEASON + 8]


def baselines_for_series(y: np.ndarray, cut: int) -> dict:
    train = y[:cut]
    out = {
        "naive": np.repeat(train[-1], HORIZON),
        "ma8": np.repeat(train[-8:].mean(), HORIZON),
        "zero": np.zeros(HORIZON),
    }
    if cut >= SEASON:
        out["snaive"] = train[cut - SEASON: cut - SEASON + HORIZON]
        if len(out["snaive"]) < HORIZON:   # pad if the seasonal window runs past train end
            out["snaive"] = np.pad(out["snaive"], (0, HORIZON - len(out["snaive"])), mode="edge")
    return out


def run_backtest(wk: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sid, g in wk.groupby("id", sort=False):
        y = g["units"].to_numpy(dtype=float)
        weeks = g["wm_yr_wk"].to_numpy()
        for fold, cut in enumerate(make_folds(weeks)):
            actual = y[cut: cut + HORIZON]
            if len(actual) < HORIZON:
                continue
            for method, fc in baselines_for_series(y, cut).items():
                rows.append(pd.DataFrame({
                    "id": sid, "fold": fold, "method": method,
                    "wm_yr_wk": weeks[cut: cut + HORIZON],
                    "h": np.arange(1, HORIZON + 1),
                    "actual": actual, "forecast": fc,
                }))
    bt = pd.concat(rows, ignore_index=True)
    bt.to_csv(OUT_CSV, index=False)
    print(f"Backtest rows: {len(bt):,} -> {OUT_CSV}")
    return bt


def wape(df: pd.DataFrame) -> float:
    denom = df["actual"].abs().sum()
    return np.nan if denom == 0 else (df["forecast"] - df["actual"]).abs().sum() / denom


def bias(df: pd.DataFrame) -> float:
    denom = df["actual"].abs().sum()
    return np.nan if denom == 0 else (df["forecast"] - df["actual"]).sum() / denom


def summarise(bt: pd.DataFrame, prof: pd.DataFrame):
    bt = bt.merge(prof[["id", "abc", "xyz", "segment", "demand_pattern"]], on="id")

    overall = (bt.groupby("method").apply(lambda d: pd.Series({"WAPE": wape(d), "bias": bias(d)}))
                 .sort_values("WAPE"))
    by_abc = (bt.groupby(["abc", "method"]).apply(wape).unstack("method").round(3))
    by_xyz = (bt.groupby(["xyz", "method"]).apply(wape).unstack("method").round(3))
    by_pat = (bt.groupby(["demand_pattern", "method"]).apply(wape).unstack("method").round(3))

    # Which baseline wins in each ABC x XYZ cell?
    cell = bt.groupby(["segment", "method"]).apply(wape).unstack("method")
    winner = cell.idxmin(axis=1).rename("best_baseline").to_frame()
    winner["WAPE"] = cell.min(axis=1).round(3)

    lines = [
        "# Phase 2 - Baseline backtest", "",
        f"Rolling-origin backtest: {N_FOLDS} folds x {HORIZON}-week horizon, weekly buckets, "
        f"{bt['id'].nunique():,} series.", "",
        "## Overall", "", overall.round(3).to_markdown(), "",
        "## WAPE by ABC class", "", by_abc.to_markdown(), "",
        "## WAPE by XYZ class", "", by_xyz.to_markdown(), "",
        "## WAPE by demand pattern", "", by_pat.to_markdown(), "",
        "## Best baseline per ABC x XYZ segment", "", winner.to_markdown(), "",
        "## How to read this", "",
        "- WAPE = sum|forecast - actual| / sum|actual|. 0.40 means errors total 40% of demand.",
        "- Bias > 0 = over-forecasting (excess stock); < 0 = under-forecasting (stockouts).",
        "- Any model in later phases must beat the best baseline *in its segment*, not just overall.",
        "- Where `zero` or `ma8` wins, the item is too lumpy for pattern-based methods; "
        "plan it with reorder points, not forecasts.",
    ]
    OUT_MD.write_text("\n".join(lines))
    print(overall.round(3))
    print(f"Summary -> {OUT_MD}")


def main():
    wk = build_weekly()
    prof = pd.read_csv(PROFILE)
    bt = run_backtest(wk)
    summarise(bt, prof)


if __name__ == "__main__":
    main()
