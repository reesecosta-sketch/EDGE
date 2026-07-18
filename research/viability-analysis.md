# Viability Analysis: Automated Multi-Sport +EV Betting Platform

**Prepared:** 2026-07-18
**Verdict up front:** **QUALIFIED NO** to the project *as specified* — **QUALIFIED YES** to a reframed, narrower version. Read §4 first if you read nothing else.

---

## 0. The one thing you need to internalize before spending a dollar

The request is written as a **machine-learning problem**. It is actually a **market-efficiency problem**, and that reframing changes almost every downstream decision.

Your two attached models (the golf cut/finish pipeline and the NASCAR finish/DK model) are genuinely strong — walk-forward validation, isotonic calibration, conformal intervals, hurdle models for zero-inflation, LambdaRank for permutation targets, purged time splits. That is better engineering than most retail bettors *or* most "betting model" blog posts. So this is not a skills problem.

The problem is this: **predicting outcomes accurately is necessary but nowhere near sufficient for +EV.** The betting line is not a passive target you out-predict. It is the aggregated forecast of every sharp bettor and syndicate on earth, already adjusted for the money bet into it. To have positive expected value you don't need a *good* model — you need a model that is **more accurate than the closing consensus of a market that has already priced in everything you can cheaply know.**

For the major markets you named — NFL sides/totals, college basketball spreads, soccer 1X2 — that market is brutally efficient. A Random Forest / XGBoost model trained on public box-score stats will, in the overwhelming majority of cases, produce probabilities *less* accurate than the no-vig closing line. When you then compute "EV" against the book's implied probability, you will see lots of green +EV numbers. **They will be mostly noise, vig, and your model's calibration error — not real edge.** This is the single most common way sophisticated people lose money in this space, and the requirements doc as written walks straight into it.

The good news: real edges exist, but they live in specific, identifiable places (§4), and your golf model is already sitting near one of them.

---

## 1. Technical Viability Assessment

### Can it be built with current technology?
Yes, unambiguously. Nothing in the stack is exotic. Postgres + Python (pandas/scikit/XGBoost/LightGBM) + Streamlit + SHAP + a scheduler is a well-trodden path, and you've already built two-thirds of the modeling layer twice. **Buildability is not the risk. Profitability is.**

### Primary technical risks (ranked by how likely they are to kill the project)

1. **Beating the closing line (existential).** If your model can't consistently beat the closing line, there is no product — just a slower way to lose the vig. This must be *proven on historical closing odds* before any UI work. See §4 validation gate.

