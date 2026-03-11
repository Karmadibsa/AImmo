"""
Observatoire Immobilier AIMMO — Toulon ≤ 500 000 €
Dashboard professionnel — Marché immobilier toulonnais en temps réel
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── Config page ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AIMMO — Observatoire Immobilier Toulon",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ─── Fond général ─── */
.stApp { background: #F4F6FA; }

/* ─── Sidebar ─── */
[data-testid="stSidebar"] {
    background: #1B2B4B !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] small {
    color: #CBD5E1 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #E8714A !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #CBD5E1 !important;
}
/* Inputs sidebar */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #253859 !important;
    color: white !important;
    border-color: #3A5278 !important;
}
[data-testid="stSidebar"] .stSlider [data-testid="stTickBar"] {
    color: #CBD5E1 !important;
}

/* ─── Header ─── */
.aimmo-header {
    background: linear-gradient(135deg, #1B2B4B 0%, #2C4A8A 100%);
    padding: 28px 32px;
    border-radius: 16px;
    margin-bottom: 28px;
    box-shadow: 0 6px 24px rgba(27,43,75,0.25);
}
.aimmo-header h1 {
    color: white;
    margin: 0 0 6px 0;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.3px;
}
.aimmo-header .subtitle {
    color: #93B4D4;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
}
.aimmo-header .badge {
    background: rgba(255,255,255,0.12);
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    color: #BDD4EC;
}

/* ─── Métriques ─── */
[data-testid="metric-container"] {
    background: white;
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    border-top: 3px solid #E8714A;
}
[data-testid="stMetricLabel"]  { color: #64748B !important; font-size: 13px !important; }
[data-testid="stMetricValue"]  { color: #1B2B4B !important; font-weight: 700 !important; }

/* ─── Onglets ─── */
[data-baseweb="tab-list"] {
    gap: 4px;
    background: white;
    padding: 6px 8px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    margin-bottom: 20px;
}
[data-baseweb="tab"] {
    border-radius: 8px !important;
    font-weight: 500 !important;
    color: #64748B !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: #1B2B4B !important;
    color: white !important;
}

/* ─── Tags NLP ─── */
.tag {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    margin: 2px 2px 2px 0;
}
.tag-blue   { background: #DBEAFE; color: #1D4ED8; }
.tag-green  { background: #DCFCE7; color: #16A34A; }
.tag-orange { background: #FEF3C7; color: #D97706; }
.tag-sea    { background: #CFFAFE; color: #0E7490; }

/* ─── Section card ─── */
.section-card {
    background: white;
    border-radius: 14px;
    padding: 20px 22px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 16px;
}

/* ─── Prix badge ─── */
.prix-badge {
    background: #FFF7ED;
    border: 1px solid #FED7AA;
    color: #C2410C;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 8px;
    font-size: 15px;
}
.pm2-badge {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    color: #1D4ED8;
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 6px;
}

hr { border: none; border-top: 1px solid #E2E8F0; margin: 16px 0; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/Karmadibsa/AImmo/"
    "feat/axel-verification/data/annonces.csv"
)
CSV_PATH = Path(__file__).parent.parent / "data" / "annonces.csv"

NLP_TAGS = {
    "Vue mer":    (["vue mer", "vue sur la mer", "vue panoramique"],    "tag-sea"),
    "Terrasse":   (["terrasse"],                                        "tag-green"),
    "Balcon":     (["balcon"],                                          "tag-green"),
    "Parking":    (["parking", "stationnement", "place de parking"],   "tag-orange"),
    "Garage":     (["garage", "box"],                                  "tag-orange"),
    "Ascenseur":  (["ascenseur"],                                       "tag-blue"),
    "Rénové":     (["refait", "rénové", "rénovation", "neuf", "neuve"],"tag-green"),
    "Cave":       (["cave"],                                            "tag-orange"),
    "Piscine":    (["piscine"],                                         "tag-blue"),
    "Proche mer": (["bord de mer", "pieds dans l'eau", "plages",
                    "proche mer", "400 mètres"],                        "tag-sea"),
}


def extract_tags(description: str) -> list:
    if not isinstance(description, str):
        return []
    d = description.lower()
    return [(lbl, css) for lbl, (kws, css) in NLP_TAGS.items() if any(k in d for k in kws)]


def tags_html(tags: list) -> str:
    return "".join(f'<span class="tag {css}">{lbl}</span>' for lbl, css in tags)


# ── Données ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    try:
        df = pd.read_csv(GITHUB_RAW_URL, encoding="utf-8-sig")
    except Exception:
        if not CSV_PATH.exists():
            return pd.DataFrame()
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    for col in ["valeur_fonciere", "surface_reelle_bati", "nombre_pieces_principales"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    mask = df["surface_reelle_bati"].fillna(0) > 0
    df["prix_m2"] = float("nan")
    df.loc[mask, "prix_m2"] = (
        df.loc[mask, "valeur_fonciere"] / df.loc[mask, "surface_reelle_bati"]
    ).round(0)
    df["prix_m2"] = pd.to_numeric(df["prix_m2"], errors="coerce")

    if "date_mutation" in df.columns:
        df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors="coerce")

    if "description" in df.columns:
        df["tags"] = df["description"].apply(extract_tags)

    return df


df_raw = load_data()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏠 AIMMO")
    st.markdown("**Observatoire Immobilier**")
    st.caption("Marché toulonnais — temps réel")
    st.markdown("---")

    st.markdown("### 🎯 Filtres")

    types_dispo = sorted(df_raw["type_local"].dropna().unique()) if not df_raw.empty else []
    type_filtre = st.selectbox("Type de bien", ["Tous"] + list(types_dispo))

    budget_max = st.slider("Budget max (€)", 50_000, 500_000, 500_000, 10_000, format="%d €")
    surface_min = st.number_input("Surface min (m²)", 0, 300, 0, 5)
    pieces_min  = st.number_input("Pièces min",        0, 8,   0, 1)

    sources_dispo = sorted(df_raw["source"].dropna().unique()) if not df_raw.empty else []
    source_filtre = st.selectbox("Source", ["Toutes"] + list(sources_dispo))

    keyword = st.text_input("🔍 Mot-clé", placeholder="terrasse, parking…")

    st.markdown("---")

    if not df_raw.empty and "date_mutation" in df_raw.columns:
        last_upd = df_raw["date_mutation"].max()
        st.caption("🕐 Dernière mise à jour")
        if pd.notna(last_upd):
            st.markdown(f"**`{last_upd.strftime('%d/%m/%Y %H:%M')}`**")

    st.caption(f"📦 {len(df_raw):,} annonces en base")
    st.markdown("---")

    if st.button("🔄 Actualiser", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Guard ──────────────────────────────────────────────────────────────────────
if df_raw.empty:
    st.error("⚠️ Aucune donnée disponible. Vérifiez que le scraping a bien tourné.")
    st.stop()

# ── Filtrage ───────────────────────────────────────────────────────────────────
df = df_raw.copy()
if type_filtre != "Tous":
    df = df[df["type_local"] == type_filtre]
if budget_max < 500_000:
    df = df[df["valeur_fonciere"] <= budget_max]
if surface_min > 0:
    df = df[df["surface_reelle_bati"] >= surface_min]
if pieces_min > 0:
    df = df[df["nombre_pieces_principales"] >= pieces_min]
if source_filtre != "Toutes":
    df = df[df["source"] == source_filtre]
if keyword:
    mask_kw = (
        df["description"].fillna("").str.contains(keyword, case=False) |
        df["titre"].fillna("").str.contains(keyword, case=False)
    )
    df = df[mask_kw]

# ── Header ─────────────────────────────────────────────────────────────────────
last_upd_str = "—"
if not df_raw.empty and "date_mutation" in df_raw.columns:
    lu = df_raw["date_mutation"].max()
    if pd.notna(lu):
        last_upd_str = lu.strftime("%d/%m/%Y à %H:%M")

st.markdown(f"""
<div class="aimmo-header">
  <h1>🏠 Observatoire Immobilier — Toulon</h1>
  <div class="subtitle">
    <span class="badge">≤ 500 000 €</span>
    <span class="badge">PAP · LeBoncoin</span>
    <span>🕐 Mis à jour le {last_upd_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPIs ───────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

prix_med  = df["valeur_fonciere"].median() if not df.empty and df["valeur_fonciere"].notna().any() else None
surf_med  = df["surface_reelle_bati"].median() if not df.empty and df["surface_reelle_bati"].notna().any() else None
pm2_med   = df["prix_m2"].median() if not df.empty and df["prix_m2"].notna().any() else None
delta_nb  = len(df) - len(df_raw) if len(df) != len(df_raw) else None

k1.metric("📋 Annonces", f"{len(df):,}", delta=f"{delta_nb:+}" if delta_nb else None)
k2.metric("💰 Prix médian",    f"{prix_med:,.0f} €"    if prix_med else "—")
k3.metric("📐 Surface médiane", f"{surf_med:.0f} m²"   if surf_med else "—")
k4.metric("💶 Prix/m² médian",  f"{pm2_med:,.0f} €/m²" if pm2_med else "—")

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_analyse, tab_liste = st.tabs(["📊  Analyse de marché", "📋  Liste des biens"])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYSE
# ════════════════════════════════════════════════════════════════════════════════
with tab_analyse:

    col_l, col_r = st.columns(2, gap="medium")

    # Distribution des prix
    with col_l:
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
                height=300, margin=dict(t=10, b=10, l=0, r=0),
                paper_bgcolor="white", plot_bgcolor="white",
                bargap=0.1, legend_title_text="",
                legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
            )
            fig.update_xaxes(tickformat=",.0f", ticksuffix=" €")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas assez de données.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Prix vs Surface
    with col_r:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 🔵 Prix en fonction de la surface")
        df_sc = df.dropna(subset=["valeur_fonciere", "surface_reelle_bati"])
        if not df_sc.empty:
            # Convertir en liste Python pour éviter le bug narwhals/Plotly (Python 3.14)
            size_vals = df_sc["prix_m2"].fillna(0).astype(float).tolist()
            fig2 = px.scatter(
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
            fig2.update_layout(
                height=300, margin=dict(t=10, b=10, l=0, r=0),
                paper_bgcolor="white", plot_bgcolor="white",
                legend_title_text="",
                legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
            )
            fig2.update_yaxes(tickformat=",.0f", ticksuffix=" €")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Pas assez de données.")
        st.markdown('</div>', unsafe_allow_html=True)

    col_l2, col_r2 = st.columns(2, gap="medium")

    # Répartition source
    with col_l2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 📡 Sources")
        if not df.empty:
            src = df["source"].value_counts().reset_index()
            src.columns = ["Source", "Annonces"]
            fig3 = px.bar(
                src, x="Source", y="Annonces",
                color="Source",
                color_discrete_sequence=["#E8714A", "#1B2B4B", "#27AE60", "#8B5CF6"],
                template="simple_white", text="Annonces",
            )
            fig3.update_traces(textposition="outside", marker_line_width=0)
            fig3.update_layout(
                height=260, margin=dict(t=20, b=10, l=0, r=0),
                showlegend=False, paper_bgcolor="white", plot_bgcolor="white",
            )
            st.plotly_chart(fig3, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Répartition type
    with col_r2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 🏠 Types de biens")
        if not df.empty:
            typ = df["type_local"].value_counts().reset_index()
            typ.columns = ["Type", "Annonces"]
            fig4 = px.pie(
                typ, names="Type", values="Annonces",
                color="Type",
                color_discrete_map={"Appartement": "#E8714A", "Maison": "#1B2B4B"},
                hole=0.5,
            )
            fig4.update_layout(
                height=260, margin=dict(t=10, b=10, l=0, r=0),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            )
            fig4.update_traces(textinfo="percent+label", textfont_size=13)
            st.plotly_chart(fig4, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — LISTE
# ════════════════════════════════════════════════════════════════════════════════
with tab_liste:
    st.markdown(f"**{len(df):,} bien(s)** correspondent à vos critères")

    if df.empty:
        st.info("😕 Aucune annonce ne correspond à vos filtres.")
    else:
        # ── Tableau ────────────────────────────────────────────────────────────
        COLS = {
            "source":                    "Source",
            "type_local":                "Type",
            "titre":                     "Titre",
            "valeur_fonciere":           "Prix (€)",
            "surface_reelle_bati":       "Surface (m²)",
            "nombre_pieces_principales": "Pièces",
            "prix_m2":                   "€/m²",
            "nom_commune":               "Commune",
            "url":                       "Lien",
        }
        df_disp = df[[c for c in COLS if c in df.columns]].copy()
        df_disp = df_disp.rename(columns=COLS).sort_values("Prix (€)", ascending=True)

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
            },
            height=360,
        )

        st.markdown("---")
        st.markdown("#### 🔍 Fiches détaillées")

        for _, row in df.iterrows():
            titre   = str(row.get("titre", "Annonce sans titre"))
            prix    = row.get("valeur_fonciere")
            surface = row.get("surface_reelle_bati")
            pm2     = row.get("prix_m2")
            tags    = row.get("tags", [])
            source  = str(row.get("source", "")).upper()

            # Label expander
            lbl = titre
            if pd.notna(prix):    lbl += f"  ·  {prix:,.0f} €"
            if pd.notna(surface): lbl += f"  ·  {surface:.0f} m²"

            with st.expander(lbl):
                left, right = st.columns([1, 2], gap="medium")

                with left:
                    # Badges prix
                    if pd.notna(prix):
                        st.markdown(
                            f'<span class="prix-badge">{prix:,.0f} €</span>'
                            + (f' <span class="pm2-badge">{pm2:,.0f} €/m²</span>' if pd.notna(pm2) else ""),
                            unsafe_allow_html=True,
                        )
                        st.markdown("")

                    info_lines = [
                        ("🏷️ Source",   source),
                        ("🏠 Type",     row.get("type_local", "—")),
                        ("📐 Surface",  f"{surface:.0f} m²" if pd.notna(surface) else "—"),
                        ("🚪 Pièces",   f"{int(row['nombre_pieces_principales'])}" if pd.notna(row.get("nombre_pieces_principales")) else "—"),
                        ("📍 Commune",  row.get("nom_commune", "—")),
                    ]
                    for icon_lbl, val in info_lines:
                        st.markdown(f"**{icon_lbl}** : {val}")

                    url = row.get("url")
                    if pd.notna(url) and url:
                        st.markdown(f"<br>[🔗 Voir l'annonce →]({url})", unsafe_allow_html=True)

                with right:
                    if tags:
                        st.markdown(tags_html(tags), unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)

                    desc = str(row.get("description", "")).strip()
                    if desc and desc != "nan":
                        st.markdown(
                            f"<small style='color:#475569;line-height:1.6'>"
                            f"{desc[:700]}{'…' if len(desc) > 700 else ''}"
                            f"</small>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.caption("Pas de description disponible.")
