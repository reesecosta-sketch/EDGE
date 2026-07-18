"""
Model-free positive-EV detection (line shopping vs. the no-vig market consensus).

No predictive model: for a 2-way market we de-vig every book's own prices, average
those no-vig probabilities into a cross-book CONSENSUS fair line, then flag any
book whose offered price beats that consensus (i.e. pays more than fair implies).
This is exactly the honest +EV approach the viability analysis pointed to — the
edge is a soft book mispricing vs. the market, not a claim to out-predict Vegas.
"""
from __future__ import annotations

from statistics import mean

from .devig import expected_value, kelly_fraction, remove_vig


def compute_event_bets(event: dict, min_ev: float, kelly_frac: float = 0.25) -> list[dict]:
    """
    event = {
      "market": "moneyline",
      "books": [ {"book": "draftkings", "prices": {"Team A": -150, "Team B": 130}}, ... ]
    }
    Returns +EV bets sorted by EV. Handles 2-outcome markets only.
    """
    books = event.get("books", [])

    # Per-book no-vig line (only well-formed 2-way books).
    book_fair: dict[str, dict[str, float]] = {}
    selections: list[str] | None = None
    for b in books:
        prices = b.get("prices", {})
        if len(prices) != 2:
            continue
        names = list(prices.keys())
        if selections is None:
            selections = names
        if set(names) != set(selections):
            continue  # inconsistent labeling across books; skip
        fair = remove_vig([prices[names[0]], prices[names[1]]])
        book_fair[b["book"]] = {names[0]: fair[0], names[1]: fair[1]}

    if selections is None or len(book_fair) < 2:
        return []  # need at least two books for a meaningful consensus

    # Consensus fair prob = mean of book no-vig probs, renormalized to sum to 1.
    consensus: dict[str, float] = {}
    for s in selections:
        vals = [bf[s] for bf in book_fair.values() if s in bf]
        consensus[s] = mean(vals) if vals else 0.0
    total = sum(consensus.values())
    if total <= 0:
        return []
    consensus = {s: p / total for s, p in consensus.items()}

    # Flag every book price that is +EV against the consensus fair line.
    out: list[dict] = []
    for b in books:
        for s, price in b.get("prices", {}).items():
            if s not in consensus:
                continue
            fair = consensus[s]
            ev = expected_value(fair, price)
            if ev >= min_ev:
                out.append({
                    "selection": s,
                    "book": b["book"],
                    "price": int(price),
                    "model_prob": fair,                              # consensus = our estimate
                    "novig_prob": book_fair.get(b["book"], {}).get(s),  # this book's own line
                    "ev": ev,
                    "kelly_frac": kelly_fraction(fair, price, kelly_frac),
                })
    out.sort(key=lambda x: x["ev"], reverse=True)
    return out


def rationale_for(bet: dict, market_label: str) -> str:
    fair = bet["model_prob"]
    price = bet["price"]
    odds = f"+{price}" if price > 0 else f"{price}"
    return (f"{bet['book'].title()} lists {bet['selection']} at {odds} on the "
            f"{market_label}; the no-vig market consensus implies {fair*100:.0f}% "
            f"- a {bet['ev']*100:+.1f}% EV edge vs. fair.")
