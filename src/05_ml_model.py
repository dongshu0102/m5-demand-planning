"""
Phase 4 - Global gradient-boosted model (LightGBM) with demand drivers.

Input : data/processed/sales_weekly.parquet
        data/processed/sku_profile.csv
        data/processed/backtest_baselines.csv
        data/processed/backtest_stat.csv
        data/raw/calendar.csv
Output: data/processed/backtest_ml.csv
        data/processed/method_per_segment_final.csv
        reports/04_ml_summary.md

Question this phase answers: does knowing *why* demand moves (price changes,
SNAP days, holidays) beat knowing only *how* it moved (history)?

Design:
  - One global model across all series (the model learns from 5,000 items at once,
    which is why ML can work where per-series ETS cannot).
  - Direct multi-horizon: horizon h is a feature. Lag features are computed as-of
    the forecast origin, so no target leakage.
  - Tweedie objective: right for zero-inflated unit counts.
  - Same 4 x 8-week folds as Phases 2-3. The model is retrained per fold on data
    strictly before the cutoff.
  - Training origins sampled every ORIGIN_STEP weeks over the last TRAIN_WEEKS,
    to keep the training set ~1M rows.

Runtime on ~5,000 series: 5-10 min.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb

WEEKLY = Path("data/processed/sales_weekly.parquet")
PROFILE = Path("data/processed/sku_profile.csv")
BASE = Path("data/processed/backtest_baselines.csv")
STAT = Path("data/processed/backtest_stat.csv")
CAL = Path("data/raw/calendar.csv")
OUT_CSV = Path("data/processed/backtest_ml.csv")
OUT_METHOD = Path("data/processed/method_per_segment_final.csv")
OUT_MD = Path("reports/04_ml_summary.md")

HORIZON = 8
N_FOLDS = 4
TRAIN_WEEKS = 104     # history window for training origins
ORIGIN_STEP = 4       # sample a training origin every N weeks
LAGS = [1, 2, 3, 4, 8, 13, 26, 52]
ROLLS = [4, 8, 13, 26]

PARAMS = dict(objective="tweedie", tweedie_variance_power=1.2, learning_rate=0.05,
              num_leaves=63, min_data_in_leaf=200, feature_fraction=0.8,
              bagging_fraction=0.8, bagging_freq=1, verbose=-1, seed=42)
N_ROUNDS = 400


def load_weekly() -> pd.DataFrame:
    wk = pd.read_parquet(WEEKLY)
    wk["week_start"] = pd.to_datetime(wk["week_start"])
    cal = pd.read_csv(CAL)
    ev = (cal.groupby("wm_yr_wk")
             .agg(n_events=("event_name_1", lambda s: s.notna().sum()))
             .reset_index())
    wk = wk.merge(ev, on="wm_yr_wk", how="left").fillna({"n_events": 0})
    wk["woy"] = wk["week_start"].dt.isocalendar().week.astype(int)
    parts = wk["id"].str.rsplit("_", n=2, expand=True)
    wk["item_key"] = parts[0]
    wk["dept"] = wk["item_key"].str.rsplit("_", n=1).str[0]
    wk["store"] = wk["id"].str.extract(r"_(CA_\d|TX_\d|WI_\d)_")[0]
    for c in ["dept", "store"]:
        wk[c] = wk[c].astype("category").cat.codes
    wk = wk.sort_values(["id", "wm_yr_wk"]).reset_index(drop=True)
    wk["t"] = wk.groupby("id").cumcount()          # position within series
    return wk


def add_origin_features(wk: pd.DataFrame) -> pd.DataFrame:
    """Features known at the origin week t (history up to and including t)."""
    g = wk.groupby("id")["units"]
    for L in LAGS:
        wk[f"lag{L}"] = g.shift(L - 1)              # lag1 = units at origin itself
    for R in ROLLS:
        wk[f"rmean{R}"] = g.transform(lambda s: s.rolling(R, min_periods=1).mean())
        wk[f"rstd{R}"] = g.transform(lambda s: s.rolling(R, min_periods=2).std())
    wk["rzero8"] = g.transform(lambda s: (s == 0).rolling(8, min_periods=1).mean())
    wk["price_at_origin"] = wk["sell_price"]
    wk["weeks_on_sale"] = wk["t"]
    return wk


def build_rows(wk: pd.DataFrame, origins: np.ndarray) -> pd.DataFrame:
    """One row per (series, origin, h) with origin features + target-week known features."""
    orig_cols = ["id", "t", "dept", "store", "weeks_on_sale", "price_at_origin", "rzero8"] \
                + [f"lag{L}" for L in LAGS] + [f"rmean{R}" for R in ROLLS] + [f"rstd{R}" for R in ROLLS]
    o = wk[wk["t"].isin(origins)][orig_cols].rename(columns={"t": "t0"})
    tgt_cols = ["id", "t", "units", "sell_price", "snap_days", "n_events", "woy", "wm_yr_wk"]
    rows = []
    for h in range(1, HORIZON + 1):
        tg = wk[tgt_cols].copy()
        tg["t0"] = tg["t"] - h
        r = o.merge(tg, on=["id", "t0"], how="inner")
        r["h"] = h
        rows.append(r)
    df = pd.concat(rows, ignore_index=True)
    df["price_ratio"] = df["sell_price"] / df["price_at_origin"]
    df["price_change"] = (df["price_ratio"] != 1).astype(int)
    return df


FEATURES = (["h", "dept", "store", "weeks_on_sale", "price_at_origin", "sell_price",
             "price_ratio", "price_change", "snap_days", "n_events", "woy", "rzero8"]
            + [f"lag{L}" for L in LAGS] + [f"rmean{R}" for R in ROLLS] + [f"rstd{R}" for R in ROLLS])


def run_folds(wk: pd.DataFrame) -> pd.DataFrame:
    n_by_id = wk.groupby("id")["t"].max()
    out = []
    importances = []
    for fold in range(N_FOLDS):
        # cutoff position relative to each series' end, same as Phases 2-3
        back = HORIZON * (N_FOLDS - fold)
        cut = (n_by_id + 1 - back).rename("cut").reset_index()
        w = wk.merge(cut, on="id")
        w = w[w["t"] >= w["cut"] - TRAIN_WEEKS - HORIZON]     # trim history for speed
        w["rel"] = w["t"] - w["cut"]                           # 0 = first forecast week
        # training origins: rel in [-TRAIN_WEEKS, -HORIZON-1], sampled; targets must be < cut
        train_orig = w[(w["rel"] <= -HORIZON - 1) & (w["rel"] >= -TRAIN_WEEKS)
                       & ((w["rel"] % ORIGIN_STEP) == 0)]["t"].unique()
        tr = build_rows(w, train_orig)
        tr = tr[tr["t"] < tr.merge(cut, on="id")["cut"]]
        te = build_rows(w, w[w["rel"] == -1]["t"].unique())
        te = te[te["t"] == te.merge(cut, on="id")["cut"] + te["h"] - 1]

        dtrain = lgb.Dataset(tr[FEATURES], label=tr["units"],
                             categorical_feature=["dept", "store"])
        model = lgb.train(PARAMS, dtrain, num_boost_round=N_ROUNDS)
        te = te.copy()
        te["forecast"] = model.predict(te[FEATURES]).clip(min=0)
        te["fold"] = fold
        te["method"] = "lgbm"
        out.append(te[["id", "fold", "h", "wm_yr_wk", "units", "forecast", "method"]]
                   .rename(columns={"units": "actual"}))
        importances.append(pd.Series(model.feature_importance("gain"), index=FEATURES))
        print(f"fold {fold}: train rows {len(tr):,}, test rows {len(te):,}")
    bt = pd.concat(out, ignore_index=True)
    bt.to_csv(OUT_CSV, index=False)
    imp = pd.concat(importances, axis=1).mean(axis=1).sort_values(ascending=False)
    return bt, imp


def wape(d):
    den = d["actual"].abs().sum()
    return np.nan if den == 0 else (d["forecast"] - d["actual"]).abs().sum() / den


def bias(d):
    den = d["actual"].abs().sum()
    return np.nan if den == 0 else (d["forecast"] - d["actual"]).sum() / den


def summarise(ml: pd.DataFrame, imp: pd.Series, prof: pd.DataFrame):
    cols = ["id", "fold", "h", "method", "actual", "forecast"]
    base = pd.read_csv(BASE)[cols]
    stat = pd.read_csv(STAT)[cols]
    ids = set(ml["id"]) & set(stat["id"])
    allbt = pd.concat([base, stat, ml[cols]], ignore_index=True)
    allbt = allbt[allbt["id"].isin(ids)]
    allbt = allbt.merge(prof[["id", "abc", "xyz", "segment", "demand_pattern", "total_revenue"]], on="id")

    overall = (allbt.groupby("method").apply(lambda d: pd.Series({"WAPE": wape(d), "bias": bias(d)}))
                    .sort_values("WAPE").round(3))
    by_seg = allbt.groupby(["segment", "method"]).apply(wape).unstack("method").round(3)
    by_h = allbt.groupby(["h", "method"]).apply(wape).unstack("method").round(3)

    rec = by_seg.idxmin(axis=1).rename("recommended").to_frame()
    rec["WAPE"] = by_seg.min(axis=1).round(3)
    rec["ets_WAPE"] = by_seg["ets"]
    rec["lgbm_WAPE"] = by_seg["lgbm"]
    rec["lgbm_vs_ets"] = ((by_seg["ets"] - by_seg["lgbm"]) / by_seg["ets"]).round(3)
    best_base = by_seg[["naive", "snaive", "ma8", "zero"]].min(axis=1)
    rec["improvement_vs_baseline"] = ((best_base - rec["WAPE"]) / best_base).round(3)
    p = prof[prof["id"].isin(ids)]
    rec["n_series"] = p.groupby("segment").size()
    rev = p.groupby("segment")["total_revenue"].sum()
    rec["revenue_share"] = (rev / rev.sum()).round(3)
    rec.to_csv(OUT_METHOD)

    lines = [
        "# Phase 4 - Global LightGBM with demand drivers", "",
        f"Same rolling backtest ({N_FOLDS} folds x {HORIZON} weeks), {len(ids):,} series. "
        f"Tweedie objective, direct multi-horizon, {len(FEATURES)} features.", "",
        "## Overall (all methods)", "", overall.to_markdown(), "",
        "## WAPE by segment", "", by_seg.to_markdown(), "",
        "## WAPE by horizon (weeks ahead)", "", by_h.to_markdown(), "",
        "## Final recommended method per segment", "", rec.to_markdown(), "",
        "## Feature importance (gain, mean over folds)", "",
        (imp / imp.sum()).round(3).head(15).rename("share").to_markdown(), "",
        "## How to read this", "",
        "- `lgbm_vs_ets` > 0 means the driver-aware model beats pure history in that segment.",
        "- If price / snap / event features rank low in importance, drivers add little at "
        "store-item level and the right answer is to forecast at a higher level and disaggregate.",
        "- WAPE by horizon shows how fast accuracy decays; that sets how far ahead a "
        "replenishment plan can be trusted (Phase 5).",
    ]
    OUT_MD.write_text("\n".join(lines))
    print(overall)
    print(rec[["recommended", "WAPE", "lgbm_vs_ets", "revenue_share"]])
    print(f"Summary -> {OUT_MD}")


def main():
    wk = load_weekly()
    wk = add_origin_features(wk)
    ml, imp = run_folds(wk)
    summarise(ml, imp, pd.read_csv(PROFILE))


if __name__ == "__main__":
    main()
