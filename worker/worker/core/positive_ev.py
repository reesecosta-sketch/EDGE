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


def compute_event_bets(event: dict, min_ev: float, kelly_frac: float = 0.25,
                       max_outcomes: int = 200) -> list[dict]:
    """
    event = {
      "market": "moneyline",
      "books": [ {"book": "draftkings", "prices": {"Team A": -150, "Team B": 130}}, ... ]
    }
    Handles ANY number of outcomes: 2-way (moneyline), 3-way (soccer 1X2), and
    N-way outrights (golf/NASCAR winner). Returns +EV bets sorted by EV.
    """
    books = event.get("books", [])

    # De-vig each book over ITS OWN listed outcomes (books may list different
    # subsets for outrights, so we don't require identical selection sets).
    book_fair: dict[str, dict[str, float]] = {}
    all_sels: set[str] = set()
    for b in books:
        prices = b.get("prices", {})
        if not (2 <= len(prices) <= max_outcomes):
            continue
        names = list(prices.keys())
        fair = remove_vig([prices[n] for n in names])
        book_fair[b["book"]] = dict(zip(names, fair))
        all_sels.update(names)

    if len(book_fair) < 2:
        return []  # need at least two books for a meaningful consensus

    # Consensus fair prob per selection = mean across books that list it (require
    # >=2 books so a lone outlier can't define its own "fair"). Renormalize to 1.
    consensus: dict[str, float] = {}
    for s in all_sels:
        vals = [bf[s] for bf in book_fair.values() if s in bf]
        if len(vals) >= 2:
            consensus[s] = mean(vals)
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
