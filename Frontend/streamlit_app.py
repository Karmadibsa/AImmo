"""
Observatoire Immobilier AIMMO — Toulon ≤ 500 000 €

Interface de visualisation des annonces immobilières.
Les données (data/annonces.csv) sont mises à jour automatiquement toutes les heures
via GitHub Actions (scraping PAP + SeLoger + LeBoncoin).

Déploiement : Streamlit Community Cloud
  - App file  : Frontend/streamlit_app.py
  - Requis    : Frontend/requirements.txt
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# ── Config page ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Observatoire Immobilier — Toulon",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #1B2B4B; }
    section[data-testid="stSidebar"] * { color: white !important; }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { color: #E8714A !important; }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stNumberInput label { color: #AABBCC !important; }

    /* Header */
    .aimmo-header {
        background: linear-gradient(135deg, #1B2B4B 0%, #2C3E6B 100%);
        color: white;
        padding: 20px 24px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .aimmo-header h1 { color: white; margin: 0; font-size: 26px; }
    .aimmo-header p  { color: #AABBCC; margin: 4px 0 0; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ── Chargement du CSV ───────────────────────────────────────────────────────────
# Source primaire : GitHub raw (toujours à jour même sans redéploiement Streamlit)
# Source secondaire : fichier local (fallback dev)
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/Karmadibsa/AImmo/"
    "feat/axel-verification/data/annonces.csv"
)
CSV_PATH = Path(__file__).parent.parent / "data" / "annonces.csv"


@st.cache_data(ttl=300)    # Cache 5min — relit depuis GitHub à chaque expiration
def load_data() -> pd.DataFrame:
    # 1. Essaie de lire depuis GitHub raw (données toujours fraîches)
    try:
        df = pd.read_csv(GITHUB_RAW_URL, encoding="utf-8-sig")
    except Exception:
        # 2. Fallback : fichier local (développement ou GitHub indisponible)
        if not CSV_PATH.exists():
            return pd.DataFrame()
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    # Conversion des types numériques
    for col in ["valeur_fonciere", "surface_reelle_bati", "nombre_pieces_principales"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Prix au m²
    mask = df["surface_reelle_bati"] > 0
    df["prix_m2"] = None
    df.loc[mask, "prix_m2"] = (
        df.loc[mask, "valeur_fonciere"] / df.loc[mask, "surface_reelle_bati"]
    ).round(0)

    # Date
    if "date_mutation" in df.columns:
        df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors="coerce")

    return df


df_raw = load_data()

# ── Sidebar — Filtres ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🏠 AIMMO")
    st.markdown("### Observatoire Immobilier")
    st.markdown("*Marché toulonnais — temps réel*")
    st.markdown("---")

    st.markdown("### 🎯 Filtres")

    # Type de bien
    types_dispo = sorted(df_raw["type_local"].dropna().unique().tolist()) if not df_raw.empty else []
    type_filtre = st.selectbox("Type de bien", ["Tous"] + types_dispo)

    # Budget
    budget_max = st.slider(
        "Budget maximum (€)",
        min_value=50_000,
        max_value=500_000,
        value=500_000,
        step=10_000,
        format="%d €",
    )

    # Surface
    surface_min = st.number_input("Surface minimum (m²)", min_value=0, max_value=300, value=0, step=5)

    # Pièces
    pieces_min = st.number_input("Pièces minimum", min_value=0, max_value=8, value=0, step=1)

    # Source
    sources_dispo = sorted(df_raw["source"].dropna().unique().tolist()) if not df_raw.empty else []
    source_filtre = st.selectbox("Source", ["Toutes"] + sources_dispo)

    st.markdown("---")

    # Dernière mise à jour
    if not df_raw.empty and "date_mutation" in df_raw.columns:
        last_upd = df_raw["date_mutation"].max()
        if pd.notna(last_upd):
            st.markdown(f"🕐 **Dernière mise à jour**  \n`{last_upd.strftime('%d/%m/%Y %H:%M')}`")
        else:
            st.markdown("🕐 Date inconnue")
    st.markdown(f"📦 **{len(df_raw):,}** annonces en base")

    st.markdown("---")
    if st.button("🔄 Recharger les données", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ── Garde-fou : aucune donnée ──────────────────────────────────────────────────
if df_raw.empty:
    st.markdown("""
    <div class="aimmo-header">
        <h1>🏠 Observatoire Immobilier — Toulon</h1>
        <p>PAP · SeLoger · LeBoncoin — Budget ≤ 500 000 €</p>
    </div>
    """, unsafe_allow_html=True)
    st.error("⚠️ Aucune donnée trouvée. Le fichier `data/annonces.csv` est introuvable ou vide.")
    st.info(
        "**Pour générer les données :**\n"
        "- En local : `python -m scraping.run_scraping`\n"
        "- Automatiquement : le workflow GitHub Actions tourne toutes les heures."
    )
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


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="aimmo-header">
    <h1>🏠 Observatoire Immobilier — Toulon</h1>
    <p>PAP · SeLoger · LeBoncoin — Budget ≤ 500 000 € · Données mises à jour toutes les heures</p>
</div>
""", unsafe_allow_html=True)


