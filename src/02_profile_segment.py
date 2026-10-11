"""
Phase 1b - Profile demand and segment SKUs (ABC / XYZ / intermittency).

Input : data/processed/sales_long.parquet
Output: data/processed/sku_profile.csv     one row per series with metrics and segment
        reports/01_profile_summary.md       plain-English summary for the README

Why this step matters to a planner:
  - ABC  : which items carry the revenue (A = top 80% of revenue)
  - XYZ  : how stable demand is (X = predictable, Z = erratic)
  - ADI/CV2: Syntetos-Boylan classification - tells you which items are
             intermittent/lumpy and need Croston-type methods instead of ETS.
"""

from pathlib import Path
import numpy as np
import pandas as pd

IN = Path("data/processed/sales_long.parquet")
OUT_CSV = Path("data/processed/sku_profile.csv")
OUT_MD = Path("reports/01_profile_summary.md")
OUT_MD.parent.mkdir(parents=True, exist_ok=True)


def profile(df: pd.DataFrame) -> pd.DataFrame:
    # Only count days after the item first appeared on sale (avoids fake zeros)
    df = df[df["on_sale"] == 1].copy()
    df["revenue"] = df["units"] * df["sell_price"]

    g = df.groupby(["id", "item_id", "dept_id", "store_id"])
    prof = g.agg(
        days=("units", "size"),
        total_units=("units", "sum"),
        total_revenue=("revenue", "sum"),
        mean_units=("units", "mean"),
        std_units=("units", "std"),
        zero_days=("units", lambda s: (s == 0).sum()),
        first_date=("date", "min"),
        last_date=("date", "max"),
    ).reset_index()

    prof["zero_share"] = prof["zero_days"] / prof["days"]
    prof["cv"] = prof["std_units"] / prof["mean_units"].replace(0, np.nan)

    # Syntetos-Boylan: ADI = average days between non-zero demands,
    #                  CV2 = squared CV of non-zero demand sizes
    nz = df[df["units"] > 0].groupby("id")["units"]
    prof = prof.merge(
        pd.DataFrame({
            "nz_count": nz.size(),
            "nz_cv2": (nz.std() / nz.mean()) ** 2,
        }).reset_index(), on="id", how="left")
    prof["adi"] = prof["days"] / prof["nz_count"].replace(0, np.nan)

    def sb_class(r):
        if pd.isna(r["adi"]):
            return "no_demand"
        if r["adi"] < 1.32 and r["nz_cv2"] < 0.49:
            return "smooth"
        if r["adi"] >= 1.32 and r["nz_cv2"] < 0.49:
            return "intermittent"
        if r["adi"] < 1.32 and r["nz_cv2"] >= 0.49:
            return "erratic"
        return "lumpy"
    prof["demand_pattern"] = prof.apply(sb_class, axis=1)

    # ABC on revenue (80 / 15 / 5)
    prof = prof.sort_values("total_revenue", ascending=False)
    cum = prof["total_revenue"].cumsum() / prof["total_revenue"].sum()
    prof["abc"] = np.where(cum <= 0.80, "A", np.where(cum <= 0.95, "B", "C"))

    # XYZ on weekly coefficient of variation (weekly smooths out daily noise)
    wk = (df.groupby(["id", "wm_yr_wk"])["units"].sum()
            .groupby("id").agg(["mean", "std"]))
    wk["cv_weekly"] = wk["std"] / wk["mean"].replace(0, np.nan)
    prof = prof.merge(wk[["cv_weekly"]].reset_index(), on="id", how="left")
    prof["xyz"] = pd.cut(prof["cv_weekly"], bins=[-np.inf, 0.5, 1.0, np.inf],
                         labels=["X", "Y", "Z"]).astype(str)
    prof["segment"] = prof["abc"] + prof["xyz"]
    return prof


def write_summary(prof: pd.DataFrame):
    n = len(prof)
    lines = [
        "# Phase 1 - Demand profile summary", "",
        f"- Series analysed: **{n:,}**",
        f"- Date range: {prof['first_date'].min().date()} to {prof['last_date'].max().date()}",
        f"- Median share of zero-demand days: **{prof['zero_share'].median():.0%}**", "",
        "## ABC (revenue concentration)", "",
        prof["abc"].value_counts().sort_index().rename("series").to_markdown(), "",
        "## XYZ (weekly demand variability)", "",
        prof["xyz"].value_counts().sort_index().rename("series").to_markdown(), "",
        "## ABC x XYZ matrix", "",
        pd.crosstab(prof["abc"], prof["xyz"]).to_markdown(), "",
        "## Demand pattern (Syntetos-Boylan)", "",
        prof["demand_pattern"].value_counts().rename("series").to_markdown(), "",
        "## What this means for forecasting", "",
        "- **AX / BX**: high value, stable -> statistical methods (ETS) with tight safety stock.",
        "- **AZ / BZ**: high value, erratic -> need promo/price drivers or ML; hold more buffer.",
        "- **CZ**: low value, erratic -> do not over-engineer; simple reorder-point rules.",
        "- **Intermittent / lumpy**: use Croston / TSB, not ETS or ARIMA.",
    ]
    OUT_MD.write_text("\n".join(lines))


def main():
    df = pd.read_parquet(IN)
    prof = profile(df)
    prof.to_csv(OUT_CSV, index=False)
    write_summary(prof)
    print(f"Profiled {len(prof):,} series -> {OUT_CSV}")
    print(pd.crosstab(prof["abc"], prof["xyz"]))
    print(prof["demand_pattern"].value_counts())
    print(f"Summary -> {OUT_MD}")


if __name__ == "__main__":
    main()
