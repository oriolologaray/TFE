"""
Run once locally before deploying to Streamlit Cloud.
Generates small deployment-ready files in app/data/ from the large local datasets.

Usage:
    python app/prepare_app_data.py
"""

import re
import shutil
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).parent.parent
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

TEST_YEAR_MIN = 2020


def _season_start_year(season_name: str) -> int:
    """Extract the first 4-digit year from a season string (e.g. '2022/2023' -> 2022)."""
    years = re.findall(r"\d{4}", str(season_name))
    return int(years[0]) if years else 0


# ---------------------------------------------------------------------------
# 1. Features — test-set rows only
# ---------------------------------------------------------------------------
print("Loading match_minute_features.csv ...")
features = pd.read_csv(ROOT / "datasets" / "match_minute_features.csv", low_memory=False)

test_mask = features["season_name"].map(_season_start_year) >= TEST_YEAR_MIN
features_test = features[test_mask].copy()
print(f"  Test-set rows: {len(features_test):,} / {len(features):,}")

out = DATA_DIR / "features_test.parquet"
features_test.to_parquet(out, index=False, compression="zstd")
print(f"  Saved {out} ({out.stat().st_size / 1e6:.1f} MB)")

# ---------------------------------------------------------------------------
# 2. Match metadata — one row per test-set match
# ---------------------------------------------------------------------------
meta_cols = [
    "match_id", "competition_name", "season_name",
    "home_team", "away_team", "final_result",
]
meta = (
    features_test[meta_cols]
    .drop_duplicates("match_id")
    .sort_values(["competition_name", "season_name", "match_id"])
    .reset_index(drop=True)
)

# final_score_home/away are not columns in the features CSV;
# derive them from goals at the last recorded minute of each match.
final_scores = (
    features_test.sort_values("minute")
    .groupby("match_id")[["goals_home", "goals_away"]]
    .last()
    .rename(columns={"goals_home": "final_score_home", "goals_away": "final_score_away"})
    .reset_index()
)
meta = meta.merge(final_scores, on="match_id", how="left")
out = DATA_DIR / "match_metadata.parquet"
meta.to_parquet(out, index=False, compression="zstd")
print(f"  Saved {out} ({out.stat().st_size / 1e6:.1f} MB)")

test_match_ids = set(meta["match_id"])

# ---------------------------------------------------------------------------
# 3. Timeline events — test-set matches, key columns only
# ---------------------------------------------------------------------------
TIMELINE_COLS = ["match_id", "minute", "event_type", "team_name", "is_home", "shot_outcome"]

print("Loading statsbomb_events.csv (this takes a while) ...")
events = pd.read_csv(
    ROOT / "datasets" / "statsbomb_events.csv",
    usecols=TIMELINE_COLS,
)
events_test = events[events["match_id"].isin(test_match_ids)].copy()
print(f"  Test-set events: {len(events_test):,} / {len(events):,}")

out = DATA_DIR / "timeline_events.parquet"
events_test.to_parquet(out, index=False, compression="zstd")
print(f"  Saved {out} ({out.stat().st_size / 1e6:.1f} MB)")

del events, events_test  # free memory before loading models

# ---------------------------------------------------------------------------
# 4. XGBoost model — already small, just copy
# ---------------------------------------------------------------------------
src = ROOT / "models" / "xgboost.pkl"
dst = DATA_DIR / "xgboost.pkl"
shutil.copy2(src, dst)
print(f"  Copied xgboost.pkl -> {dst} ({dst.stat().st_size / 1e6:.1f} MB)")

# ---------------------------------------------------------------------------
# 5. Random Forest — try maximum compression; warn if still too large for git
# ---------------------------------------------------------------------------
src = ROOT / "models" / "random_forest.pkl"
dst = DATA_DIR / "random_forest.pkl"

print("Compressing random_forest.pkl (this may take a few minutes) ...")
rf_model = joblib.load(src)
joblib.dump(rf_model, dst, compress=("zlib", 9))
size_mb = dst.stat().st_size / 1e6
print(f"  Compressed RF: {size_mb:.1f} MB  (original: {src.stat().st_size / 1e6:.1f} MB)")

if size_mb > 100:
    print(
        f"\n  WARNING: random_forest.pkl is {size_mb:.0f} MB - too large for a standard git commit.\n"
        "  Options:\n"
        "    a) Use Git LFS:  git lfs track 'app/data/random_forest.pkl'\n"
        "    b) Upload as a GitHub Release asset and fetch at app startup.\n"
        "    c) Cloud deployment will use XGBoost only (graceful fallback in app.py).\n"
    )
else:
    print("  RF model fits within the 100 MB git limit — safe to commit.")

print("\nDone. Files in app/data/:")
for f in sorted(DATA_DIR.iterdir()):
    print(f"  {f.name:40s} {f.stat().st_size / 1e6:6.1f} MB")
