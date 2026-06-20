"""
Football Match Result Predictor — Streamlit app.

Run locally:
    streamlit run app/app.py

Requires app/data/ to be populated first:
    python app/prepare_app_data.py
"""

from pathlib import Path

import joblib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"

FEATURE_COLS = [
    # Cumulative stats — home (17)
    "goals_home", "shots_home", "shots_on_target_home", "shots_in_box_home",
    "passes_home", "pressures_home", "duels_won_home", "clearances_home",
    "blocks_home", "carries_home", "yellow_cards_home", "red_cards_home",
    "attacks_third_home", "xg_home", "xg_last15_home", "shots_last15_home",
    "pressures_last15_home",
    # Cumulative stats — away (17)
    "goals_away", "shots_away", "shots_on_target_away", "shots_in_box_away",
    "passes_away", "pressures_away", "duels_won_away", "clearances_away",
    "blocks_away", "carries_away", "yellow_cards_away", "red_cards_away",
    "attacks_third_away", "xg_away", "xg_last15_away", "shots_last15_away",
    "pressures_last15_away",
    # Derived features (14)
    "score_diff", "xg_diff", "shots_diff",
    "possession_home", "pass_completion_home", "pass_completion_away",
    "minutes_remaining", "players_diff", "total_goals",
    "xg_per_shot_home", "xg_per_shot_away",
    "goals_minus_xg_home", "goals_minus_xg_away",
    "is_womens",
]

CLASS_LABELS = ["home_win", "draw", "away_win"]
CLASS_DISPLAY = {"home_win": "Victoria local", "draw": "Empate", "away_win": "Victoria visitante"}
CLASS_COLORS = {"home_win": "#1f77b4", "draw": "#ff7f0e", "away_win": "#d62728"}

# ---------------------------------------------------------------------------
# Cached data loading
# ---------------------------------------------------------------------------
@st.cache_resource
def load_models() -> dict:
    models = {}
    xgb_path = DATA_DIR / "xgboost.pkl"
    rf_path = DATA_DIR / "random_forest.pkl"
    if xgb_path.exists():
        models["XGBoost"] = joblib.load(xgb_path)
    if rf_path.exists():
        models["Random Forest"] = joblib.load(rf_path)
    return models


@st.cache_data
def load_features() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "features_test.parquet")


@st.cache_data
def load_metadata() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "match_metadata.parquet")


@st.cache_data
def load_timeline() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "timeline_events.parquet")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def predict_minute(model, features_df: pd.DataFrame, match_id: int, minute: int) -> dict:
    row = features_df[
        (features_df["match_id"] == match_id) & (features_df["minute"] == minute)
    ]
    if row.empty:
        return {}
    proba = model.predict_proba(row[FEATURE_COLS])[0]
    return dict(zip(model.classes_, proba))


def predict_all_minutes(model, features_df: pd.DataFrame, match_id: int) -> pd.DataFrame:
    match_rows = features_df[features_df["match_id"] == match_id].sort_values("minute")
    probas = model.predict_proba(match_rows[FEATURE_COLS])
    result = match_rows[["minute"]].copy().reset_index(drop=True)
    for i, cls in enumerate(model.classes_):
        result[cls] = probas[:, i]
    return result


def probability_bar_chart(proba: dict) -> go.Figure:
    labels = [CLASS_DISPLAY[c] for c in CLASS_LABELS if c in proba]
    values = [proba[c] for c in CLASS_LABELS if c in proba]
    colors = [CLASS_COLORS[c] for c in CLASS_LABELS if c in proba]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=colors,
        text=[f"{v:.1%}" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        xaxis=dict(range=[0, 1], tickformat=".0%"),
        yaxis=dict(autorange="reversed"),
        height=200, margin=dict(l=10, r=60, t=10, b=10),
        showlegend=False,
    )
    return fig


