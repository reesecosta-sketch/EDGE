"""
Golf model — the first vertical and the CLV go/no-go gate (viability §4).

Golf is the recommended starting market: soft, prop-rich, high-variance, and it
maps cleanly onto bettable markets (make-cut, top-5, top-10, matchups). This class
is the *adapter* that turns per-player features into calibrated probabilities the
platform can devig against and rank.

STATUS: structural placeholder. `fit()` trains a gradient-boosted classifier on a
feature frame you supply; `predict_event()` emits calibrated make-cut / top-N
probabilities. Wire `_load_training_frame()` to your real feature pipeline (SG
data, course fit, form) before trusting any output. The probabilities below are
NOT real until that's connected.
"""
from __future__ import annotations

import numpy as np

from .base import Selection, SportModel


class GolfModel(SportModel):
    sport_id = "golf"
    model_version = "golf-0.1.0-scaffold"

    def __init__(self) -> None:
        self._models: dict = {}
        self._feature_cols: list[str] = []

    # ---- data hook (connect to your real feature pipeline) -------------------
    def _load_training_frame(self):
        """
        Return (X: DataFrame of numeric features, targets: dict of Series).
        Targets expected: 'made_cut' (0/1), 'top_5' (0/1), 'top_10' (0/1).
        Replace this stub with your real historical feature build.
        """
        raise NotImplementedError(
            "Connect GolfModel._load_training_frame() to your golf feature "
            "pipeline (SG stats, course fit, recent form). Until then run the "
            "worker with --dry-run to exercise the devig/EV path on sample odds."
        )

    # ---- training ------------------------------------------------------------
    def fit(self) -> dict:
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.ensemble import HistGradientBoostingClassifier

        X, targets = self._load_training_frame()
        self._feature_cols = list(X.columns)
        metrics: dict = {}
        for market, y in targets.items():
            base = HistGradientBoostingClassifier(
                max_iter=300, learning_rate=0.05, max_depth=5,
                min_samples_leaf=20, l2_regularization=0.1, random_state=17,
            )
            # Calibration matters: EV is only meaningful if probabilities are
            # calibrated. Isotonic on top of the booster.
            model = CalibratedClassifierCV(base, method="isotonic", cv=5)
            model.fit(X.values, y.values)
            self._models[market] = model
        # TODO: report walk-forward AUC + CLV here (see core/clv.py). Placeholder:
        metrics["note"] = "fit complete; wire walk-forward + CLV reporting"
        return metrics

    # ---- inference -----------------------------------------------------------
    def predict_event(self, event: dict) -> list[Selection]:
        """
        event = {"players": [{"name": ..., "features": {...}}, ...]}
        Emits make_cut / top_10 selections per player with SHAP-derived drivers.
        Field-normalizes top-N so probabilities are coherent (Σ top_10 ≈ 10).
        """
        if not self._models:
            raise RuntimeError("call fit() before predict_event()")

        players = event["players"]
        feats = np.array([[p["features"].get(c, np.nan) for c in self._feature_cols]
                          for p in players], dtype=float)

        out: list[Selection] = []
        raw_top10 = None
        for market, model in self._models.items():
            probs = model.predict_proba(feats)[:, 1]
            if market == "top_10":
                # exactly 10 players make top 10 => normalize the field to sum 10
                s = probs.sum()
                probs = np.minimum(probs * (10.0 / s), 0.97) if s > 0 else probs
                raw_top10 = probs
            for p, prob in zip(players, probs):
                out.append(Selection(
                    market=market,
                    name=p["name"],
                    model_prob=float(prob),
                    shap_top=self._explain(p),
                ))
        del raw_top10
        return out

    def _explain(self, player: dict) -> list[dict]:
        """
        Top drivers for the 1-2 sentence rationale. Real implementation: run SHAP
        (shap.TreeExplainer) on the calibrated model's base estimator and take the
        top |value| features for THIS player. Placeholder echoes provided features.
        """
        feats = player.get("features", {})
        ranked = sorted(feats.items(), key=lambda kv: abs(kv[1] or 0), reverse=True)
        return [{"feature": k, "value": round(float(v), 3)}
                for k, v in ranked[:3] if v is not None]
