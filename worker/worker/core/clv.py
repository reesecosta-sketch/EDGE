"""
Closing Line Value — the only leading indicator of a real edge (viability §4).

CLV measures whether the price you bet was better than the (no-vig) closing price.
Consistent positive CLV precedes profit; a good backtest that ignores CLV does not.
This module is what the golf go/no-go gate reports.
"""
from __future__ import annotations

from dataclasses import dataclass

from .devig import american_to_prob, remove_vig, DevigMethod


@dataclass
class ClvResult:
    bet_prob: float        # no-vig fair prob implied by the price we bet
    close_prob: float      # no-vig fair prob implied by the closing price
    clv_points: float      # close_prob - bet_prob, in probability points
    beat_close: bool       # did the market move toward our side?


def clv_two_way(
    bet_price: int,
    bet_price_other: int,
    close_price: int,
    close_price_other: int,
    method: DevigMethod = "multiplicative",
) -> ClvResult:
    """
    CLV for a two-way market. Provide both sides at bet time and at close so each
    can be de-vigged properly (you cannot de-vig one price in isolation).

    Positive clv_points => the fair probability of our selection rose by close,
    i.e. we bet a price better than the market's eventual consensus. Good.
    """
    bet_fair = remove_vig([bet_price, bet_price_other], method)[0]
    close_fair = remove_vig([close_price, close_price_other], method)[0]
    delta = close_fair - bet_fair
    return ClvResult(bet_fair, close_fair, delta, delta > 0)


def clv_points_from_novig(bet_novig_prob: float, close_novig_prob: float) -> float:
    """When both no-vig probs are already computed (e.g. multi-way outrights)."""
    return close_novig_prob - bet_novig_prob


def summarize_clv(clv_points: list[float]) -> dict:
    """
    Aggregate a sample of bets into the go/no-go numbers. `beat_rate` is the share
    of bets with positive CLV; `mean_clv` is the average probability-point gain.
    Rule of thumb for the gate: beat_rate materially above 50% AND mean_clv > 0,
    over a few hundred bets, is the minimum evidence of a real edge.
    """
    n = len(clv_points)
    if n == 0:
        return {"n": 0, "beat_rate": None, "mean_clv": None}
    beat = sum(1 for c in clv_points if c > 0)
    return {
        "n": n,
        "beat_rate": beat / n,
        "mean_clv": sum(clv_points) / n,
    }
