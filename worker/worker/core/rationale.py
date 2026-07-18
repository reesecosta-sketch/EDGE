"""
Turns a bet + its SHAP drivers into the 1-2 sentence explanation the dashboard
shows (the explainability requirement). Deterministic, no LLM — cheap and honest.
"""
from __future__ import annotations

from .devig import edge


_MARKET_LABEL = {
    "make_cut": "make the cut",
    "top_5": "finish top 5",
    "top_10": "finish top 10",
    "moneyline": "win outright",
    "spread": "cover the spread",
}


def build_rationale(
    selection: str,
    market: str,
    model_prob: float,
    novig_prob: float | None,
    shap_top: list[dict],
) -> str:
    """e.g. 'Model gives Player D a 71% chance to make the cut vs. 64% fair — a
    +7.0pt edge, driven mainly by course_fit and sg_approach.'"""
    action = _MARKET_LABEL.get(market, market)
    pct = f"{model_prob * 100:.0f}%"

    if novig_prob is not None:
        e = edge(model_prob, novig_prob) * 100
        edge_clause = (f" vs. {novig_prob * 100:.0f}% fair - a "
                       f"{e:+.1f}pt edge")
    else:
        edge_clause = ""

    drivers = [d["feature"] for d in shap_top[:3]]
    if len(drivers) >= 2:
        driver_clause = f", driven mainly by {drivers[0]} and {drivers[1]}"
    elif drivers:
        driver_clause = f", driven mainly by {drivers[0]}"
    else:
        driver_clause = ""

    return (f"Model gives {selection} a {pct} chance to {action}"
            f"{edge_clause}{driver_clause}.")
