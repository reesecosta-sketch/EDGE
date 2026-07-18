"""Tests for model-free positive-EV detection (consensus de-vig line shopping)."""
from worker.core.positive_ev import compute_event_bets


def _event(books):
    return {"market": "moneyline", "books": books}


def test_no_bets_when_books_agree():
    # All books identical & efficient => nothing beats the consensus.
    ev = _event([
        {"book": "a", "prices": {"X": -110, "Y": -110}},
        {"book": "b", "prices": {"X": -110, "Y": -110}},
        {"book": "c", "prices": {"X": -110, "Y": -110}},
    ])
    assert compute_event_bets(ev, min_ev=0.02) == []


def test_flags_soft_book_outlier():
    # Two sharp books ~50/50; one soft book prices Y way too generously (+140).
    ev = _event([
        {"book": "sharp1", "prices": {"X": -110, "Y": -110}},
        {"book": "sharp2", "prices": {"X": -108, "Y": -112}},
        {"book": "soft",   "prices": {"X": -150, "Y": +140}},
    ])
    bets = compute_event_bets(ev, min_ev=0.02)
    assert bets, "expected the soft +140 price on Y to be flagged"
    top = bets[0]
    assert top["book"] == "soft" and top["selection"] == "Y"
    assert top["ev"] > 0
    assert 0.0 <= top["kelly_frac"] <= 0.05


def test_requires_two_books():
    ev = _event([{"book": "solo", "prices": {"X": +200, "Y": -250}}])
    assert compute_event_bets(ev, min_ev=0.0) == []


def test_consensus_is_devigged_below_one():
    # model_prob (consensus fair) for both sides should sum to ~1 (vig removed).
    ev = _event([
        {"book": "a", "prices": {"X": -120, "Y": +100}},
        {"book": "b", "prices": {"X": -125, "Y": +105}},
    ])
    bets = compute_event_bets(ev, min_ev=-1.0)  # flag everything
    fair = {b["selection"]: b["model_prob"] for b in bets}
    assert abs(sum(set(fair.values())) - 1.0) < 1e-6 or abs(fair["X"] + fair["Y"] - 1.0) < 1e-6
