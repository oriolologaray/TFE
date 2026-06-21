"""Shared cached data loading for all app pages."""

from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

CLASS_LABELS = ["home_win", "draw", "away_win"]
CLASS_DISPLAY = {"home_win": "Victoria local", "draw": "Empate", "away_win": "Victoria visitante"}
CLASS_COLORS = {"home_win": "#1f77b4", "draw": "#ff7f0e", "away_win": "#d62728"}

FEATURE_COLS = [
    # Cumulative stats - home (17)
    "goals_home", "shots_home", "shots_on_target_home", "shots_in_box_home",
    "passes_home", "pressures_home", "duels_won_home", "clearances_home",
    "blocks_home", "carries_home", "yellow_cards_home", "red_cards_home",
    "attacks_third_home", "xg_home", "xg_last15_home", "shots_last15_home",
    "pressures_last15_home",
    # Cumulative stats - away (17)
    "goals_away", "shots_away", "shots_on_target_away", "shots_in_box_away",
    "passes_away", "pressures_away", "duels_won_away", "clearances_away",
    "blocks_away", "carries_away", "yellow_cards_away", "red_cards_away",
    "attacks_third_away", "xg_away", "xg_last15_away", "shots_last15_away",
    "pressures_last15_away",
    # Derived (14)
    "score_diff", "xg_diff", "shots_diff",
    "possession_home", "pass_completion_home", "pass_completion_away",
    "minutes_remaining", "players_diff", "total_goals",
    "xg_per_shot_home", "xg_per_shot_away",
    "goals_minus_xg_home", "goals_minus_xg_away",
    "is_womens",
]


@st.cache_resource
def load_models() -> dict:
    models = {}
    for name, filename in [("XGBoost", "xgboost.pkl"), ("Random Forest", "random_forest.pkl"), ("SVM Lineal", "svm_linear_calibrated.pkl")]:
        path = DATA_DIR / filename
        if path.exists():
            models[name] = joblib.load(path)
    return models


def predict_proba_named(model, X) -> dict[str, float]:
    """Return {class_name: probability} handling XGBoost integer-encoded classes.

    XGBoost 2.x stores model.classes_ as [0, 1, 2] when trained on string labels.
    The verified mapping (confirmed against minute-90 predictions on known results):
      0 -> home_win, 1 -> draw, 2 -> away_win
    This is the order the LabelEncoder saw the classes in the training data,
    NOT alphabetical order.
    """
    import numpy as np
    proba_raw = model.predict_proba(X)[0]
    classes = model.classes_

    if np.issubdtype(type(classes[0]), np.integer):
        int_to_class = {0: "home_win", 1: "draw", 2: "away_win"}
        classes = [int_to_class[int(c)] for c in classes]

    return {str(cls): float(p) for cls, p in zip(classes, proba_raw)}


@st.cache_data
def load_features() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "features_test.parquet")


@st.cache_data
def load_metadata() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "match_metadata.parquet")


@st.cache_data
def load_timeline() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "timeline_events.parquet")
