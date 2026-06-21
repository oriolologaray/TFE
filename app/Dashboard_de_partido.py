"""
Predictor de Resultados de Futbol en Vivo — Explorador de partido.

Ejecucion local:
    streamlit run app/app.py

Requiere app/data/ generado previamente:
    python app/prepare_app_data.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from data_loader import (
    CLASS_COLORS, CLASS_DISPLAY, CLASS_LABELS, FEATURE_COLS,
    load_features, load_metadata, load_models, load_timeline,
    predict_proba_named,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Predictor de Resultados de Futbol",
    page_icon=":soccer:",
    layout="wide",
)

st.title("Predictor de Resultados de Futbol en Vivo")

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
models    = load_models()
features_df = load_features()
metadata  = load_metadata()
timeline_df = load_timeline()

if not models:
    st.error("No se encontraron modelos en app/data/. Ejecuta `python app/prepare_app_data.py`.")
    st.stop()

available_models = list(models.keys())

# ---------------------------------------------------------------------------
# Game + model selectors — in the main window
# ---------------------------------------------------------------------------
sel_col1, sel_col2, sel_col3, sel_col4 = st.columns([2, 1, 3, 1.2])

with sel_col1:
    competitions = sorted(metadata["competition_name"].unique())
    competition  = st.selectbox("Competición", competitions, label_visibility="visible")

with sel_col2:
    seasons = sorted(
        metadata[metadata["competition_name"] == competition]["season_name"].unique(),
        reverse=True,
    )
    season = st.selectbox("Temporada", seasons)

with sel_col3:
    mask = (
        (metadata["competition_name"] == competition)
        & (metadata["season_name"] == season)
    )
    matches_meta = metadata[mask].copy()
    matches_meta["label"] = (
        matches_meta["home_team"] + " vs " + matches_meta["away_team"]
        + "  (" + matches_meta["final_score_home"].astype(int).astype(str)
        + "-"   + matches_meta["final_score_away"].astype(int).astype(str) + ")"
    )
    match_id = st.selectbox(
        "Partido",
        options=matches_meta["match_id"].tolist(),
        format_func=lambda x: matches_meta.set_index("match_id").loc[x, "label"],
    )

with sel_col4:
    model_name = st.selectbox("Modelo", available_models)

model = models[model_name]

st.divider()

# ---------------------------------------------------------------------------
# Match context
# ---------------------------------------------------------------------------
selected   = matches_meta[matches_meta["match_id"] == match_id].iloc[0]
home_team  = selected["home_team"]
away_team  = selected["away_team"]
final_result = selected["final_result"]
score_h    = int(selected["final_score_home"])
score_a    = int(selected["final_score_away"])

match_features = features_df[features_df["match_id"] == match_id].sort_values("minute")
match_events   = timeline_df[timeline_df["match_id"] == match_id]

# Match header
h_col, s_col, a_col = st.columns([5, 2, 5])
with h_col:
    st.markdown(f"<h2 style='margin-bottom:0'>{home_team}</h2>", unsafe_allow_html=True)
with s_col:
    st.markdown(
        f"<h2 style='text-align:center;margin-bottom:0'>{score_h} – {score_a}</h2>",
        unsafe_allow_html=True,
    )
with a_col:
    st.markdown(
        f"<h2 style='text-align:right;margin-bottom:0'>{away_team}</h2>",
        unsafe_allow_html=True,
    )
st.caption(
    f"Resultado final: **{CLASS_DISPLAY.get(final_result, final_result)}**"
    f"&nbsp;·&nbsp;{competition}&nbsp;·&nbsp;{season}"
)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_exp, tab_evo = st.tabs(["Explorador", "Evolución de probabilidades"])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — Explorador
# ═══════════════════════════════════════════════════════════════════════════
with tab_exp:

    minute = st.slider("Minuto", min_value=1, max_value=90, value=45)

    # ── Timeline ─────────────────────────────────────────────────────────
    goals  = match_events[match_events["shot_outcome"] == "Goal"]
    shots  = match_events[
        (match_events["event_type"] == "Shot")
        & (match_events["shot_outcome"] != "Goal")
    ]

    fig_tl = go.Figure()

    # Centre line
    fig_tl.add_shape(type="line", x0=1, x1=90, y0=0, y1=0,
                     line=dict(color="#cccccc", width=2))
    # Half-time
    fig_tl.add_vline(x=45, line_dash="dot", line_color="#bbbbbb", opacity=0.7,
                     annotation_text="MT", annotation_position="top left",
                     annotation_font=dict(color="#aaaaaa", size=11))

    def _scatter(x, y_val, symbol, size, color, opacity, name, hover):
        return go.Scatter(
            x=x, y=[y_val] * len(x), mode="markers",
            marker=dict(size=size, color=color, opacity=opacity, symbol=symbol),
            name=name, hovertemplate=hover + "<extra></extra>",
        )

    # Shots (faded triangles)
    home_shots = shots[shots["is_home"] == True]["minute"]
    away_shots = shots[shots["is_home"] == False]["minute"]
    if not home_shots.empty:
        fig_tl.add_trace(_scatter(home_shots, 0.4, "triangle-up",   8,
                                   CLASS_COLORS["home_win"], 0.35,
                                   f"Tiro — {home_team}", "min %{x}  Tiro local"))
    if not away_shots.empty:
        fig_tl.add_trace(_scatter(away_shots, -0.4, "triangle-down", 8,
                                   CLASS_COLORS["away_win"], 0.35,
                                   f"Tiro — {away_team}", "min %{x}  Tiro visitante"))

    # Goals (large stars + minute label)
    home_goals = goals[goals["is_home"] == True]
    away_goals = goals[goals["is_home"] == False]

    for df_g, y_val, pos, cls_key, team in [
        (home_goals,  0.75, "top center",    "home_win", home_team),
        (away_goals, -0.75, "bottom center", "away_win", away_team),
    ]:
        if not df_g.empty:
            fig_tl.add_trace(go.Scatter(
                x=df_g["minute"], y=[y_val] * len(df_g),
                mode="markers+text",
                marker=dict(size=20, color=CLASS_COLORS[cls_key], symbol="star"),
                text=[f"{m}'" for m in df_g["minute"]],
                textposition=pos,
                textfont=dict(size=10, color=CLASS_COLORS[cls_key]),
                name=f"Gol — {team}",
                hovertemplate=f"min %{{x}}  Gol {team}<extra></extra>",
            ))

    # Team labels on left
    for y_val, team, cls_key in [
        ( 0.75, home_team, "home_win"),
        (-0.75, away_team, "away_win"),
    ]:
        fig_tl.add_annotation(
            x=-0.5, y=y_val, text=f"<b>{team}</b>", showarrow=False,
            xanchor="right", font=dict(color=CLASS_COLORS[cls_key], size=12),
        )

    # Selected minute line
    fig_tl.add_vline(x=minute, line_color="crimson", line_width=2,
                     annotation_text=f"  min {minute}",
                     annotation_position="top right",
                     annotation_font=dict(color="crimson", size=12))

    fig_tl.update_layout(
        height=230,
        margin=dict(l=140, r=30, t=30, b=55),
        xaxis=dict(range=[0, 92], tickvals=[1, 15, 30, 45, 60, 75, 90],
                   showgrid=False, zeroline=False),
        yaxis=dict(range=[-1.2, 1.2], visible=False),
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="top", y=-0.22,
                    xanchor="center", x=0.5, font=dict(size=11)),
    )
    st.plotly_chart(fig_tl, use_container_width=True, config={"displayModeBar": False})

    # ── Event list ────────────────────────────────────────────────────────
    SHOT_OUTCOME_LABEL = {
        "Goal":          ("⚽", "Gol"),
        "Saved":         ("🧤", "Tiro parado"),
        "Saved To Post": ("🧤", "Tiro parado en el palo"),
        "Blocked":       ("🛡️", "Tiro bloqueado"),
        "Post":          ("🏁", "Tiro al palo"),
        "Off T":         ("↗️", "Tiro fuera"),
        "Wayward":       ("↗️", "Tiro desviado"),
    }

    key_events = match_events[match_events["event_type"] == "Shot"].copy()
    key_events["icon"]        = key_events["shot_outcome"].map(
        lambda o: SHOT_OUTCOME_LABEL.get(o, ("·", o))[0]
    )
    key_events["descripcion"] = key_events["shot_outcome"].map(
        lambda o: SHOT_OUTCOME_LABEL.get(o, ("·", o))[1]
    )
    key_events["equipo"] = key_events["team_name"]
    key_events = key_events[["minute", "icon", "descripcion", "equipo"]].sort_values("minute")
    key_events.columns = ["Minuto", "", "Evento", "Equipo"]

    visible = key_events[key_events["Minuto"] <= minute]
    past, future = visible, key_events[key_events["Minuto"] > minute]

    with st.expander(f"Eventos del partido — mostrando hasta el minuto {minute} "
                     f"({len(visible)} de {len(key_events)})", expanded=True):
        if visible.empty:
            st.caption("Sin tiros registrados hasta este minuto.")
        else:
            def _style_row(row):
                is_home = row["Equipo"] == home_team
                bg = "#e8f0fb" if is_home else "#fce8e8"
                return [f"background-color:{bg}"] * len(row)

            styled = (
                visible.style
                .apply(_style_row, axis=1)
                .set_properties(**{"font-size": "13px"})
                .hide(axis="index")
            )
            st.dataframe(styled, use_container_width=True, height=220)

    # ── Probability at selected minute ────────────────────────────────────
    st.markdown(f"#### Predicción en el minuto {minute}")

    row = match_features[match_features["minute"] == minute]
    if row.empty:
        st.warning(f"Sin datos para el minuto {minute}.")
    else:
        proba = predict_proba_named(model, row[FEATURE_COLS])
        predicted = max(proba, key=proba.get)

        # Stacked bar
        fig_pb = go.Figure()
        for cls in CLASS_LABELS:
            p = proba.get(cls, 0.0)
            fig_pb.add_trace(go.Bar(
                y=[""], x=[p], orientation="h",
                marker_color=CLASS_COLORS[cls],
                name=CLASS_DISPLAY[cls],
                text=f"{p:.0%}" if p >= 0.10 else "",
                textposition="inside", insidetextanchor="middle",
                textfont=dict(color="white", size=14, family="Arial Black"),
                hovertemplate=f"{CLASS_DISPLAY[cls]}: {p:.1%}<extra></extra>",
            ))
        fig_pb.update_layout(
            barmode="stack", height=68,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(visible=False, range=[0, 1]),
            yaxis=dict(visible=False),
            showlegend=False,
            plot_bgcolor="white", paper_bgcolor="white",
        )
        st.plotly_chart(fig_pb, use_container_width=True,
                        config={"displayModeBar": False})

        # Metric cards
        m1, m2, m3 = st.columns(3)
        for col, cls in zip([m1, m2, m3], CLASS_LABELS):
            p = proba.get(cls, 0.0)
            col.metric(
                label=CLASS_DISPLAY[cls],
                value=f"{p:.1%}",
                delta="Predicción" if cls == predicted else None,
                delta_color="off",
            )

# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — Evolucion
# ═══════════════════════════════════════════════════════════════════════════
with tab_evo:

    # Compute probabilities for all 90 minutes
    all_probas = [
        predict_proba_named(model, match_features[match_features["minute"] == m][FEATURE_COLS])
        for m in match_features["minute"]
    ]
    evo = pd.DataFrame(all_probas)
    evo["minute"] = match_features["minute"].values

    goal_minutes = match_events[match_events["shot_outcome"] == "Goal"]["minute"].tolist()

    fig_evo = go.Figure()
    for cls in CLASS_LABELS:
        if cls not in evo.columns:
            continue
        fig_evo.add_trace(go.Scatter(
            x=evo["minute"], y=evo[cls],
            name=CLASS_DISPLAY[cls],
            mode="lines",
            line=dict(color=CLASS_COLORS[cls], width=2.5),
            hovertemplate=f"{CLASS_DISPLAY[cls]}: %{{y:.1%}}<extra></extra>",
        ))

    for gm in goal_minutes:
        fig_evo.add_vline(x=gm, line_dash="dot", line_color="#aaaaaa", opacity=0.6)
    fig_evo.add_hline(y=1 / 3, line_dash="dash", line_color="#dddddd",
                      annotation_text="base", annotation_position="right",
                      annotation_font=dict(color="#bbbbbb", size=10))

    fig_evo.update_layout(
        height=420,
        margin=dict(l=10, r=20, t=20, b=20),
        xaxis=dict(title="Minuto", range=[1, 90],
                   tickvals=[1, 15, 30, 45, 60, 75, 90], showgrid=False),
        yaxis=dict(title="Probabilidad", tickformat=".0%",
                   range=[0, 1], showgrid=True, gridcolor="#f0f0f0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=12)),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    st.plotly_chart(fig_evo, use_container_width=True,
                    config={"displayModeBar": False})

    st.caption(
        "Las líneas verticales grises punteadas marcan los goles del partido. "
        "La línea horizontal indica la probabilidad de referencia (1/3 para tres clases equiprobables)."
    )
