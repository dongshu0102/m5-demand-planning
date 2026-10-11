"""
Phase 5 - From forecast to decision: safety stock, reorder points, replenishment plan,
          and the inventory-vs-service trade-off.

Input : data/processed/backtest_{baselines,stat,ml}.csv
        data/processed/method_per_segment_final.csv
        data/processed/sku_profile.csv
Output: data/processed/replenishment_plan.csv   per series: forecast, safety stock, ROP, order-up-to
        data/processed/service_tradeoff.csv     inventory $ vs fill rate across service levels
        reports/05_replenishment_summary.md

Planning assumptions (M5 has no supply data, so these are stated, not derived):
  LEAD_TIME_WEEKS   supplier lead time
  REVIEW_WEEKS      periodic review interval (order-up-to policy)
  HOLDING_RATE      annual inventory holding cost as a share of item value
  SERVICE_TARGET    cycle service level by ABC class - A gets the most protection

Method:
  1. Take each series' recommended forecast (from Phase 4) over the backtest.
  2. Measure its weekly forecast error empirically (RMSE over the backtest), per series.
  3. Safety stock = z(service) x RMSE x sqrt(L + R). Using the *model's own* error,
     not demand variance, is the key step: better forecasts earn lower safety stock.
  4. Order-up-to level S = forecast over (L + R) + safety stock.
  5. Simulate the last backtest fold (8 weeks of real demand) under the policy, for
     a range of service levels, to show what each point of fill rate costs in stock.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm

PROC = Path("data/processed")
OUT_PLAN = PROC / "replenishment_plan.csv"
OUT_TRADE = PROC / "service_tradeoff.csv"
OUT_MD = Path("reports/05_replenishment_summary.md")

LEAD_TIME_WEEKS = 2
REVIEW_WEEKS = 1
HOLDING_RATE = 0.25
SERVICE_TARGET = {"A": 0.98, "B": 0.95, "C": 0.90}
TRADEOFF_LEVELS = [0.80, 0.85, 0.90, 0.95, 0.98, 0.99]
HORIZON = 8
PLAN_FOLD = 3           # last fold = the 8 weeks we simulate


def load_backtests() -> pd.DataFrame:
    cols = ["id", "fold", "h", "method", "actual", "forecast"]
    parts = []
    for f in ["backtest_baselines.csv", "backtest_stat.csv", "backtest_ml.csv"]:
        p = PROC / f
        if p.exists():
            parts.append(pd.read_csv(p)[cols])
    return pd.concat(parts, ignore_index=True)


def pick_recommended(bt: pd.DataFrame, prof: pd.DataFrame) -> pd.DataFrame:
    rec = pd.read_csv(PROC / "method_per_segment_final.csv")[["segment", "recommended"]]
    m = prof[["id", "segment", "abc"]].merge(rec, on="segment")
    bt = bt.merge(m, on="id")
    bt = bt[bt["method"] == bt["recommended"]]
    return bt


def error_stats(bt: pd.DataFrame) -> pd.DataFrame:
    """Per-series weekly RMSE and bias of the recommended method over all folds."""
    bt = bt.copy()
    bt["err"] = bt["forecast"] - bt["actual"]
    g = bt.groupby("id")
    out = pd.DataFrame({
        "rmse": np.sqrt(g["err"].apply(lambda e: (e ** 2).mean())),
        "bias": g["err"].mean(),
        "mean_demand": g["actual"].mean(),
    }).reset_index()
    return out


def build_plan(bt: pd.DataFrame, prof: pd.DataFrame, err: pd.DataFrame,
               service: dict) -> pd.DataFrame:
    plan = bt[bt["fold"] == PLAN_FOLD]
    LR = LEAD_TIME_WEEKS + REVIEW_WEEKS
    fc_lr = (plan[plan["h"] <= LR].groupby("id")["forecast"].sum()
                 .rename("forecast_LplusR"))
    fc_8 = plan.groupby("id")["forecast"].sum().rename("forecast_8wk")
    act_8 = plan.groupby("id")["actual"].sum().rename("actual_8wk")
    p = (prof[["id", "item_id", "store_id", "segment", "abc", "xyz", "demand_pattern"]]
         .merge(err, on="id").merge(fc_lr, on="id").merge(fc_8, on="id").merge(act_8, on="id"))
    p["service_target"] = p["abc"].map(service)
    p["z"] = norm.ppf(p["service_target"])
    p["safety_stock"] = (p["z"] * p["rmse"] * np.sqrt(LR)).clip(lower=0)
    p["reorder_point"] = p["forecast_LplusR"] + p["safety_stock"]
    p["order_up_to"] = p["reorder_point"]        # periodic review: S = ROP for R folded in
    p["avg_price"] = prof.set_index("id").loc[p["id"], "total_revenue"].values / \
                     prof.set_index("id").loc[p["id"], "total_units"].replace(0, np.nan).values
    p["safety_stock_value"] = p["safety_stock"] * p["avg_price"]
    return p


def simulate(plan_rows: pd.DataFrame, policy: pd.DataFrame) -> dict:
    """
    Periodic-review order-up-to simulation over the 8 plan weeks, per series.
    Week t: receive orders placed L weeks ago -> meet demand -> place order up to S.
    Start with on-hand = S (steady state).  Lost sales, not backorders.
    """
    LR = LEAD_TIME_WEEKS + REVIEW_WEEKS
    wide = plan_rows.pivot(index="id", columns="h", values="actual").loc[policy["id"]]
    D = wide.to_numpy(dtype=float)                        # (n, 8)
    S = policy["order_up_to"].to_numpy(dtype=float)
    n = len(S)
    on_hand = S.copy()
    pipeline = np.zeros((n, LEAD_TIME_WEEKS))             # orders arriving in 1..L weeks
    met = np.zeros(n); demand = np.zeros(n); hold = np.zeros(n); stockout_wk = np.zeros(n)
    for t in range(HORIZON):
        on_hand += pipeline[:, 0]
        pipeline = np.roll(pipeline, -1, axis=1); pipeline[:, -1] = 0
        d = D[:, t]
        sold = np.minimum(on_hand, d)
        met += sold; demand += d
        stockout_wk += (d > on_hand)
        on_hand -= sold
        hold += on_hand
        if t % REVIEW_WEEKS == 0:
            position = on_hand + pipeline.sum(axis=1)
            q = np.maximum(S - position, 0)
            pipeline[:, -1] += q
    price = policy["avg_price"].to_numpy(dtype=float)
    avg_on_hand = hold / HORIZON
    return {
        "fill_rate": met.sum() / demand.sum() if demand.sum() > 0 else np.nan,
        "avg_on_hand_units": avg_on_hand.sum(),
        "avg_on_hand_value": np.nansum(avg_on_hand * price),
        "holding_cost_8wk": np.nansum(avg_on_hand * price) * HOLDING_RATE * HORIZON / 52,
        "series_with_stockout": int((stockout_wk > 0).sum()),
        "share_series_stockout": float((stockout_wk > 0).mean()),
        "per_series_fill": np.where(demand > 0, met / np.maximum(demand, 1e-9), np.nan),
    }


def main():
    prof = pd.read_csv(PROC / "sku_profile.csv")
    bt = pick_recommended(load_backtests(), prof)
    err = error_stats(bt)
    plan_rows = bt[bt["fold"] == PLAN_FOLD]

    # Main plan at the ABC-differentiated service targets
    plan = build_plan(bt, prof, err, SERVICE_TARGET)
    sim = simulate(plan_rows, plan)
    plan["sim_fill_rate"] = sim["per_series_fill"]
    plan.drop(columns=["z"]).round(3).to_csv(OUT_PLAN, index=False)

    # Trade-off curve: same service level for everything, swept
    rows = []
    for sl in TRADEOFF_LEVELS:
        pol = build_plan(bt, prof, err, {"A": sl, "B": sl, "C": sl})
        s = simulate(plan_rows, pol)
        rows.append({"service_level": sl,
                     "fill_rate": round(s["fill_rate"], 4),
                     "avg_on_hand_units": round(s["avg_on_hand_units"]),
                     "avg_on_hand_value": round(s["avg_on_hand_value"]),
                     "holding_cost_8wk": round(s["holding_cost_8wk"]),
                     "share_series_stockout": round(s["share_series_stockout"], 3),
                     "safety_stock_value": round(pol["safety_stock_value"].sum())})
    rows.append({"service_level": "ABC mix (98/95/90)",
                 "fill_rate": round(sim["fill_rate"], 4),
                 "avg_on_hand_units": round(sim["avg_on_hand_units"]),
                 "avg_on_hand_value": round(sim["avg_on_hand_value"]),
                 "holding_cost_8wk": round(sim["holding_cost_8wk"]),
                 "share_series_stockout": round(sim["share_series_stockout"], 3),
                 "safety_stock_value": round(plan["safety_stock_value"].sum())})
    trade = pd.DataFrame(rows)
    trade.to_csv(OUT_TRADE, index=False)

    # Segment view of the main plan
    seg = (plan.groupby("segment")
               .agg(n=("id", "size"),
                    service_target=("service_target", "first"),
                    forecast_8wk=("forecast_8wk", "sum"),
                    actual_8wk=("actual_8wk", "sum"),
                    safety_stock_units=("safety_stock", "sum"),
                    safety_stock_value=("safety_stock_value", "sum"),
                    fill_rate=("sim_fill_rate", "mean"))
               .round(2))
    seg["ss_weeks_of_demand"] = (seg["safety_stock_units"] / (seg["actual_8wk"] / HORIZON)).round(2)

    # Where safety stock dollars go vs where revenue is
    rev = prof.groupby("segment")["total_revenue"].sum()
    seg["revenue_share"] = (rev / rev.sum()).round(3)
    seg["ss_value_share"] = (seg["safety_stock_value"] / seg["safety_stock_value"].sum()).round(3)

    lines = [
        "# Phase 5 - Replenishment plan and service trade-off", "",
        f"Policy: periodic review every {REVIEW_WEEKS} wk, order-up-to, lead time {LEAD_TIME_WEEKS} wk, "
        f"holding cost {HOLDING_RATE:.0%}/yr. Safety stock sized from each series' own "
        f"backtest RMSE of the recommended forecast method.", "",
        f"Simulated over the last {HORIZON} weeks of real demand ({len(plan):,} series), lost-sales.", "",
        "## Plan by segment (service targets A 98% / B 95% / C 90%)", "",
        seg.to_markdown(), "",
        "## Service level vs inventory (uniform service level swept, then the ABC mix)", "",
        trade.to_markdown(index=False), "",
        "## How to read this", "",
        "- `ss_weeks_of_demand`: safety stock expressed in weeks of average demand. "
        "Z segments need far more cover per unit of demand than X segments - that is the "
        "cost of unpredictability, and the argument for improving forecasts where revenue is.",
        "- `ss_value_share` vs `revenue_share`: if a low-revenue segment eats a large share of "
        "safety stock dollars, lower its service target.",
        "- The trade-off table is the conversation with finance: each step up in service "
        "level costs a known amount of inventory. The ABC mix row shows that differentiating "
        "targets gets most of the fill rate for less stock than a uniform high target.",
        "- Simulated fill rate will land below the service target: the target is per "
        "replenishment cycle, the simulation counts every lost unit, and 8 weeks is a small sample.",
    ]
    OUT_MD.write_text("\n".join(lines))
    print(seg[["n", "fill_rate", "ss_weeks_of_demand", "revenue_share", "ss_value_share"]])
    print(trade.to_string(index=False))
    print(f"Plan -> {OUT_PLAN}\nTrade-off -> {OUT_TRADE}\nSummary -> {OUT_MD}")


if __name__ == "__main__":
    main()
