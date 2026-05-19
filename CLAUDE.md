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
| 4 — Modeling | `notebooks/modeling.ipynb` | In progress (RF done: 66.4% overall, 71% at min 60) |
| 5 — Evaluation & Deployment | — | Pending |

## Modeling Dataset Schema

**Identifiers (not model features):** `match_id`, `competition_name`, `season_name`, `home_team`, `away_team`

**Cumulative stats (home and away):** `goals`, `shots`, `shots_on_target`, `shots_in_box`, `xg`, `passes`, `complete_passes`, `pressures`, `duels_won`, `clearances`, `blocks`, `carries`, `yellow_cards`, `red_cards`, `attacks_third`

**Rolling window (last 15 min):** `xg_last15`, `shots_last15`, `pressures_last15`

**Derived features:** `score_diff`, `xg_diff`, `shots_diff`, `possession_home` (carry-based), `pass_completion_home`, `pass_completion_away`, `minutes_remaining`, `period`, `score_tied`, `is_womens`, `players_diff` (red_cards_away − red_cards_home), `players_diff_x_time` (players_diff × minutes_remaining), `total_goals`, `xg_per_shot_home`, `xg_per_shot_away`, `goals_minus_xg_home`, `goals_minus_xg_away`

**Total model features: 54**

**Target:** `final_result` ∈ {home_win, draw, away_win}

## Key Decisions

- **Train/test split must be by `match_id`**, not random rows — all 90 rows of the same match share the same target, so random splitting leaks data. Prefer a temporal split by `season_name`.
- **Stoppage time** (period=2, minute > 90): goals clipped to minute 90 snapshot. Part of regulation.
- **Extra time / penalties** (periods 3-5): excluded from features, but `final_result` still reflects the actual outcome (including ET/penalties). No matches excluded.
- **`competition_name` / `season_name`**: metadata only, not model features. Competitions are treated as comparable and independent.
- **One row per minute** (not fixed checkpoints) — aggregate to checkpoints later if needed. Preserves granularity for rolling features and temporal accuracy curves.
- **`possession_home`**: derived from carry events (no direct possession column in StatsBomb). Falls back to 0.5 when no carries yet.
- **`is_womens`**: boolean flag — EDA showed different result distributions between men's and women's competitions.
- **Class imbalance**: home_win ~47%, draw ~27%, away_win ~26%. Use `class_weight='balanced'` or report macro-F1 alongside accuracy.

## Planned Models

Random Forest, XGBoost (primary), and optionally an LSTM for the sequential formulation. Hyperparameter tuning via grid search / random search. Evaluate at multiple temporal checkpoints (min 15, 30, 45, 60, 75, 90) to understand how confidence improves during the match.