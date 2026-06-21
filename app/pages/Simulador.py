"""Simulador de estado de partido — Tab independiente del Explorador."""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import (
    CLASS_COLORS, CLASS_DISPLAY, CLASS_LABELS, FEATURE_COLS,
    load_features, load_models, predict_proba_named,
)

st.set_page_config(page_title="Simulador", page_icon="game_die", layout="wide")

models = load_models()
features_df = load_features()

if not models:
    st.error("No se encontraron modelos. Ejecuta `python app/prepare_app_data.py`.")
    st.stop()

available_models = list(models.keys())
medians = features_df[FEATURE_COLS].median()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Simulador de partido")
st.markdown(
    "Ajusta el estado del partido con los controles. El resto de variables se inicializan "
    "con la mediana del conjunto de test como estado neutro. Ambos modelos disponibles "
    "se muestran en paralelo."
)
st.divider()

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Marcador y tiempo")
    goals_home = st.number_input("Goles local", 0, 10, 0)
    goals_away = st.number_input("Goles visitante", 0, 10, 0)
    sim_minute = st.slider("Minuto actual", 1, 90, 45)
    is_womens = st.toggle("Competicion femenina", value=False)
    players_diff = st.slider("Diferencial de jugadores (local - visitante)", -3, 3, 0,
                             help="Positivo si el local tiene mas jugadores en campo (expulsiones del visitante).")

with col2:
    st.subheader("Produccion ofensiva")
    shots_home = st.slider("Tiros local", 0, 30, int(medians.get("shots_home", 5)))
    shots_away = st.slider("Tiros visitante", 0, 30, int(medians.get("shots_away", 5)))
    xg_home = st.slider("xG local", 0.0, 5.0,
                         float(round(medians.get("xg_home", 0.5), 1)), step=0.1)
    xg_away = st.slider("xG visitante", 0.0, 5.0,
                         float(round(medians.get("xg_away", 0.5), 1)), step=0.1)

with col3:
    st.subheader("Control del juego")
    possession = st.slider("Posesion local (%)", 0, 100, 50) / 100
    pass_completion_home = st.slider(
        "Precision de pase local (%)", 0, 100,
        int(round(medians.get("pass_completion_home", 0.78) * 100)),
    ) / 100
    pass_completion_away = st.slider(
        "Precision de pase visitante (%)", 0, 100,
        int(round(medians.get("pass_completion_away", 0.74) * 100)),
    ) / 100

# ---------------------------------------------------------------------------
# Build feature vector
# ---------------------------------------------------------------------------
sim_vector = medians.copy()

sim_vector["goals_home"] = goals_home
sim_vector["goals_away"] = goals_away
sim_vector["shots_home"] = shots_home
sim_vector["shots_away"] = shots_away
sim_vector["xg_home"] = xg_home
sim_vector["xg_away"] = xg_away
sim_vector["possession_home"] = possession
sim_vector["pass_completion_home"] = pass_completion_home
sim_vector["pass_completion_away"] = pass_completion_away
sim_vector["players_diff"] = players_diff
sim_vector["minutes_remaining"] = 90 - sim_minute
sim_vector["is_womens"] = int(is_womens)

# Derived
sim_vector["score_diff"] = goals_home - goals_away
sim_vector["total_goals"] = goals_home + goals_away
sim_vector["xg_diff"] = xg_home - xg_away
sim_vector["shots_diff"] = shots_home - shots_away
sim_vector["goals_minus_xg_home"] = goals_home - xg_home
sim_vector["goals_minus_xg_away"] = goals_away - xg_away
sim_vector["xg_per_shot_home"] = (xg_home / shots_home) if shots_home > 0 else 0.0
sim_vector["xg_per_shot_away"] = (xg_away / shots_away) if shots_away > 0 else 0.0

sim_df = pd.DataFrame([sim_vector[FEATURE_COLS]])

# ---------------------------------------------------------------------------
# Prediction display
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Prediccion")

model_cols = st.columns(len(available_models))
for col, model_name in zip(model_cols, available_models):
    with col:
        mdl = models[model_name]
        proba = predict_proba_named(mdl, sim_df)
        predicted = max(proba, key=proba.get)

        st.markdown(f"**{model_name}**")

        # Stacked bar
        fig = go.Figure()
        for cls in CLASS_LABELS:
            p = proba.get(cls, 0)
            fig.add_trace(go.Bar(
                y=[""], x=[p], orientation="h",
                marker_color=CLASS_COLORS[cls],
                name=CLASS_DISPLAY[cls],
                text=f"{p:.0%}" if p >= 0.12 else "",
                textposition="inside", insidetextanchor="middle",
                textfont=dict(color="white", size=13),
                hovertemplate=f"{CLASS_DISPLAY[cls]}: {p:.1%}<extra></extra>",
            ))
        fig.update_layout(
            barmode="stack", height=70,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(visible=False, range=[0, 1]),
            yaxis=dict(visible=False),
            showlegend=False,
            plot_bgcolor="white", paper_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False}, key=f"sim_{model_name}")

        m1, m2, m3 = st.columns(3)
        for mc, cls in zip([m1, m2, m3], CLASS_LABELS):
            p = proba.get(cls, 0)
            mc.metric(
                label=CLASS_DISPLAY[cls],
                value=f"{p:.1%}",
                delta="Prediccion" if cls == predicted else None,
                delta_color="off",
            )