def evolution_chart(evolutions: dict[str, pd.DataFrame], goal_minutes: list[int]) -> go.Figure:
    fig = go.Figure()
    line_styles = {"XGBoost": "solid", "Random Forest": "dash"}
    for model_name, df in evolutions.items():
        for cls in CLASS_LABELS:
            if cls not in df.columns:
                continue
            fig.add_trace(go.Scatter(
                x=df["minute"], y=df[cls],
                name=f"{CLASS_DISPLAY[cls]} ({model_name})",
                mode="lines",
                line=dict(color=CLASS_COLORS[cls], dash=line_styles.get(model_name, "solid")),
                legendgroup=cls,
            ))
    for m in goal_minutes:
        fig.add_vline(x=m, line_dash="dot", line_color="gray", opacity=0.5)
    fig.add_hline(y=1/3, line_dash="dash", line_color="lightgray",
                  annotation_text="base", annotation_position="right")
    fig.update_layout(
        xaxis_title="Minuto", yaxis_title="Probabilidad",
        yaxis=dict(range=[0, 1], tickformat=".0%"),
        height=420, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def timeline_chart(events: pd.DataFrame, selected_minute: int) -> go.Figure:
    goal_events = events[events["shot_outcome"] == "Goal"]
    fig = go.Figure()
    for team, group in events.groupby("team_name"):
        fig.add_trace(go.Scatter(
            x=group["minute"], y=[team] * len(group),
            mode="markers",
            marker=dict(size=5, opacity=0.3),
            name=team, showlegend=True,
        ))
    if not goal_events.empty:
        for team, group in goal_events.groupby("team_name"):
            fig.add_trace(go.Scatter(
                x=group["minute"], y=[team] * len(group),
                mode="markers",
                marker=dict(size=14, symbol="star", opacity=1.0),
                name=f"Gol — {team}", showlegend=True,
            ))
    fig.add_vline(x=selected_minute, line_color="red", line_width=2,
                  annotation_text=f"min {selected_minute}", annotation_position="top")
    fig.update_layout(
        xaxis=dict(range=[0, 91], title="Minuto"),
        height=180, margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title="",
    )
    return fig


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Predictor de Resultados de Fútbol",
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ Predictor de Resultados de Fútbol")
st.caption("TFM — UNIR Máster en Inteligencia Artificial")

models = load_models()
features_df = load_features()
metadata = load_metadata()
timeline_df = load_timeline()

if not models:
    st.error("No se han encontrado modelos en app/data/. Ejecuta `python app/prepare_app_data.py`.")
    st.stop()

available_models = list(models.keys())

# ---------------------------------------------------------------------------
# Sidebar — game selection (shared across all tabs)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Selección de partido")
    competitions = sorted(metadata["competition_name"].unique())
    competition = st.selectbox("Competición", competitions)

    seasons = sorted(
        metadata[metadata["competition_name"] == competition]["season_name"].unique(),
        reverse=True,
    )
    season = st.selectbox("Temporada", seasons)

    mask = (metadata["competition_name"] == competition) & (metadata["season_name"] == season)
    matches_meta = metadata[mask].copy()
    matches_meta["label"] = (
        matches_meta["home_team"] + " vs " + matches_meta["away_team"]
        + "  (" + matches_meta["final_score_home"].astype(str)
        + "–" + matches_meta["final_score_away"].astype(str) + ")"
    )
    match_labels = matches_meta.set_index("match_id")["label"].to_dict()
    match_id = st.selectbox("Partido", options=list(match_labels.keys()),
                            format_func=lambda x: match_labels[x])

selected_meta = matches_meta[matches_meta["match_id"] == match_id].iloc[0]
home_team = selected_meta["home_team"]
away_team = selected_meta["away_team"]
final_result = selected_meta["final_result"]

st.subheader(f"{home_team}  vs  {away_team}")
st.caption(
    f"Resultado final: **{CLASS_DISPLAY.get(final_result, final_result)}**  "
    f"({selected_meta['final_score_home']}–{selected_meta['final_score_away']})"
)

match_events = timeline_df[timeline_df["match_id"] == match_id]
goal_minutes = match_events[match_events["shot_outcome"] == "Goal"]["minute"].tolist()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🔍 Explorador de partido", "📈 Evolución", "🎮 Simulador"])

# ── Tab 1: Explorer ─────────────────────────────────────────────────────────
with tab1:
    col_ctrl, col_main = st.columns([1, 3])
    with col_ctrl:
        model_name_1 = st.radio("Modelo", available_models, key="model_tab1")
        minute = st.slider("Minuto", min_value=1, max_value=90, value=45, key="minute_tab1")

    with col_main:
        st.plotly_chart(timeline_chart(match_events, minute),
                        use_container_width=True, config={"displayModeBar": False})

        proba = predict_minute(models[model_name_1], features_df, match_id, minute)
        if proba:
            st.plotly_chart(probability_bar_chart(proba),
                            use_container_width=True, config={"displayModeBar": False})
        else:
            st.warning(f"No hay datos para el minuto {minute} en este partido.")

# ── Tab 2: Evolution ────────────────────────────────────────────────────────
with tab2:
    selected_models_2 = st.multiselect(
        "Modelos a comparar", available_models, default=available_models, key="models_tab2"
    )
    if selected_models_2:
        evolutions = {
            name: predict_all_minutes(models[name], features_df, match_id)
            for name in selected_models_2
        }
        st.plotly_chart(evolution_chart(evolutions, goal_minutes),
                        use_container_width=True)
        if len(available_models) == 1 and "Random Forest" not in available_models:
            st.info(
                "El modelo Random Forest no está disponible en este entorno. "
                "Consulta app/prepare_app_data.py para activarlo localmente."
            )
    else:
        st.info("Selecciona al menos un modelo.")

# ── Tab 3: Simulator ─────────────────────────────────────────────────────────
with tab3:
    st.markdown(
        "Ajusta el estado del partido manualmente. Los valores restantes se inicializan "
        "con la mediana del conjunto de test como estado neutro."
    )

    medians = features_df[FEATURE_COLS].median()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Marcador y tiempo")
        goals_home = st.number_input("Goles local", 0, 10, 0, key="sim_gh")
        goals_away = st.number_input("Goles visitante", 0, 10, 0, key="sim_ga")
        sim_minute = st.slider("Minuto actual", 1, 90, 45, key="sim_min")
        is_womens = st.toggle("Competición femenina", value=False, key="sim_fem")

    with col2:
        st.subheader("Producción ofensiva")
        shots_home = st.slider("Tiros local", 0, 30, int(medians.get("shots_home", 5)), key="sim_sh")
        shots_away = st.slider("Tiros visitante", 0, 30, int(medians.get("shots_away", 5)), key="sim_sa")
        xg_home = st.slider("xG local", 0.0, 5.0, float(round(medians.get("xg_home", 0.5), 1)),
                             step=0.1, key="sim_xgh")
        xg_away = st.slider("xG visitante", 0.0, 5.0, float(round(medians.get("xg_away", 0.5), 1)),
                             step=0.1, key="sim_xga")

    with col3:
        st.subheader("Control del juego")
        possession = st.slider("Posesión local (%)", 0, 100, 50, key="sim_poss") / 100
        players_diff = st.slider("Diferencial de jugadores (local − visitante)", -3, 3, 0,
                                 key="sim_pd")

    # Build feature vector from medians + user overrides
    sim_vector = medians.copy()
    sim_vector["goals_home"] = goals_home
    sim_vector["goals_away"] = goals_away
    sim_vector["shots_home"] = shots_home
    sim_vector["shots_away"] = shots_away
    sim_vector["xg_home"] = xg_home
    sim_vector["xg_away"] = xg_away
    sim_vector["possession_home"] = possession
    sim_vector["players_diff"] = players_diff
    sim_vector["minutes_remaining"] = 90 - sim_minute
    sim_vector["is_womens"] = int(is_womens)
    # Derived features
    sim_vector["score_diff"] = goals_home - goals_away
    sim_vector["total_goals"] = goals_home + goals_away
    sim_vector["xg_diff"] = xg_home - xg_away
    sim_vector["shots_diff"] = shots_home - shots_away
    sim_vector["goals_minus_xg_home"] = goals_home - xg_home
    sim_vector["goals_minus_xg_away"] = goals_away - xg_away
    sim_vector["xg_per_shot_home"] = (xg_home / shots_home) if shots_home > 0 else 0.0
    sim_vector["xg_per_shot_away"] = (xg_away / shots_away) if shots_away > 0 else 0.0

    sim_df = pd.DataFrame([sim_vector[FEATURE_COLS]])

    st.divider()
    st.subheader("Predicción")
    sim_cols = st.columns(len(available_models))
    for col, model_name in zip(sim_cols, available_models):
        with col:
            st.markdown(f"**{model_name}**")
            proba_sim = dict(zip(
                models[model_name].classes_,
                models[model_name].predict_proba(sim_df)[0],
            ))
            st.plotly_chart(
                probability_bar_chart(proba_sim),
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"sim_chart_{model_name}",
            )