2. **EV computed against the wrong baseline (very common, subtle).** EV must be computed against the **de-vigged ("no-vig") fair probability**, not the raw implied probability of one side. Raw implied probs across both sides sum to ~104–110% (that's the hold). Naively comparing your model prob to a single side's raw implied prob systematically distorts EV. Correct method: take both sides' odds → remove vig (multiplicative, or better, Shin/power method for favorite-longshot bias) → that no-vig line *is* the sharp market's fair probability → your edge is `model_prob − novig_prob`. And here's the uncomfortable part: **the de-vigged line from a sharp book (Pinnacle, Circa) is usually a better probability estimate than your model.** For most bets, the honest answer to "what's the true probability?" is "roughly whatever Pinnacle says."

3. **Multiple-testing / false discovery.** Screening thousands of bets daily across six sports, some will show large +EV by chance. Without correction (and without out-of-sample CLV confirmation) you'll bet the noise. Flexible models make this worse, not better.

4. **Data leakage.** Your NASCAR file already handles this well (dominator/DNF stats excluded as race-day outcomes; leak-free rolling means kept). At platform scale across six sports, leakage will be your most frequent silent bug — a feature that encodes the result, a stat updated post-game, a line captured after news broke.

5. **Odds data latency & coverage.** +EV opportunities decay in **seconds to minutes**. A daily batch dashboard will surface lines that are already gone (the book saw the same thing and moved). Real +EV screening is a near-real-time polling problem, which is a different, more expensive architecture than "train a model, render a table."

### API / data reality check

- **balldontlie** (`api.balldontlie.io`): NBA-centric, generous but rate-limited free tier; fine for stats, **provides no betting odds**. Good for features, not for lines.
- **CollegeFootballData** (`collegefootballdata.com`): excellent free CFB stats/historical data, includes some lines. One of the better sources you listed.
- **TheRundown / prop-line / OddsMagnet**: odds aggregators. This is where cost, rate limits, and **Terms of Service** bite. Most odds APIs: (a) charge meaningfully for real-time/high-frequency access, (b) rate-limit hard on cheap tiers, (c) **prohibit commercial redistribution** in their ToS. The Odds API, OddsJam's API, etc. are priced per-request/per-tier and add up fast at polling frequencies.
- **Scraping sportsbooks directly** (implied by "scraped from live odds APIs"): violates essentially every sportsbook's ToS and is an ongoing cat-and-mouse maintenance burden. Not a foundation to build a product on.
- **Historical closing lines** (the data you *most* need for the validation gate) are the hardest and most expensive to get cleanly. Budget for this specifically.

**Rotate the keys you pasted** (see the chat message) before any of this.

---

## 2. Competitive Landscape

This is a **mature, well-funded category**, which is itself a signal that easy edges are gone.

| Product | What it does | Why it matters to you |
|---|---|---|
| **OddsJam** | Real-time +EV screener + arbitrage + line shopping across dozens of books | The thing your dashboard describes, already built, at scale, near-real-time |
| **Unabated** | Sharp-line-anchored fair value, market devig, "no-vig" tools | Does the correct EV math (§1.2) as a core feature |
| **OddsShopper / Outlier / Pikkit / Rebet** | +EV props, projections, bet tracking | Props-focused, mobile, growing |
| **DIY / r/algobetting** | Roll-your-own model builders | Your actual peer group; mostly focused on CLV, not black-box ML |

**Honest differentiation assessment:** "Ensemble ML model that finds +EV across six sports with a Streamlit dashboard" is **not differentiated** — the incumbents win on odds-feed breadth, speed, and book coverage, which are capital/ops problems you can't out-engineer solo. Where an individual *can* differentiate is a **genuine modeling edge in a specific, less-efficient market** that the aggregators price generically or ignore. That is a vertical play, not a platform play.

**Evidence of demand:** Yes — the category's size proves demand exists. But demand for *tools* mostly converts to subscriptions, not betting profit, and the profitable-edge segment is small and adversarial (books limit and ban winners; see §3).

---

## 3. The practical killers nobody puts in the requirements doc

Even with a real edge, these constrain the business:

- **Bookmaker limits & bans.** Soft/recreational books (where the beatable lines are) **limit or close winning accounts fast** — sometimes within days. Sharp books (Pinnacle, Circa) let you win but offer thinner edges. This caps how much any real edge can earn regardless of model quality. It is the single biggest reason "I have a +EV model" rarely becomes "I have income."
- **Automated betting violates ToS.** Placing bets via bot/API is against virtually every sportsbook's terms and is a fast route to confiscated funds and a permanent ban. A tool that *recommends* bets for a human to place manually is a very different (and safer) product than one that *places* them. I'd build only the former.
- **Legal / jurisdiction.** Sports betting legality varies by state/country; offering a paid betting-adjacent *service* carries its own regulatory exposure. Get this checked for your jurisdiction before monetizing.
- **Edges decay.** Any public or easily-derived edge erodes as others find it. This is a maintenance treadmill, not a build-once asset.

None of these are reasons to never touch the space. They are reasons the specified "fully automated, six-sport, black-box, daily dashboard" framing over-promises.

---

## 4. Go / No-Go

### Recommendation: **Reframe, then a conditional GO on a narrow slice.**

**Kill these parts of the spec (they are the fatal-flaw parts):**
- ❌ "Six sports at launch." Each sport is a separate data pipeline, feature set, and efficiency profile. This is 6 projects wearing a trenchcoat. It guarantees you build breadth before proving edge.
- ❌ "Model beats the market on major-market sides/spreads (NFL/CBB/soccer moneyline)." Most efficient markets on earth. Don't fight there first, maybe not ever.
- ❌ "Fully automated betting." Build a *decision-support* tool a human acts on. Never auto-place.
- ❌ EV vs. raw implied probability. Use de-vigged fair prob from a sharp book.

**Keep and double down on:**
- ✅ Your existing modeling rigor (walk-forward, calibration, SHAP explainability — the explainability requirement is easy and genuinely good; SHAP on tree models is cheap and you're right to want it).
- ✅ **One vertical where a solo modeler realistically has edge.** Your strongest candidate is *already on your disk*: **golf**. Golf betting markets (outrights, 2-/3-ball matchups, top-5/top-10, make-cut) are **structurally softer** than NFL sides — huge fields, high variance, many bookmaker-priced props, and books can't sharpen 156 individual prices as tightly as one NFL spread. Your golf pipeline's outputs (P(make cut), P(top 5), P(top 10), finish distribution) map **directly** onto real, bettable golf markets. NASCAR is a similar structurally-soft, prop-rich market and you have a model there too. **Player props in general** are the retail-accessible frontier because books hang them softer and can't price thousands of them precisely.

### What to validate *first* — the single gate

**Before building any dashboard, database, or UI, prove Closing Line Value (CLV).**

1. Pull historical **closing** odds for the market you're attacking (start: golf top-10 / make-cut, or matchups).
2. For each historical event, generate your model's probability **as of before the line closed** (strict walk-forward — you already do this).
3. De-vig the closing line to a fair probability.
4. Measure: **when your model flags a bet as +EV vs. the *opening* or mid-week line, does that bet's price systematically move in your favor by close?** Positive CLV over a few hundred bets is the only leading indicator of a real edge. Profit follows CLV; nothing follows a good backtest that ignores CLV.
5. Only if CLV is positive and stable → build the pipeline/DB/dashboard around it.

If you can't beat the closing line in a *soft* market like golf props, you cannot beat it anywhere, and the honest move is to stop — cheaply, before the platform build.

### Complexity estimate

| Scope | Effort | Notes |
|---|---|---|
| **CLV validation harness, golf only** (no UI) | **1–3 weeks** | Reuses your existing golf model. This is the go/no-go experiment. Do this first. |
| **MVP: one sport, devig +EV screen, Streamlit dashboard + SHAP rationale** | **4–8 weeks** | Only if the gate passes. Postgres, odds ingestion, daily refresh, ranked table, filters. |
| **Near-real-time odds polling + multi-book line shopping** | **+2–3 months** | Where it stops being a weekend project. Ops-heavy, API-cost-heavy. |
| **Full spec: 6 sports, automated, "beats Vegas" platform** | **Many months + ongoing**, and likely **-EV in the major markets regardless of effort** | Not recommended as stated. |

**Hardest technical challenges, in order:** (1) proving CLV at all; (2) clean historical *closing* odds data; (3) correct devig + calibration so EV means something; (4) avoiding leakage and multiple-testing false positives at scale; (5) near-real-time freshness if you go beyond a daily batch.

---

## 5. Concrete next step

Build the **golf CLV harness** on top of your existing `s05_model.py`. Reuse the pipeline; add one module that:
- ingests historical opening + closing odds for golf top-10 / make-cut / matchups,
- runs your model strictly as-of pre-close,
- de-vigs the market, computes `model_prob − novig_prob`,
- reports **CLV and calibration** (reliability curve) over all historical events.

That is a 1–3 week experiment that answers the only question that matters — *do you actually have an edge?* — before you invest in Postgres, Streamlit, odds subscriptions, or a second sport. Everything in the original spec is worth building **if and only if** that number comes back positive.

**Bottom line:** The platform as specified has a fatal flaw (it assumes model accuracy equals edge in the most efficient markets, computed against the wrong baseline). But you personally are one focused experiment away from knowing whether a *narrower, honest* version is real — and your golf model is the right place to run it.

---

### Notes on the reference material you provided
- Pinnacle's "how to build a model" and Unabated's "road to sports betting models" are the two most useful links you listed — both emphasize devig/CLV over raw prediction. Weight them heavily.
- The academic papers (arXiv 1710.02824 on soccer, PLOS ONE, the theses) are legitimate but report edges that are thin, market-specific, and often pre-date the current efficiency of these markets. Treat published edges as "existed once, in that market" not "available now."
- Reminder: the API keys in your prompt are exposed and should be rotated.
