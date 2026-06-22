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

## Deployment — Streamlit Web App

**Framework:** Streamlit. Performance is not a concern with proper caching: models loaded once via `st.cache_resource`; parquet files loaded via `st.cache_data`.

**Deployment target:** Streamlit Community Cloud (free, direct GitHub integration). GitHub Pages cannot host Streamlit — it serves static files only.

**File sizes (local):**
- `datasets/statsbomb_events.csv` — 1.7 GB (gitignored)
- `datasets/match_minute_features.csv` — 121 MB (gitignored)
- `models/random_forest.pkl` — 986 MB (gitignored; too large for git even compressed)
- `models/xgboost.pkl` — 3.6 MB

**Deployment data pipeline:** Run `python app/prepare_app_data.py` once locally to generate small committed files in `app/data/`:
- `features_test.parquet` — test-set rows only (~62k rows, ~5 MB compressed)
- `match_metadata.parquet` — one row per test match (~100 KB)
- `timeline_events.parquet` — test-set events, 5 key columns only (~5–15 MB)
- `xgboost.pkl` — copied from `models/` (3.6 MB)
- `random_forest.pkl` — gitignored in `app/data/`; RF is local-only unless Git LFS is set up

**RF on cloud:** graceful fallback in `app.py` — if `random_forest.pkl` is absent, the model selector and Tab 2 comparison show XGBoost only. XGBoost is the final model so this is acceptable for the cloud demo.

**File structure:**
```
app/
├── app.py                # entry point: st.navigation([Dashboard, Simulador])
├── data_loader.py        # shared cached loading (models, parquet files, constants)
├── pages/
│   ├── Dashboard_de_partido.py   # game selector + timeline + prediction + evolution
│   └── Simulador.py              # match state sliders → real-time prediction
├── prepare_app_data.py   # run once locally to generate app/data/
└── data/                 # committed to git (small files only)
    ├── features_test.parquet
    ├── match_metadata.parquet
    ├── timeline_events.parquet
    └── xgboost.pkl
```

**Local development:** `streamlit run app/app.py` — auto-reloads on file save. No push needed.

**Game scope:** only test-set matches (seasons 2020–2025). Game selector in sidebar cascades Competition → Season → Match.

### Page 1 — Explorador de partido (`app.py`)
Timeline + current minute prediction + full-match evolution chart on a single page. Sidebar: game selector + model radio.

Layout:
- **Header**: home team | score | away team + result caption
- **Timeline** (full width): single horizontal axis, home events above (blue), away below (red). Goals as large stars with minute label. Shots as small triangles. Half-time dashed line. Selected minute as red vertical line.
- **Minute slider** (full width, drives both timeline marker and prediction panel)
- **Two columns**:
  - Left: stacked bar chart (3 colors) + three metric cards with exact probabilities
  - Right: line chart of P(home_win), P(draw), P(away_win) across all 90 minutes; goal events as dotted vertical lines; selected minute as dashed red line

### Page 2 — Simulador (`pages/Simulador.py`)
Match state sliders → real-time probability prediction. Completely separate from the Explorador.

Controls (3 columns): score + time | offensive production | ball control.
Feature vector built from user inputs; all other features set to dataset medians as neutral baseline.
Both available models shown side by side. Each shows the same stacked bar + metric card layout as the Explorador.

### Tab 1 — Explorador de partido
- Sidebar: game selector, model selector (XGBoost / Random Forest), minute slider (1–90)
- Timeline: Plotly scatter (x=minute, y=event_type, colour=team); goals marked; vertical line at selected minute
- Probability panel: horizontal bar chart for P(home_win), P(draw), P(away_win) at the selected minute
- Data source: `match_minute_features.csv` (pre-computed features) + `statsbomb_events.csv` (timeline events)

### Tab 2 — Evolución de probabilidades
- Same game selection (shared via `st.session_state`)
- Plotly line chart: x=minute (1–90), three lines per model (home/draw/away), model toggle overlay (XGBoost vs RF)
- Goal events marked as vertical lines; horizontal dashed reference at 0.33 (random baseline per class)
- Data source: all 90 rows for the selected match in `match_minute_features.csv`

### Tab 3 — Simulador personalizado (Option A: match state sliders)
The model takes 48 aggregated features, not raw events. The simulator exposes the most predictive features as controls; the rest are set to dataset medians as neutral defaults.

**User controls:**
- Goals (home / away) → computes `score_diff`, `total_goals`, `goals_minus_xg`
- Shots and shots on target (home / away) → computes `shots_diff`
- xG (home / away) → computes `xg_diff`, `xg_per_shot`
- Possession % (home) → maps to `possession_home`
- Minute → maps to `minutes_remaining`
- Players diff (red cards)
- Competition type toggle (men's / women's) → `is_womens`

The app calls `features.build_feature_vector()` which assembles the 48-feature vector and calls `model.predict_proba()` in real time. Both models shown side by side.

### Option B — Event builder (future work)
Allow users to add individual events (Goal, Shot, Pass, Pressure…) at a chosen minute for a chosen team, and have the app recompute cumulative features on the fly. Requires replicating the full feature engineering pipeline inside the app. Feasible but ~3–4× more implementation work than Option A; documented here as a natural extension for a production version.