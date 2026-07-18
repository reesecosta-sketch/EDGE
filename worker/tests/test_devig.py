"""Tests for the EV/devig core — the math that must be right or the product loses money."""
import math

import pytest

from worker.core.devig import (american_to_decimal, american_to_prob,
                               expected_value, kelly_fraction, prob_to_american,
                               remove_vig)
from worker.core.clv import clv_two_way


def test_american_to_prob_known_values():
    assert math.isclose(american_to_prob(-110), 110 / 210, rel_tol=1e-9)
    assert math.isclose(american_to_prob(+100), 0.5, rel_tol=1e-9)
    assert math.isclose(american_to_prob(+200), 1 / 3, rel_tol=1e-9)


def test_decimal_conversion():
    assert math.isclose(american_to_decimal(+100), 2.0, rel_tol=1e-9)
    assert math.isclose(american_to_decimal(-200), 1.5, rel_tol=1e-9)


def test_prob_to_american_roundtrip():
    # Probability is the invariant; the +100/-100 even-money sign is ambiguous,
    # so round-trip through probability rather than asserting the exact price.
    for price in (-350, -110, +145, +900):
        p = american_to_prob(price)
        assert math.isclose(american_to_prob(prob_to_american(p)), p, abs_tol=1e-4)


@pytest.mark.parametrize("method", ["multiplicative", "power", "shin"])
def test_devig_sums_to_one(method):
    fair = remove_vig([-110, -110], method=method)
    assert math.isclose(sum(fair), 1.0, abs_tol=1e-9)
    # symmetric market => ~50/50 after removing vig
    assert math.isclose(fair[0], 0.5, abs_tol=1e-6)


def test_devig_removes_hold():
    # -110/-110 implies 52.38% each = 104.76% booksum; fair must be below implied
    implied = american_to_prob(-110)
    fair = remove_vig([-110, -110], "multiplicative")[0]
    assert fair < implied
    assert math.isclose(fair, 0.5, abs_tol=1e-9)


def test_expected_value_sign():
    # We think 60%; price is +100 (implies 50%) => clearly +EV
    assert expected_value(0.60, +100) > 0
    # We think 40%; price -200 (implies 66.7%) => -EV
    assert expected_value(0.40, -200) < 0


def test_kelly_nonnegative_and_capped():
    assert kelly_fraction(0.40, -200) == 0.0          # no edge => no stake
    f = kelly_fraction(0.70, +100, fraction=0.25, cap=0.05)
    assert 0.0 < f <= 0.05                              # capped


def test_clv_positive_when_line_moves_our_way():
    # Bet Player at +120 (other -140); closes at -110 (other -110): moved our way
    r = clv_two_way(bet_price=+120, bet_price_other=-140,
                    close_price=-110, close_price_other=-110)
    assert r.beat_close
    assert r.clv_points > 0