# ── Métriques ──────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "📋 Annonces filtrées",
    f"{len(df):,}",
    delta=f"{len(df) - len(df_raw):+,}" if len(df) != len(df_raw) else None,
)
col2.metric(
    "💰 Prix médian",
    f"{df['valeur_fonciere'].median():,.0f} €" if not df.empty and df["valeur_fonciere"].notna().any() else "—",
)
col3.metric(
    "📐 Surface médiane",
    f"{df['surface_reelle_bati'].median():.0f} m²" if not df.empty and df["surface_reelle_bati"].notna().any() else "—",
)
col4.metric(
    "💶 Prix médian /m²",
    f"{df['prix_m2'].median():,.0f} €/m²" if not df.empty and df["prix_m2"].notna().any() else "—",
)

st.markdown("---")

# ── Graphiques ─────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### 📊 Distribution des prix")
    df_hist = df.dropna(subset=["valeur_fonciere"])
    if not df_hist.empty:
        fig = px.histogram(
            df_hist,
            x="valeur_fonciere",
            nbins=30,
            color="type_local",
            color_discrete_map={"Appartement": "#E8714A", "Maison": "#1B2B4B"},
            labels={"valeur_fonciere": "Prix (€)", "type_local": "Type", "count": "Nb annonces"},
            template="simple_white",
        )
        fig.update_layout(bargap=0.08, height=320, margin=dict(t=10, b=10), legend_title="Type")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas assez de données pour ce graphique.")

with col_right:
    st.markdown("#### 🔵 Prix vs Surface")
    df_sc = df.dropna(subset=["valeur_fonciere", "surface_reelle_bati"])
    if not df_sc.empty:
        fig2 = px.scatter(
            df_sc,
            x="surface_reelle_bati",
            y="valeur_fonciere",
            color="type_local",
            color_discrete_map={"Appartement": "#E8714A", "Maison": "#1B2B4B"},
            hover_data={
                "nom_commune": True,
                "nombre_pieces_principales": True,
                "source": True,
                "prix_m2": ":.0f",
            },
            labels={
                "surface_reelle_bati": "Surface (m²)",
                "valeur_fonciere": "Prix (€)",
                "type_local": "Type",
                "prix_m2": "€/m²",
            },
            template="simple_white",
            opacity=0.65,
        )
        fig2.update_layout(height=320, margin=dict(t=10, b=10), legend_title="Type")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Pas assez de données pour ce graphique.")

st.markdown("---")

# ── Tableau des annonces ───────────────────────────────────────────────────────
st.markdown(f"#### 📋 Annonces ({len(df):,} résultats)")

# Colonnes à afficher et leur label
COLS = {
    "source":                   "Source",
    "type_local":               "Type",
    "titre":                    "Titre",
    "valeur_fonciere":          "Prix (€)",
    "surface_reelle_bati":      "Surface (m²)",
    "nombre_pieces_principales":"Pièces",
    "prix_m2":                  "€/m²",
    "nom_commune":              "Commune",
    "code_postal":              "CP",
    "url":                      "Lien",
}

df_display = df[[c for c in COLS if c in df.columns]].copy()
df_display = df_display.rename(columns=COLS)
df_display = df_display.sort_values("Prix (€)", ascending=True)

# Formatage lisible
for col in ["Prix (€)", "€/m²"]:
    if col in df_display.columns:
        df_display[col] = df_display[col].apply(
            lambda x: f"{x:,.0f} €" if pd.notna(x) else "—"
        )
for col in ["Surface (m²)"]:
    if col in df_display.columns:
        df_display[col] = df_display[col].apply(
            lambda x: f"{x:.0f} m²" if pd.notna(x) else "—"
        )
for col in ["Pièces"]:
    if col in df_display.columns:
        df_display[col] = df_display[col].apply(
            lambda x: f"{int(x)}" if pd.notna(x) else "—"
        )

st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Lien": st.column_config.LinkColumn("Lien", display_text="🔗 Voir l'annonce"),
        "Titre": st.column_config.TextColumn("Titre", width="large"),
    },
    height=520,
)

# ── Source par site ────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 📡 Répartition par source")

if not df.empty and "source" in df.columns:
    src_counts = df["source"].value_counts().reset_index()
    src_counts.columns = ["Source", "Annonces"]
    fig3 = px.bar(
        src_counts,
        x="Source",
        y="Annonces",
        color="Source",
        color_discrete_sequence=["#E8714A", "#1B2B4B", "#27AE60"],
        template="simple_white",
        text="Annonces",
    )
    fig3.update_traces(textposition="outside")
    fig3.update_layout(height=280, margin=dict(t=10, b=10), showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)
