# worker

Python: odds ingestion → per-sport models → **de-vig → EV → Kelly → CLV** → ranked `ev_bets`.

## Run
```bash
python -m venv .venv && .venv\Scripts\Activate.ps1   # PowerShell
pip install -r requirements.txt
python -m worker.run --sport golf --dry-run          # sample odds, prints table, no DB/keys
pytest -q                                            # core math tests
```

## Layout
| Path | Real? | What |
|---|---|---|
| `worker/core/devig.py` | ✅ real + tested | American-odds conversion, multiplicative/power/**Shin** de-vig, EV, fractional Kelly |
| `worker/core/clv.py` | ✅ real + tested | Closing-line-value — the go/no-go metric |
| `worker/core/rationale.py` | ✅ real | 1–2 sentence explanation from SHAP drivers |
| `worker/run.py` | ✅ real (dry-run) | Orchestrator; correct market-type de-vig (props vs mutually-exclusive) |
| `worker/models/base.py` | ✅ interface | `SportModel` — implement one per sport |
| `worker/models/golf.py` | ⚠️ stub | Calibrated classifier scaffold; **connect `_load_training_frame()` to real features** |
| `worker/ingest/odds_api.py` | ⚠️ stub | `sample_market()` real; `fetch_odds()` needs the live HTTP + snapshot cache |
| `worker/db.py` | ✅ real | Service-role Postgres writer (bypasses RLS) |

## Before this is real
1. `GolfModel._load_training_frame()` → your golf feature pipeline (SG stats, course fit, form).
2. `odds_api.fetch_odds()` → live pull, persist to `odds_snapshots`, respect credit budget.
3. Replace `_explain()` placeholder with real `shap.TreeExplainer` output.
4. Report walk-forward AUC **and CLV** in `GolfModel.fit()` — that's the gate.
