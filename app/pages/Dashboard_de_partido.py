"""
Predictor de Resultados de Futbol en Vivo — Explorador de partido.

Ejecucion local:
    streamlit run app/Dashboard_de_partido.py

Requiere app/data/ generado previamente:
    python app/prepare_app_data.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
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

# Match context (compact — la cabecera dinámica va dentro de la pestaña)
st.markdown(
    f"<div style='margin:4px 0 18px 0'>"
    f"<span style='font-size:2.4em;font-weight:800;color:#1a1a1a;line-height:1.1'>"
    f"{home_team} vs {away_team}</span><br>"
    f"<span style='font-size:1.05em;color:#666'>"
    f"{competition}&nbsp;·&nbsp;{season}&nbsp;·&nbsp;"
    f"Resultado final: <b style='color:#444'>{CLASS_DISPLAY.get(final_result, final_result)}</b>"
    f"&nbsp;({score_h}–{score_a})</span></div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_exp, tab_evo = st.tabs(["Explorador", "Evolución de probabilidades"])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — Explorador
# ═══════════════════════════════════════════════════════════════════════════
with tab_exp:

    # ── Slider ───────────────────────────────────────────────────────────
    minute = st.slider("Minuto", min_value=1, max_value=90, value=45, format="%d'")

    # Score al minuto seleccionado
    row_at_minute = match_features[match_features["minute"] == minute]
    if not row_at_minute.empty:
        score_h_now = int(row_at_minute.iloc[0]["goals_home"])
        score_a_now = int(row_at_minute.iloc[0]["goals_away"])
    else:
        score_h_now, score_a_now = 0, 0

    home_color = CLASS_COLORS["home_win"]
    away_color = CLASS_COLORS["away_win"]

    # ── Cabecera + probabilidades (lado a lado) ──────────────────────────
    left_col, right_col = st.columns([2, 3])

    with left_col:
        st.markdown(
            f"<div style='margin-top:10px'>"
            f"<span style='font-size:1.3em;font-weight:700;color:{home_color}'>{home_team}</span>"
            f"&nbsp;<span style='font-size:1.9em;font-weight:900'>&nbsp;{score_h_now}–{score_a_now}&nbsp;</span>"
            f"<span style='font-size:1.3em;font-weight:700;color:{away_color}'>{away_team}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"Marcador al minuto {minute}'")

    with right_col:
        if not row_at_minute.empty:
            proba = predict_proba_named(model, row_at_minute[FEATURE_COLS])
            predicted = max(proba, key=proba.get)

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
                barmode="stack", height=52,
                margin=dict(l=0, r=0, t=4, b=0),
                xaxis=dict(visible=False, range=[0, 1]),
                yaxis=dict(visible=False),
                showlegend=False,
                plot_bgcolor="white", paper_bgcolor="white",
            )
            st.plotly_chart(fig_pb, use_container_width=True, config={"displayModeBar": False})

            m1, m2, m3 = st.columns(3)
            for col, cls in zip([m1, m2, m3], CLASS_LABELS):
                p = proba.get(cls, 0.0)
                col.markdown(
                    f"<p style='color:#888;font-size:0.85em;margin:0 0 2px 0;font-weight:500'>"
                    f"{CLASS_DISPLAY[cls]}</p>"
                    f"<p style='font-size:1.8em;font-weight:900;margin:0;line-height:1.1'>"
                    f"{p:.1%}</p>",
                    unsafe_allow_html=True,
                )
        else:
            st.warning(f"Sin datos para el minuto {minute}.")

    st.divider()

    # ── Mappings ─────────────────────────────────────────────────────────
    SHOT_OUTCOME_LABEL = {
        "Goal":          ("⚽", "Gol"),
        "Saved":         ("🧤", "Tiro parado"),
        "Saved To Post": ("🧤", "Tiro parado en el palo"),
        "Blocked":       ("🛡️", "Tiro bloqueado"),
        "Post":          ("🏁", "Tiro al palo"),
        "Off T":         ("↗️", "Tiro fuera"),
        "Wayward":       ("↗️", "Tiro desviado"),
    }
    SHOT_MARKER = {
        "Goal":          ("circle",       "Gol"),
        "Saved":         ("diamond-open", "Parada"),
        "Saved To Post": ("diamond-open", "Parada"),
        "Blocked":       ("triangle-up",  "Tiro"),
        "Post":          ("triangle-up",  "Tiro"),
        "Off T":         ("triangle-up",  "Tiro"),
        "Wayward":       ("triangle-up",  "Tiro"),
    }

    # ── Timeline data ─────────────────────────────────────────────────────
    goals = match_events[match_events["shot_outcome"] == "Goal"].sort_values("minute").reset_index(drop=True)
    shots = match_events[
        (match_events["event_type"] == "Shot")
        & (match_events["shot_outcome"] != "Goal")
    ]

    _h, _a = 0, 0
    _score_only, _score_labels = [], []
    for _, _g in goals.iterrows():
        if _g["is_home"]:
            _h += 1
        else:
            _a += 1
        _score_only.append(f"{_h}-{_a}")
        _score_labels.append(f"{int(_g['minute'])}'  {_h}–{_a}")
    if not goals.empty:
        goals = goals.copy()
        goals["score_only"]  = _score_only
        goals["score_label"] = _score_labels

    home_shots_df = shots[shots["is_home"] == True].copy()
    away_shots_df = shots[shots["is_home"] == False].copy()
    home_goals_df = goals[goals["is_home"] == True]
    away_goals_df = goals[goals["is_home"] == False]

    # ── LÍNEA DE TIEMPO ──────────────────────────────────────────────────
    st.markdown(
        f"<div style='font-size:0.82em;color:#555;padding:6px 0 4px 0;display:flex;"
        f"gap:16px;align-items:center;flex-wrap:wrap'>"
        f"<b style='color:#222;letter-spacing:0.05em'>EVENTOS</b>"
        f"<span>&#9679;&nbsp;Gol</span>"
        f"<span>&#9650;&nbsp;Tiro</span>"
        f"<span>&#9826;&nbsp;Parada</span>"
        f"<span style='margin-left:6px;border-left:1px solid #ddd;padding-left:14px'>"
        f"<span style='color:{home_color}'>&#9632;</span>&nbsp;{home_team} (local)</span>"
        f"<span><span style='color:{away_color}'>&#9632;</span>&nbsp;{away_team} (visitante)</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    fig_tl = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.0,
    )

    # Fondos de carril (contiguos): local arriba (azul), visitante abajo (rojo)
    fig_tl.add_shape(
        type="rect", xref="x domain", yref="y domain",
        x0=0, x1=1, y0=0, y1=1, fillcolor=home_color, opacity=0.13,
        layer="below", line_width=0, row=1, col=1,
    )
    fig_tl.add_shape(
        type="rect", xref="x2 domain", yref="y2 domain",
        x0=0, x1=1, y0=0, y1=1, fillcolor=away_color, opacity=0.13,
        layer="below", line_width=0, row=2, col=1,
    )

    # Etiquetas de equipo dentro del carril
    fig_tl.add_annotation(
        x=0, y=0.9, xref="x domain", yref="y", xanchor="left",
        text=f"<b>{home_team}</b> <span style='color:#999'>(local)</span>",
        showarrow=False, font=dict(color=home_color, size=13),
    )
    fig_tl.add_annotation(
        x=0, y=0.06, xref="x2 domain", yref="y2", xanchor="left",
        text=f"<b>{away_team}</b> <span style='color:#999'>(visitante)</span>",
        showarrow=False, font=dict(color=away_color, size=13),
    )

    # Línea de descanso (MT) y de minuto (naranja). Se dibujan como trazas para
    # que queden por encima del fondo de color de cada carril.
    for rn in (1, 2):
        fig_tl.add_trace(go.Scatter(
            x=[45, 45], y=[0, 1], mode="lines",
            line=dict(color="#bbbbbb", width=1, dash="dot"),
            opacity=0.7, hoverinfo="skip", showlegend=False,
        ), row=rn, col=1)
        fig_tl.add_trace(go.Scatter(
            x=[minute, minute], y=[0, 1], mode="lines",
            line=dict(color="#f0a500", width=2.5),
            hoverinfo="skip", showlegend=False,
        ), row=rn, col=1)
    fig_tl.add_annotation(
        x=45, y=1.0, xref="x", yref="paper", yanchor="bottom",
        text="MT", showarrow=False,
        font=dict(color="#888", size=10),
        bgcolor="white", bordercolor="#ccc", borderwidth=1, borderpad=3,
    )
    fig_tl.add_annotation(
        x=minute, y=1.0, xref="x", yref="paper", yanchor="bottom",
        text=f"<b>{minute}'</b>", showarrow=False,
        bgcolor="#f0a500", font=dict(color="white", size=11),
        borderpad=4,
    )

    def _add_events(df_shots_t, df_goals_t, row_n, t_color, y_rows):
        """Marcadores con etiquetas multilínea, escalonados para no solaparse."""
        evts = []
        if not df_goals_t.empty:
            for _, r in df_goals_t.iterrows():
                sc = str(r.get("score_only", "")).replace("-", "–")
                evts.append({
                    "minute": r["minute"], "symbol": "circle", "size": 16,
                    "label": f"<b>Gol</b><br>{int(r['minute'])}'<br><b>{sc}</b>",
                    "hover": "Gol",
                })
        if not df_shots_t.empty:
            for _, r in df_shots_t.iterrows():
                sym, lbl = SHOT_MARKER.get(r["shot_outcome"], ("triangle-up", "Tiro"))
                evts.append({
                    "minute": r["minute"], "symbol": sym, "size": 12,
                    "label": f"<b>{lbl}</b><br>{int(r['minute'])}'",
                    "hover": lbl,
                })
        if not evts:
            return

        # Los eventos en tiempo de descuento (minuto > 90) se sitúan en el minuto
        # 90, igual que se hace al construir el dataset; la etiqueta mantiene el
        # minuto real.
        for e in evts:
            e["xpos"] = min(e["minute"], 90)

        evts.sort(key=lambda e: e["xpos"])

        # Empaquetado greedy en varias filas: cada evento va a la primera fila
        # cuyo último evento esté a >= GAP minutos, evitando que las etiquetas se solapen
        GAP = 7
        last_in_row = [-999] * len(y_rows)
        for e in evts:
            ri = next(
                (r for r in range(len(y_rows)) if e["xpos"] - last_in_row[r] >= GAP),
                min(range(len(y_rows)), key=lambda r: last_in_row[r]),
            )
            e["y"] = y_rows[ri]
            last_in_row[ri] = e["xpos"]

        for is_past in (True, False):
            alpha = 1.0 if is_past else 0.22
            tc = t_color if is_past else "#cfcfcf"
            sub = [e for e in evts if (e["xpos"] <= minute) == is_past]
            if not sub:
                continue
            fig_tl.add_trace(go.Scatter(
                x=[e["xpos"] for e in sub],
                y=[e["y"] for e in sub],
                mode="markers+text",
                marker=dict(
                    symbol=[e["symbol"] for e in sub],
                    size=[e["size"] for e in sub],
                    color=t_color, opacity=alpha,
                    line=dict(width=1.5, color=t_color),
                ),
                text=[e["label"] for e in sub],
                textposition="bottom center",
                textfont=dict(size=9, color=tc),
                showlegend=False,
                hovertext=[e["hover"] for e in sub],
                hovertemplate="min %{x}  %{hovertext}<extra></extra>",
            ), row=row_n, col=1)

    # Local: eventos en la franja inferior (nombre arriba). Visitante: franja
    # superior (nombre abajo), dejando libre la esquina de cada literal.
    _add_events(home_shots_df, home_goals_df, 1, home_color,
                y_rows=[0.74, 0.52, 0.30])
    _add_events(away_shots_df, away_goals_df, 2, away_color,
                y_rows=[0.94, 0.72, 0.50])

    fig_tl.update_xaxes(range=[-3, 93], showgrid=False, zeroline=False, showticklabels=False, row=1, col=1)
    fig_tl.update_xaxes(range=[-3, 93], showgrid=False, zeroline=False,
                         tickvals=[1, 15, 30, 45, 60, 75, 90], ticksuffix="", row=2, col=1)
    fig_tl.update_yaxes(range=[0, 1], visible=False)
    fig_tl.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=34, b=36),
        plot_bgcolor="white", paper_bgcolor="white",
        showlegend=False,
    )
    st.plotly_chart(fig_tl, use_container_width=True, config={"displayModeBar": False})

    # ── Eventos del partido ──────────────────────────────────────────────
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
