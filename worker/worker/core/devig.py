"""
De-vigging, expected value, and Kelly staking — the core of the whole product.

The viability analysis is blunt about this: EV must be computed against the
*no-vig fair probability* of a sharp market, NOT the raw implied probability of
one side. Raw implied probs across a market sum to >100% (the hold), so naive
"model_prob - implied_prob" systematically misstates edge. Everything here exists
to compute EV honestly.

American odds convention throughout the platform (matches the sportsbooks and the
`price integer` column in the schema).
"""
from __future__ import annotations

import math
from typing import Iterable, Literal, Sequence

DevigMethod = Literal["multiplicative", "power", "shin"]


# --------------------------------------------------------------------- odds conv
def american_to_prob(price: int | float) -> float:
    """Raw implied probability of a single American-odds price (still contains vig)."""
    price = float(price)
    if price > 0:
        return 100.0 / (price + 100.0)
    return -price / (-price + 100.0)


def american_to_decimal(price: int | float) -> float:
    price = float(price)
    if price > 0:
        return price / 100.0 + 1.0
    return 100.0 / (-price) + 1.0


def prob_to_american(p: float) -> int:
    """Fair probability -> American odds (no vig). Inverse of american_to_prob."""
    if not 0.0 < p < 1.0:
        raise ValueError(f"probability must be in (0,1), got {p}")
    if p >= 0.5:
        return int(round(-100.0 * p / (1.0 - p)))
    return int(round(100.0 * (1.0 - p) / p))


# ------------------------------------------------------------------------ de-vig
def remove_vig(
    prices: Sequence[int | float],
    method: DevigMethod = "multiplicative",
) -> list[float]:
    """
    Convert a full market's American prices into no-vig fair probabilities that
    sum to 1. Pass EVERY selection in the market (both sides of a moneyline, or
    all N players in an outright) — de-vigging needs the complete book.

    method:
      "multiplicative" — divide each implied prob by the booksum. Robust default.
      "power"          — raise implied probs to a common exponent k s.t. they sum
                         to 1. Corrects favorite-longshot bias better than mult.
      "shin"           — Shin (1993) model; estimates an insider-trading fraction
                         z and backs out fair probs. Best for two-way sharp lines.
    """
    implied = [american_to_prob(p) for p in prices]
    booksum = sum(implied)
    if booksum <= 0:
        raise ValueError("non-positive booksum; bad prices")

    if method == "multiplicative":
        return [p / booksum for p in implied]
    if method == "power":
        return _power_devig(implied)
    if method == "shin":
        return _shin_devig(implied)
    raise ValueError(f"unknown devig method: {method}")


def _power_devig(implied: Sequence[float]) -> list[float]:
    """Find k with sum(p_i**k) == 1, return p_i**k. Bisection on k in [0.2, 6]."""
    lo, hi = 0.2, 6.0
    for _ in range(100):
        k = 0.5 * (lo + hi)
        s = sum(p ** k for p in implied)
        if abs(s - 1.0) < 1e-12:
            break
        # sum decreases as k grows (each p_i < 1), so booksum>1 => raise k
        if s > 1.0:
            lo = k
        else:
            hi = k
    k = 0.5 * (lo + hi)
    fair = [p ** k for p in implied]
    total = sum(fair)
    return [f / total for f in fair]  # renormalize against tiny residual


def _shin_devig(implied: Sequence[float]) -> list[float]:
    """
    Shin model. With booksum Π and implied π_i, fair prob is
        p_i = ( sqrt(z^2 + 4(1-z) * π_i^2 / Π) - z ) / (2(1-z))
    Solve for z in [0, 0.5) so that sum(p_i) == 1. Bisection.
    """
    pi_sum = sum(implied)

    def fair_for(z: float) -> list[float]:
        out = []
        for pi in implied:
            num = math.sqrt(z * z + 4.0 * (1.0 - z) * pi * pi / pi_sum) - z
            out.append(num / (2.0 * (1.0 - z)))
        return out

    lo, hi = 0.0, 0.5
    for _ in range(100):
        z = 0.5 * (lo + hi)
        s = sum(fair_for(z))
        if abs(s - 1.0) < 1e-12:
            break
        # larger z shrinks favorites more; sum decreases as z grows
        if s > 1.0:
            lo = z
        else:
            hi = z
    fair = fair_for(0.5 * (lo + hi))
    total = sum(fair)
    return [f / total for f in fair]


# --------------------------------------------------------------------------- EV
def expected_value(model_prob: float, price: int | float) -> float:
    """
    EV per 1 unit staked, given OUR probability and the OFFERED American price.
        EV = p * decimal_odds - 1
    Positive => the offered price pays more than our fair estimate implies.
    """
    return model_prob * american_to_decimal(price) - 1.0


def edge(model_prob: float, novig_prob: float) -> float:
    """Probability-point edge vs. the sharp no-vig fair line. The honest edge."""
    return model_prob - novig_prob


def kelly_fraction(
    model_prob: float,
    price: int | float,
    fraction: float = 0.25,
    cap: float = 0.05,
) -> float:
    """
    Fractional-Kelly stake as a fraction of bankroll.
        f* = (b*p - (1-p)) / b,  where b = decimal_odds - 1
    Scaled by `fraction` (quarter-Kelly by default — full Kelly is too swingy for
    the estimation error in these models) and capped. Never returns < 0.
    """
    b = american_to_decimal(price) - 1.0
    if b <= 0:
        return 0.0
    full = (b * model_prob - (1.0 - model_prob)) / b
    if full <= 0:
        return 0.0
    return min(full * fraction, cap)
