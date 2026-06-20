# TFE — Football Match Result Prediction

Master's thesis at UNIR (Máster en Inteligencia Artificial).
Team: Arnau Armengol Sayavera, Laura Chavarria Solé, Oriol Ologaray Arasa.
Director: Víctor Daniel Díaz Suárez.

## Goal

Predict P(home_win), P(draw), P(away_win) at every minute of a football match, simulated from historical event data. Target: ≥70% accuracy on test set. Multiclass classification problem following CRISP-DM methodology.

## Dataset

**Source:** StatsBomb Open Data — `datasets/statsbomb_events.csv`
- 12.2M rows, 28 columns, 3,464 matches, 21 competitions
- One row per action (event-level). Key columns: `match_id`, `period`, `minute`, `second`, `team_name`, `is_home`, `event_type`, `xg`, `shot_outcome`, `pass_outcome`, `loc_x`, `loc_y`, `final_result`, `final_score_home`, `final_score_away`
- `xg` and outcome columns are 99%+ NaN (structural: only populated for the relevant event type)

**Modeling dataset:** `datasets/match_minute_features.csv`
- One row per (match_id, minute), 90 rows per match, ~311,760 rows total
- Built by `notebooks/feature_engineering.ipynb`

## Phase Status (CRISP-DM)

| Phase | Notebook | Status |
|---|---|---|
| 2 — Data Understanding (EDA) | `notebooks/eda.ipynb` | Done |
| 3 — Data Preparation | `notebooks/feature_engineering.ipynb` | Done |
| 4 — Modeling | `notebooks/modeling.ipynb` | Done (RF + XGBoost + SVM lineal trained; XGBoost selected as final model) |
| 5 — Evaluation & Deployment | `notebooks/modeling.ipynb` (sections 6–7) | Evaluation done; deployment section in thesis is empty placeholder |

### Model Results (test set: seasons 2020–2025, 692 matches, 62,280 rows)

| Model | Accuracy | Macro-F1 | Log-loss | Acc @ min 60 |
|---|---|---|---|---|
| Random Forest | 65.0% | 63.3% | 0.772 | 70.4% |
| XGBoost (**final**) | 65.4% | 62.7% | 0.753 | 68.8% |
| SVM lineal | 63.9% | 50.0% | 0.798 | 68.4% |

XGBoost chosen as final model: best accuracy + lowest log-loss (probability quality matters for the prototype). Random Forest has better Macro-F1 (better on draws). SVM lineal barely identifies draws (recall 3%).

Trained models saved in `models/random_forest.pkl` and `models/xgboost.pkl`.

## Modeling Dataset Schema

**Identifiers (not model features):** `match_id`, `competition_name`, `season_name`, `home_team`, `away_team`

**Cumulative stats (home and away):** `goals`, `shots`, `shots_on_target`, `shots_in_box`, `xg`, `passes`, `complete_passes`, `pressures`, `duels_won`, `clearances`, `blocks`, `carries`, `yellow_cards`, `red_cards`, `attacks_third`

**Rolling window (last 15 min):** `xg_last15`, `shots_last15`, `pressures_last15`

**Derived features:** `score_diff`, `xg_diff`, `shots_diff`, `possession_home` (carry-based), `pass_completion_home`, `pass_completion_away`, `minutes_remaining`, `is_womens`, `players_diff` (red_cards_away − red_cards_home), `total_goals`, `xg_per_shot_home`, `xg_per_shot_away`, `goals_minus_xg_home`, `goals_minus_xg_away`

**Excluded as redundant:** `minute` (= 90 − minutes_remaining, r = −1.0), `period` (derivable from minutes_remaining threshold), `complete_passes_home/away` (r ≈ 0.98 with passes; recoverable as passes × pass_completion), `score_tied` (= score_diff == 0, zero independent information), `players_diff_x_time` (product of two present features; trees learn this interaction)

**Total model features: 48**

**Target:** `final_result` ∈ {home_win, draw, away_win}

## Key Decisions

- **Train/test split must be by `match_id`**, not random rows — all 90 rows of the same match share the same target, so random splitting leaks data. Prefer a temporal split by `season_name`.
- **Stoppage time** (period=2, minute > 90): goals clipped to minute 90 snapshot. Part of regulation.
- **Extra time / penalties** (periods 3-5): excluded from features, but `final_result` still reflects the actual outcome (including ET/penalties). No matches excluded.
- **`competition_name` / `season_name`**: metadata only, not model features. Competitions are treated as comparable and independent.
- **One row per minute** (not fixed checkpoints) — aggregate to checkpoints later if needed. Preserves granularity for rolling features and temporal accuracy curves.
- **`possession_home`**: derived from carry events (no direct possession column in StatsBomb). Falls back to 0.5 when no carries yet.
- **`is_womens`**: boolean flag — EDA showed different result distributions between men's and women's competitions.
- **Class imbalance**: home_win 45.2%, away_win 31.8%, draw 23.0% (across 3,464 matches). Use `class_weight='balanced'` or report macro-F1 alongside accuracy.

## Models

Three models trained and compared: **Random Forest**, **XGBoost** (selected as final), and **SVM lineal** (baseline comparison). LSTM was explicitly discarded due to the added complexity of design and validation without a clear benefit.

Hyperparameter tuning via `RandomizedSearchCV` (12 candidates each), scored by Macro-F1, with internal train/val split at the `match_id` level to avoid leakage. Evaluated at temporal checkpoints min 15, 30, 45, 60, 75, 90.

### Hyperparameter configuration (best)
- **Random Forest**: 500 trees, max_depth=8, min_samples_leaf=5, max_features='sqrt', class_weight='balanced'
- **XGBoost**: 300 estimators, max_depth=5, lr=0.03, subsample=0.7, colsample_bytree=0.9, min_child_weight=3, reg_lambda=3, reg_alpha=0.1, gamma=0.5
- **SVM lineal**: C=0.01 (LinearSVC + StandardScaler + CalibratedClassifierCV for probability output)