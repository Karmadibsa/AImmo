"""Onglet 4 — Assistant conversationnel (wizard rule-based)."""

import pandas as pd
import streamlit as st

from ui.components import market_badge_html, tags_html


def _bot(text: str) -> None:
    st.markdown(f'<div class="bot-bubble">🤖 {text}</div>', unsafe_allow_html=True)


def _usr(text: str) -> None:
    st.markdown(f'<div class="user-bubble">{text}</div>', unsafe_allow_html=True)


def render_assistant(df_scored: pd.DataFrame) -> None:
    # ── Bandeau Phase 2 ──────────────────────────────────────────────────────
    st.info(
        "🚧 **Phase 2 — NidBot IA (à venir)** : "
        "La prochaine phase du projet intégrera un conseiller conversationnel "
        "basé sur l'IA (LLM), disponible 24h/24, capable d'argumenter ses "
        "recommandations et de générer des rapports PDF personnalisés. "
        "L'assistant ci-dessous est la version **Projet 1** : guidage rule-based "
        "par critères, sans intelligence artificielle."
    )
    st.markdown("---")

    _, center, _ = st.columns([1, 3, 1])

    with center:
        st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)

        _bot("Bonjour ! Je suis votre assistant AIMMO. 👋")
        _bot("Je vais vous aider à trouver les <b>meilleures opportunités</b> "
             "sur le marché toulonnais selon vos critères.")

        # ── ÉTAPE 0 — TYPE DE BIEN ───────────────────────────────────────────
        _bot("Vous cherchez quel type de bien ?")
        if st.session_state.asst_step == 0:
            c1, c2 = st.columns(2)
            if c1.button("🏢 Appartement", use_container_width=True, key="asst_appart"):
                st.session_state.asst_type = "Appartement"
                st.session_state.asst_step = 1
                st.rerun()
            if c2.button("🏡 Maison", use_container_width=True, key="asst_maison"):
                st.session_state.asst_type = "Maison"
                st.session_state.asst_step = 1
                st.rerun()

        # ── ÉTAPE 1+ — BUDGET ────────────────────────────────────────────────
        if st.session_state.asst_step >= 1:
            _usr(f"{'🏢 Appartement' if st.session_state.asst_type == 'Appartement' else '🏡 Maison'}")
            _bot("Quel est votre <b>budget maximum</b> ?")
            if st.session_state.asst_step == 1:
                _budgets = [
                    ("💶 Moins de 200 000 €",  200_000),
                    ("💶 200 000 – 300 000 €", 300_000),
                    ("💶 300 000 – 400 000 €", 400_000),
                    ("💶 Jusqu'à 500 000 €",   500_000),
                ]
                cols = st.columns(2)
                for i, (lbl, val) in enumerate(_budgets):
                    if cols[i % 2].button(lbl, key=f"asst_budget_{i}", use_container_width=True):
                        st.session_state.asst_budget = val
                        st.session_state.asst_step = 2
                        st.rerun()

        # ── ÉTAPE 2+ — SURFACE ───────────────────────────────────────────────
        if st.session_state.asst_step >= 2:
            _bud_lbl = {200_000: "< 200 000 €", 300_000: "200–300 000 €",
                        400_000: "300–400 000 €", 500_000: "≤ 500 000 €"}
            _usr(f"💶 {_bud_lbl.get(st.session_state.asst_budget, '')}")
            _bot("Quelle <b>surface minimum</b> vous faut-il ?")
            if st.session_state.asst_step == 2:
                _surfaces = [
                    ("📐 Peu importe", 0),
                    ("📐 ≥ 30 m²",    30),
                    ("📐 ≥ 50 m²",    50),
                    ("📐 ≥ 70 m²",    70),
                ]
                cols = st.columns(2)
                for i, (lbl, val) in enumerate(_surfaces):
                    if cols[i % 2].button(lbl, key=f"asst_surf_{i}", use_container_width=True):
                        st.session_state.asst_surface = val
                        st.session_state.asst_step = 3
                        st.rerun()

        # ── ÉTAPE 3 — RÉSULTATS ──────────────────────────────────────────────
        if st.session_state.asst_step >= 3:
            _surf_lbl = {0: "Peu importe", 30: "≥ 30 m²", 50: "≥ 50 m²", 70: "≥ 70 m²"}
            _usr(f"📐 {_surf_lbl.get(st.session_state.asst_surface, '')}")

            _t = st.session_state.asst_type
            _b = st.session_state.asst_budget
            _s = st.session_state.asst_surface

            if df_scored.empty or "ecart_pct" not in df_scored.columns:
                _bot("😕 Pas assez de données pour la régression. Réessayez après le prochain scraping.")
            else:
                _mask = (
                    (df_scored["type_local"] == _t) &
                    (df_scored["valeur_fonciere"] <= _b) &
                    (df_scored["surface_reelle_bati"] >= _s)
                )
                df_res = df_scored[_mask].sort_values("ecart_pct")
                n_res  = len(df_res)
                n_opp  = (df_res["ecart_pct"] < -10).sum()

                if n_res == 0:
                    _bot("😕 Aucune annonce ne correspond à ces critères. "
                         "Essayez d'élargir votre budget ou surface.")
                else:
                    _bot(f"J'ai trouvé <b>{n_res} bien(s)</b> correspondant à votre recherche, "
                         f"dont <b>{n_opp} opportunité(s)</b> sous-évaluée(s) par le marché. 👇")

                    for _, row in df_res.head(15).iterrows():
                        titre   = str(row.get("titre", "Annonce sans titre"))
                        prix    = row.get("valeur_fonciere")
                        surface = row.get("surface_reelle_bati")
                        pm2     = row.get("prix_m2")
                        ecart_p = row.get("ecart_pct")
                        ecart_e = row.get("ecart")
                        prix_p  = row.get("prix_predit")
                        tags    = row.get("tags", [])
                        url     = row.get("url")

                        if pd.notna(ecart_p):
                            ep = float(ecart_p)
                            card_cls = ("opport" if ep < -10 else
                                        "bonne"  if ep < -5  else
                                        "normal" if ep <= 5  else "eleve")
                        else:
                            card_cls = "normal"

                        prix_str    = f"{prix:,.0f} €"    if pd.notna(prix)    else "—"
                        surface_str = f"{surface:.0f} m²" if pd.notna(surface) else "—"

                        st.markdown(
                            f'<div class="result-card {card_cls}">'
                            f'<b style="font-size:14px">{titre[:70]}</b><br>'
                            f'<span style="color:#64748B;font-size:12px">'
                            f'{surface_str} &nbsp;·&nbsp; {prix_str}'
                            + (f" &nbsp;·&nbsp; {pm2:,.0f} €/m²" if pd.notna(pm2) else "")
                            + "</span></div>",
                            unsafe_allow_html=True,
                        )

                        with st.expander("Voir le détail →"):
                            left, right = st.columns([1, 2])
                            with left:
                                if pd.notna(ecart_p):
                                    st.markdown(market_badge_html(float(ecart_p)), unsafe_allow_html=True)
                                if pd.notna(prix_p) and pd.notna(ecart_e):
                                    st.caption(f"Prix attendu : {prix_p:,.0f} €  ·  Économie : {abs(ecart_e):,.0f} €")
                                if pd.notna(prix):
                                    st.markdown(
                                        f'<span class="prix-badge">{prix:,.0f} €</span>'
                                        + (f' <span class="pm2-badge">{pm2:,.0f} €/m²</span>' if pd.notna(pm2) else ""),
                                        unsafe_allow_html=True,
                                    )
                                for icon_lbl, val in [
                                    ("🏷️ Source",  str(row.get("source", "")).upper()),
                                    ("📐 Surface", surface_str),
                                    ("🚪 Pièces",  f"{int(row['nombre_pieces_principales'])}"
                                     if pd.notna(row.get("nombre_pieces_principales")) else "—"),
                                    ("📍 Commune", row.get("nom_commune", "—")),
                                ]:
                                    st.markdown(f"**{icon_lbl}** : {val}")
                                if pd.notna(url) and url:
                                    st.markdown(f"[🔗 Voir l'annonce →]({url})")
                            with right:
                                if tags:
                                    st.markdown(tags_html(tags), unsafe_allow_html=True)
                                desc = str(row.get("description", "")).strip()
                                if desc and desc != "nan":
                                    st.markdown(
                                        f"<small style='color:#475569;line-height:1.6'>"
                                        f"{desc[:600]}{'…' if len(desc) > 600 else ''}</small>",
                                        unsafe_allow_html=True,
                                    )
                                else:
                                    st.caption("Pas de description disponible.")

                    if n_res > 15:
                        _bot(f"… et {n_res - 15} autre(s) bien(s). "
                             "Affinez vos critères pour voir moins de résultats.")

            # Bouton reset
            if st.button("🔄 Nouvelle recherche", use_container_width=False, key="asst_reset"):
                st.session_state.asst_step    = 0
                st.session_state.asst_type    = None
                st.session_state.asst_budget  = None
                st.session_state.asst_surface = None
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
