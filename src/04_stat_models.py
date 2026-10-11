"""
Phase 3 - Statistical models per segment, backtested on the same folds as the baselines.

Input : data/processed/sales_weekly.parquet
        data/processed/sku_profile.csv
        data/processed/backtest_baselines.csv
Output: data/processed/backtest_stat.csv        forecast vs actual, same shape as baselines file
        data/processed/method_per_segment.csv   recommended method per ABC x XYZ segment
        reports/03_stat_models_summary.md

Models (statsforecast):
  AutoETS           exponential smoothing, automatic error/trend selection.
                    Non-seasonal, because Phase 2 showed seasonal naive never wins
                    at store-item level - recent level matters more than last year.
  CrostonOptimized  classic intermittent-demand method: separate smoothing of
                    demand size and demand interval.
  TSB               Teunter-Syntetos-Babai: like Croston but updates every period,
                    so it handles items that are going obsolete.

All models run on all series; the recommendation table then picks, per segment,
the best of {baselines + stat models}. A planner cares about the method that wins
in the segment, not the method that wins on average.

Runtime on 5,748 series x 4 folds: roughly 5-15 min depending on cores.
Set N_JOBS below; -1 = all cores.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import AutoETS, CrostonOptimized, TSB

WEEKLY = Path("data/processed/sales_weekly.parquet")
PROFILE = Path("data/processed/sku_profile.csv")
BASE = Path("data/processed/backtest_baselines.csv")
OUT_CSV = Path("data/processed/backtest_stat.csv")
OUT_METHOD = Path("data/processed/method_per_segment.csv")
OUT_MD = Path("reports/03_stat_models_summary.md")

HORIZON = 8
N_FOLDS = 4
N_JOBS = -1
MIN_TRAIN = 60       # weeks; series shorter than this skip the earliest folds anyway


def load_series() -> pd.DataFrame:
    wk = pd.read_parquet(WEEKLY, columns=["id", "week_start", "units"])
    df = wk.rename(columns={"id": "unique_id", "week_start": "ds", "units": "y"})
    df["ds"] = pd.to_datetime(df["ds"])
    df["y"] = df["y"].astype(float)
    # Need at least MIN_TRAIN + the backtest window to be comparable with baselines
    n = df.groupby("unique_id").size()
    keep = n[n >= MIN_TRAIN + HORIZON * N_FOLDS].index
    df = df[df["unique_id"].isin(keep)]
    print(f"Series for stat models: {df['unique_id'].nunique():,}")
    return df


def run_models(df: pd.DataFrame) -> pd.DataFrame:
    sf = StatsForecast(
        models=[
            AutoETS(season_length=1, alias="ets"),
            CrostonOptimized(alias="croston"),
            TSB(alpha_d=0.2, alpha_p=0.2, alias="tsb"),
        ],
        freq="W-SAT",            # M5 weeks start Saturday; adjust if your week_start differs
        n_jobs=N_JOBS,
    )
    cv = sf.cross_validation(df=df, h=HORIZON, step_size=HORIZON, n_windows=N_FOLDS)
    cv = cv.reset_index() if "unique_id" not in cv.columns else cv
    cv = cv.rename(columns={"unique_id": "id"})
    # Negative forecasts are meaningless for units
    for m in ["ets", "croston", "tsb"]:
        cv[m] = cv[m].clip(lower=0)
    # Reshape to the same long format as the baselines file
    cv["fold"] = cv.groupby("id")["cutoff"].rank(method="dense").astype(int) - 1
    cv["h"] = cv.groupby(["id", "cutoff"]).cumcount() + 1
    long = cv.melt(id_vars=["id", "fold", "h", "ds", "y"],
                   value_vars=["ets", "croston", "tsb"],
                   var_name="method", value_name="forecast")
    long = long.rename(columns={"y": "actual"})
    long.to_csv(OUT_CSV, index=False)
    print(f"Stat backtest rows: {len(long):,} -> {OUT_CSV}")
    return long


def wape(d: pd.DataFrame) -> float:
    den = d["actual"].abs().sum()
    return np.nan if den == 0 else (d["forecast"] - d["actual"]).abs().sum() / den


def bias(d: pd.DataFrame) -> float:
    den = d["actual"].abs().sum()
    return np.nan if den == 0 else (d["forecast"] - d["actual"]).sum() / den


def summarise(stat: pd.DataFrame, prof: pd.DataFrame):
    base = pd.read_csv(BASE)
    ids = stat["id"].unique()
    base = base[base["id"].isin(ids)]
    cols = ["id", "fold", "h", "method", "actual", "forecast"]
    allbt = pd.concat([base[cols], stat[cols]], ignore_index=True)
    allbt = allbt.merge(prof[["id", "abc", "xyz", "segment", "demand_pattern"]], on="id")

    overall = (allbt.groupby("method").apply(lambda d: pd.Series({"WAPE": wape(d), "bias": bias(d)}))
                    .sort_values("WAPE").round(3))
    by_seg = allbt.groupby(["segment", "method"]).apply(wape).unstack("method").round(3)
    by_pat = allbt.groupby(["demand_pattern", "method"]).apply(wape).unstack("method").round(3)

    rec = by_seg.idxmin(axis=1).rename("recommended").to_frame()
    rec["WAPE"] = by_seg.min(axis=1).round(3)
    best_base = by_seg[["naive", "snaive", "ma8", "zero"]].min(axis=1)
    rec["best_baseline_WAPE"] = best_base.round(3)
    rec["improvement_vs_baseline"] = ((best_base - rec["WAPE"]) / best_base).round(3)
    rec["n_series"] = prof[prof["id"].isin(ids)].groupby("segment").size()
    rec.to_csv(OUT_METHOD)

    # Dollar-weighted view: which segments matter
    rev = prof[prof["id"].isin(ids)].groupby("segment")["total_revenue"].sum()
    rec["revenue_share"] = (rev / rev.sum()).round(3)

    lines = [
        "# Phase 3 - Statistical models vs baselines", "",
        f"Same rolling backtest as Phase 2 ({N_FOLDS} folds x {HORIZON} weeks), {len(ids):,} series.", "",
        "## Overall (all methods)", "", overall.to_markdown(), "",
        "## WAPE by segment", "", by_seg.to_markdown(), "",
        "## WAPE by demand pattern", "", by_pat.to_markdown(), "",
        "## Recommended method per segment", "", rec.to_markdown(), "",
        "## How to read this", "",
        "- `improvement_vs_baseline` is the relative WAPE reduction over the best simple baseline. "
        "A segment where it is near zero is not worth modelling - plan it with reorder points.",
        "- `revenue_share` says where accuracy is worth money. Prioritise effort by "
        "revenue_share x improvement, not by WAPE alone.",
        "- ETS is non-seasonal on purpose: Phase 2 showed the 52-week seasonal naive never won.",
        "- Croston/TSB should win on intermittent and lumpy items; if ETS wins there too, "
        "the intermittency threshold (ADI 1.32) may be too loose for weekly data.",
    ]
    OUT_MD.write_text("\n".join(lines))
    print(overall)
    print(rec)
    print(f"Summary -> {OUT_MD}")


def main():
    df = load_series()
    prof = pd.read_csv(PROFILE)
    stat = run_models(df)
    summarise(stat, prof)


if __name__ == "__main__":
    main()
