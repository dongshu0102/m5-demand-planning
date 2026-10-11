"""
Phase 1a - Load the M5 dataset and build a tractable subset.

Input  (from Kaggle m5-forecasting-accuracy, placed in data/raw/):
    sales_train_evaluation.csv   (or sales_train_validation.csv)
    calendar.csv
    sell_prices.csv

Output (data/processed/):
    sales_long.parquet   one row per item-store-day, with price and calendar fields

Subset choice: one state (CA), one category (FOODS). This gives ~1,400 series,
which is enough to show intermittent demand and hierarchy without needing a big machine.
Change STATE / CATEGORY / STORES below to widen or narrow.
"""

from pathlib import Path
import pandas as pd

RAW = Path("data/raw")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

STATE = "CA"
CATEGORY = "FOODS"
STORES = None            # e.g. ["CA_1", "CA_2"] to narrow further; None = all stores in STATE


def load_sales() -> pd.DataFrame:
    f = RAW / "sales_train_evaluation.csv"
    if not f.exists():
        f = RAW / "sales_train_validation.csv"
    if not f.exists():
        raise FileNotFoundError(
            "Download the M5 files from Kaggle (m5-forecasting-accuracy) into data/raw/")
    df = pd.read_csv(f)
    df = df[(df["state_id"] == STATE) & (df["cat_id"] == CATEGORY)]
    if STORES:
        df = df[df["store_id"].isin(STORES)]
    print(f"Subset: {len(df):,} series ({STATE}, {CATEGORY})")
    return df


def to_long(sales: pd.DataFrame) -> pd.DataFrame:
    id_cols = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]
    day_cols = [c for c in sales.columns if c.startswith("d_")]
    long = sales.melt(id_vars=id_cols, value_vars=day_cols,
                      var_name="d", value_name="units")
    long["units"] = long["units"].astype("int16")
    return long


def add_calendar(long: pd.DataFrame) -> pd.DataFrame:
    cal = pd.read_csv(RAW / "calendar.csv", parse_dates=["date"])
    keep = ["d", "date", "wm_yr_wk", "weekday", "month", "year",
            "event_name_1", "event_type_1", "snap_CA", "snap_TX", "snap_WI"]
    cal = cal[keep]
    long = long.merge(cal, on="d", how="left")
    long["snap"] = long[f"snap_{STATE}"].astype("int8")
    return long.drop(columns=["snap_CA", "snap_TX", "snap_WI"])


def add_prices(long: pd.DataFrame) -> pd.DataFrame:
    prices = pd.read_csv(RAW / "sell_prices.csv")
    long = long.merge(prices, on=["store_id", "item_id", "wm_yr_wk"], how="left")
    # A missing price means the item was not yet on sale in that store-week.
    long["on_sale"] = long["sell_price"].notna().astype("int8")
    return long


def main():
    sales = load_sales()
    long = to_long(sales)
    long = add_calendar(long)
    long = add_prices(long)
    long = long.sort_values(["id", "date"]).reset_index(drop=True)
    long.to_parquet(OUT / "sales_long.parquet", index=False)
    print(f"Wrote {len(long):,} rows -> {OUT / 'sales_long.parquet'}")
    print(long.head())


if __name__ == "__main__":
    main()
