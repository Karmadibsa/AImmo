"""Onglet 2 — Liste des biens avec tableau + fiches détaillées."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from ui.components import market_badge_html, photo_carousel, tags_html

# Import du moteur k-NN from scratch
try:
    _root = str(Path(__file__).parent.parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from analysis.similarity import find_similar_properties
    _HAS_KNN = True
except Exception:
    _HAS_KNN = False


def render_list(df: pd.DataFrame) -> None:
    st.markdown(f"**{len(df):,} bien(s)** correspondent à vos critères")

    if df.empty:
        st.info("😕 Aucune annonce ne correspond à vos filtres.")
        return

    # ── Tableau ──────────────────────────────────────────────────────────────
    COLS = {
        "source":                    "Source",
        "type_local":                "Type",
        "titre":                     "Titre",
        "valeur_fonciere":           "Prix (€)",
        "surface_reelle_bati":       "Surface (m²)",
        "nombre_pieces_principales": "Pièces",
        "prix_m2":                   "€/m²",
        "dpe":                       "DPE",
        "nom_commune":               "Commune",
        "prix_baisse":               "📉",
        "url":                       "Lien",
    }
    df_disp = (
        df[[c for c in COLS if c in df.columns]]
        .copy()
        .rename(columns=COLS)
        .sort_values("Prix (€)", ascending=True)
    )
    st.dataframe(
        df_disp,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Lien":         st.column_config.LinkColumn("Lien", display_text="🔗 Voir"),
            "Titre":        st.column_config.TextColumn("Titre", width="large"),
            "Prix (€)":     st.column_config.NumberColumn("Prix (€)",     format="%.0f €"),
            "Surface (m²)": st.column_config.NumberColumn("Surface (m²)", format="%.0f m²"),
            "€/m²":         st.column_config.NumberColumn("€/m²",         format="%.0f €"),
            "Pièces":       st.column_config.NumberColumn("Pièces",        format="%d"),
            "DPE":          st.column_config.TextColumn("DPE", width="small"),
            "📉":           st.column_config.CheckboxColumn("📉 Baisse"),
        },
        height=360,
    )

    st.markdown("---")
    st.markdown("#### 🔍 Fiches détaillées")

    for idx_int, (_, row) in enumerate(df.iterrows()):
        titre       = str(row.get("titre", "Annonce sans titre"))
        prix        = row.get("valeur_fonciere")
        surface     = row.get("surface_reelle_bati")
        pm2         = row.get("prix_m2")
        ep_lst      = row.get("ecart_pct")
        tags        = row.get("tags", [])
        source      = str(row.get("source", "")).upper()
        prix_baisse = row.get("prix_baisse")
        annee_constr= row.get("annee_construction")

        lbl = titre
        if pd.notna(prix):    lbl += f"  ·  {prix:,.0f} €"
        if pd.notna(surface): lbl += f"  ·  {surface:.0f} m²"
        if prix_baisse is True or prix_baisse == 1: lbl += "  📉"
        if pd.notna(ep_lst):
            ep_f = float(ep_lst)
            if ep_f < -10:  lbl += "  🎯"
            elif ep_f < -5: lbl += "  ✅"
            elif ep_f > 10: lbl += "  ⚠️"

        with st.expander(lbl):
            left, right = st.columns([1, 2], gap="medium")

            with left:
                if pd.notna(ep_lst):
                    st.markdown(market_badge_html(float(ep_lst)), unsafe_allow_html=True)
                    prix_p  = row.get("prix_predit")
                    ecart_e = row.get("ecart")
                    if pd.notna(prix_p) and pd.notna(ecart_e):
                        st.caption(f"Prix attendu : {prix_p:,.0f} €  ·  Écart : {ecart_e:+,.0f} €")

                if pd.notna(prix):
                    st.markdown(
                        f'<span class="prix-badge">{prix:,.0f} €</span>'
                        + (f' <span class="pm2-badge">{pm2:,.0f} €/m²</span>' if pd.notna(pm2) else ""),
                        unsafe_allow_html=True,
                    )

                # Badges DPE + GES
                _DPE_COLORS = {
                    "A": ("#00A651", "#fff"), "B": ("#51B747", "#fff"),
                    "C": ("#A8CC3B", "#000"), "D": ("#FFED00", "#000"),
                    "E": ("#F7931D", "#fff"), "F": ("#ED1C24", "#fff"),
                    "G": ("#9B1B22", "#fff"),
                }
                _GES_COLORS = {
                    "A": ("#E8F5E9", "#1B5E20"), "B": ("#C8E6C9", "#1B5E20"),
                    "C": ("#A5D6A7", "#1B5E20"), "D": ("#EDE7F6", "#4A148C"),
                    "E": ("#CE93D8", "#fff"),    "F": ("#AB47BC", "#fff"),
                    "G": ("#6A1B9A", "#fff"),
                }
                dpe_val = row.get("dpe")
                ges_val = row.get("ges")
                nrj_val = row.get("energie_valeur")
                badges_html = ""
                if pd.notna(dpe_val) and str(dpe_val) in _DPE_COLORS:
                    bg, fg = _DPE_COLORS[str(dpe_val)]
                    badges_html += (
                        f'<span style="background:{bg};color:{fg};padding:2px 10px;'
                        f'border-radius:4px;font-weight:700;font-size:13px;margin-right:6px;">'
                        f'DPE {dpe_val}</span>'
                    )
                if pd.notna(ges_val) and str(ges_val) in _GES_COLORS:
                    bg, fg = _GES_COLORS[str(ges_val)]
                    badges_html += (
                        f'<span style="background:{bg};color:{fg};padding:2px 10px;'
                        f'border-radius:4px;font-weight:600;font-size:13px;">GES {ges_val}</span>'
                    )
                if badges_html:
                    st.markdown(badges_html, unsafe_allow_html=True)
                if pd.notna(nrj_val) and nrj_val > 0:
                    st.caption(f"⚡ {int(nrj_val)} kWhEP/m²/an")

                info_lines = [
                    ("🏷️ Source",  source),
                    ("🏠 Type",    row.get("type_local", "—")),
                    ("📐 Surface", f"{surface:.0f} m²" if pd.notna(surface) else "—"),
                    ("🚪 Pièces",  f"{int(row['nombre_pieces_principales'])}"
                     if pd.notna(row.get("nombre_pieces_principales")) else "—"),
                    ("📍 Commune", row.get("nom_commune", "—")),
                ]
                if pd.notna(annee_constr) and annee_constr:
                    info_lines.append(("🏗️ Construction", str(int(annee_constr))))
                if prix_baisse is True or prix_baisse == 1:
                    info_lines.append(("📉 Prix", "**En baisse récente**"))

                for icon_lbl, val in info_lines:
                    st.markdown(f"**{icon_lbl}** : {val}")

                url = row.get("url")
                if pd.notna(url) and url:
                    st.markdown(f"[🔗 Voir l'annonce →]({url})")

                visite = row.get("visite_virtuelle")
                if pd.notna(visite) and visite:
                    st.markdown(f"[🥽 Visite virtuelle →]({visite})")

            with right:
                # Carousel photos
                _photos_raw = row.get("photos")
                if _photos_raw is not None:
                    _card_key = str(row.get("url", idx_int))
                    photo_carousel(_photos_raw, key=f"list_{_card_key}")

                if tags:
                    st.markdown(tags_html(tags), unsafe_allow_html=True)
                desc = str(row.get("description", "")).strip()
                if desc and desc != "nan":
                    st.markdown(
                        f"<small style='color:#475569;line-height:1.6'>"
                        f"{desc[:700]}{'…' if len(desc) > 700 else ''}</small>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("Pas de description disponible.")

            # ── Biens similaires (k-NN from scratch) ─────────────────────────
            if _HAS_KNN and len(df) >= 4:
                st.markdown("---")
                st.markdown("**🔍 Biens similaires** *(k-NN from scratch)*")
                try:
                    items_list = df.to_dict("records")
                    similars = find_similar_properties(
                        items_list, target_idx=idx_int, k=3,
                        feature_keys=["surface_reelle_bati", "valeur_fonciere",
                                      "nombre_pieces_principales", "prix_m2"],
                    )
                    scols = st.columns(len(similars))
                    for ci, sim in enumerate(similars):
                        with scols[ci]:
                            s_titre   = str(sim.get("titre", ""))[:40]
                            s_prix    = sim.get("valeur_fonciere")
                            s_surf    = sim.get("surface_reelle_bati")
                            s_sim_pct = sim.get("_similarite_pct", 0)
                            s_url     = sim.get("url", "")
                            prix_str  = f"{s_prix:,.0f} €"  if pd.notna(s_prix) else "—"
                            surf_str  = f"{s_surf:.0f} m²" if pd.notna(s_surf) else "—"
                            st.markdown(
                                f'<div class="section-card" style="padding:10px 14px;">'
                                f'<small style="color:#64748B;">{s_sim_pct:.0f}% similaire</small><br>'
                                f'<b style="font-size:12px;">{s_titre}…</b><br>'
                                f'<span style="color:#1B2B4B;font-weight:700;">{prix_str}</span>'
                                f' · <span style="color:#64748B;">{surf_str}</span><br>'
                                + (f'<a href="{s_url}" target="_blank" style="font-size:11px;">🔗 Voir</a>' if s_url else "")
                                + '</div>',
                                unsafe_allow_html=True,
                            )
                except Exception:
                    pass  # silencieux si erreur k-NN
