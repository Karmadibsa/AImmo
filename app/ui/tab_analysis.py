"""Onglet 1 — Analyse de marché (graphiques)."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def render_analysis(df: pd.DataFrame) -> None:
    col_l, col_r = st.columns(2, gap="medium")

    # ── 1. Types de biens (Pie) ──────────────────────────────────────────────
    with col_l:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 🏠 Types de biens")
        if not df.empty:
            typ = df["type_local"].value_counts().reset_index()
            typ.columns = ["Type", "Annonces"]
            fig = px.pie(
                typ, names="Type", values="Annonces",
                color="Type",
                color_discrete_map={"Appartement": "#E8714A", "Maison": "#1B2B4B"},
                hole=0.5,
            )
            fig.update_layout(
                height=280, margin=dict(t=10, b=10, l=0, r=0),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                paper_bgcolor="white",
            )
            fig.update_traces(textinfo="percent+label", textfont_size=13)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 2. Distribution des prix (Histogramme) ───────────────────────────────
    with col_r:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 📊 Distribution des prix")
        df_h = df.dropna(subset=["valeur_fonciere"])
        if not df_h.empty:
            fig = px.histogram(
                df_h, x="valeur_fonciere", nbins=20, color="type_local",
                color_discrete_map={"Appartement": "#E8714A", "Maison": "#1B2B4B"},
                labels={"valeur_fonciere": "Prix (€)", "type_local": "Type", "count": "Annonces"},
                template="simple_white",
            )
            fig.update_layout(
                height=280, margin=dict(t=10, b=10, l=0, r=0),
                paper_bgcolor="white", plot_bgcolor="white",
                bargap=0.1, legend_title_text="",
                legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
            )
            fig.update_xaxes(tickformat=",.0f", ticksuffix=" €")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas assez de données.")
        st.markdown('</div>', unsafe_allow_html=True)

    col_l2, col_r2 = st.columns(2, gap="medium")

    # ── 3. Prix vs Surface (Scatter) ─────────────────────────────────────────
    with col_l2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 🔵 Prix en fonction de la surface")
        df_sc = df.dropna(subset=["valeur_fonciere", "surface_reelle_bati"])
        if not df_sc.empty:
            size_vals = df_sc["prix_m2"].fillna(0).astype(float).tolist()
            fig = px.scatter(
                df_sc, x="surface_reelle_bati", y="valeur_fonciere",
                color="type_local", size=size_vals,
                color_discrete_map={"Appartement": "#E8714A", "Maison": "#1B2B4B"},
                hover_name="titre",
                hover_data={"nombre_pieces_principales": True, "source": True,
                            "prix_m2": ":.0f", "surface_reelle_bati": False},
                labels={"surface_reelle_bati": "Surface (m²)", "valeur_fonciere": "Prix (€)",
                        "type_local": "Type", "prix_m2": "€/m²"},
                template="simple_white", opacity=0.8,
            )
            fig.update_layout(
                height=300, margin=dict(t=10, b=10, l=0, r=0),
                paper_bgcolor="white", plot_bgcolor="white",
                legend_title_text="",
                legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
            )
            fig.update_yaxes(tickformat=",.0f", ticksuffix=" €")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas assez de données.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 4. Répartition par Sources (Bar) ──────────────────────────────────────
    with col_r2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 📡 Répartition par Sources")
        if not df.empty:
            src = df["source"].value_counts().reset_index()
            src.columns = ["Source", "Annonces"]
            fig = px.bar(
                src, x="Source", y="Annonces",
                color="Source",
                color_discrete_sequence=["#E8714A", "#1B2B4B", "#27AE60", "#8B5CF6"],
                template="simple_white", text="Annonces",
            )
            fig.update_traces(textposition="outside", marker_line_width=0)
            fig.update_layout(
                height=300, margin=dict(t=20, b=10, l=0, r=0),
                showlegend=False, paper_bgcolor="white", plot_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 5. Analyse de régression — au choix ──────────────────────────────────
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### 📈 Analyse de régression")
    col_sel, _ = st.columns([2, 3])
    with col_sel:
        reg_mode = st.selectbox(
            "Type d'analyse",
            [
                "📈 Régression linéaire (Prix ~ Surface)",
                "📍 Prix/m² moyen par quartier",
                "📊 Régression multivariée (Surface + Pièces + DPE)",
            ],
            key="reg_mode_select",
        )

    df_reg = df.dropna(subset=["valeur_fonciere", "surface_reelle_bati"])

    if "Linéaire" in reg_mode:
        # Scatter + droite OLS par type de bien (calcul inline from scratch)
        fig_lr = go.Figure()
        COLS = {"Appartement": "#E8714A", "Maison": "#1B2B4B"}
        for ttype, grp in df_reg.groupby("type_local"):
            c = COLS.get(ttype, "#8B5CF6")
            xs = grp["surface_reelle_bati"].tolist()
            ys = grp["valeur_fonciere"].tolist()
            fig_lr.add_trace(go.Scatter(
                x=xs, y=ys, mode="markers", name=ttype,
                marker=dict(color=c, size=5, opacity=0.6),
                text=grp["titre"].fillna("").tolist(),
                hovertemplate="<b>%{text}</b><br>%{x:.0f} m² → %{y:,.0f} €<extra>" + ttype + "</extra>",
            ))
            if len(xs) >= 2:
                n = len(xs)
                xm = sum(xs) / n
                ym = sum(ys) / n
                denom = sum((x - xm) ** 2 for x in xs)
                if denom > 0:
                    slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denom
                    intercept = ym - slope * xm
                    x_min, x_max = min(xs), max(xs)
                    fig_lr.add_trace(go.Scatter(
                        x=[x_min, x_max],
                        y=[slope * x_min + intercept, slope * x_max + intercept],
                        mode="lines", name=f"Tendance {ttype}",
                        line=dict(color=c, width=2, dash="dash"),
                    ))
        fig_lr.update_layout(
            height=360, margin=dict(t=10, b=10, l=0, r=0),
            paper_bgcolor="white", plot_bgcolor="white",
            xaxis_title="Surface (m²)", yaxis_title="Prix (€)",
            legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
        )
        fig_lr.update_yaxes(tickformat=",.0f", ticksuffix=" €")
        st.plotly_chart(fig_lr, use_container_width=True)

    elif "quartier" in reg_mode:
        # Prix/m² médian par quartier (barres)
        col_qrt = "nom_commune" if "nom_commune" in df.columns else "quartier"
        df_qrt_chart = (
            df.dropna(subset=["prix_m2", col_qrt])
            .groupby(col_qrt)["prix_m2"]
            .agg(["median", "count"])
            .reset_index()
            .rename(columns={"median": "Prix/m² médian", "count": "N annonces"})
        )
        df_qrt_chart = df_qrt_chart[df_qrt_chart["N annonces"] >= 3].sort_values("Prix/m² médian", ascending=True)
        if not df_qrt_chart.empty:
            fig_qrt = px.bar(
                df_qrt_chart, x="Prix/m² médian", y=col_qrt, orientation="h",
                color="Prix/m² médian", color_continuous_scale="RdYlGn_r",
                text=df_qrt_chart["Prix/m² médian"].apply(lambda v: f"{v:,.0f} €/m²"),
                labels={"Prix/m² médian": "€/m² médian", col_qrt: "Quartier"},
                template="simple_white",
            )
            fig_qrt.update_traces(textposition="outside")
            fig_qrt.update_layout(
                height=max(300, len(df_qrt_chart) * 30), margin=dict(t=10, b=10, l=0, r=10),
                paper_bgcolor="white", plot_bgcolor="white",
                showlegend=False, coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_qrt, use_container_width=True)
        else:
            st.info("Pas assez de données par quartier (minimum 3 annonces).")

    else:
        # Régression multivariée — calcul à la demande
        try:
            from analysis.regression import compute_multivariate_regression
            with st.spinner("Calcul de la régression multivariée (descente de gradient)…"):
                df_mv = compute_multivariate_regression(df_reg)

            fig_mv = go.Figure()
            COLS = {"Appartement": "#E8714A", "Maison": "#1B2B4B"}
            for ttype, grp in df_mv.dropna(subset=["mv_prix_predit"]).groupby("type_local"):
                c = COLS.get(ttype, "#8B5CF6")
                r2 = grp["mv_r2"].iloc[0] if "mv_r2" in grp.columns else None
                r2_lbl = f" (R²={r2:.3f})" if r2 is not None else ""
                fig_mv.add_trace(go.Scatter(
                    x=grp["surface_reelle_bati"].tolist(),
                    y=grp["valeur_fonciere"].tolist(),
                    mode="markers", name=f"{ttype}{r2_lbl}",
                    marker=dict(
                        color=grp["mv_ecart_pct"].tolist(),
                        colorscale="RdYlGn_r", cmin=-30, cmax=30,
                        size=6, opacity=0.7, showscale=False,
                    ),
                    text=grp["titre"].fillna("").tolist(),
                    hovertemplate="<b>%{text}</b><br>%{x:.0f} m² → %{y:,.0f} €<extra>" + ttype + r2_lbl + "</extra>",
                ))
                # Droite de tendance multivariée (surface uniquement pour la ligne)
                xs = sorted(grp["surface_reelle_bati"].dropna().tolist())
                ys = grp.set_index("surface_reelle_bati")["mv_prix_predit"].reindex(xs, method="nearest").tolist()
                if xs:
                    fig_mv.add_trace(go.Scatter(
                        x=[xs[0], xs[-1]], y=[ys[0], ys[-1]],
                        mode="lines", name=f"Tendance {ttype} (MV)",
                        line=dict(color=c, width=2, dash="dot"),
                    ))
            fig_mv.update_layout(
                height=380, margin=dict(t=10, b=10, l=0, r=0),
                paper_bgcolor="white", plot_bgcolor="white",
                xaxis_title="Surface (m²)", yaxis_title="Prix (€)",
                legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
            )
            fig_mv.update_yaxes(tickformat=",.0f", ticksuffix=" €")
            st.plotly_chart(fig_mv, use_container_width=True)
        except Exception as exc:
            st.warning(f"Régression multivariée non disponible : {exc}")

    st.markdown('</div>', unsafe_allow_html=True)
