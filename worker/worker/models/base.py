"""
SportModel — the interface every sport plugs into. The whole multi-sport design
rests on this: ingestion, devig, EV, and dashboard code are sport-agnostic; only
the model + feature engineering differ per sport (viability §1: "each sport is a
separate project"). Add a sport by implementing this, nothing else.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Selection:
    """One bettable outcome the model prices (a player to make the cut, a team ML)."""
    market: str            # 'make_cut', 'top_10', 'moneyline', ...
    name: str              # player/team/side label
    model_prob: float      # our estimated probability of the outcome
    shap_top: list[dict] = field(default_factory=list)  # [{feature, value}] drivers


class SportModel(ABC):
    """Implement one per sport. Kept deliberately small."""

    sport_id: str
    model_version: str

    @abstractmethod
    def fit(self) -> dict:
        """Train on historical data. Return metrics (walk-forward AUC/MAE/CLV...)."""

    @abstractmethod
    def predict_event(self, event: dict) -> list[Selection]:
        """Return priced selections for one upcoming event."""
