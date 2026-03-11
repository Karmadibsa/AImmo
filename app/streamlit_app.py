"""
Observatoire Immobilier AIMMO — Toulon ≤ 500 000 €
Dashboard professionnel — Marché immobilier toulonnais en temps réel
"""

import io

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── Config page ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NidDouillet by AImmo — Observatoire Immobilier Toulon",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #1E293B; }

/* ─── Fond général ─── */
.stApp { background: #F4F6FA; }

/* ══════════════════════════════════════════════════════════════════
   ZONE PRINCIPALE — couleur de texte par défaut (anti blanc-sur-blanc)
══════════════════════════════════════════════════════════════════ */
.main p, .main span:not([data-baseweb="tag"] span),
.main label, .main small,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span { color: #1E293B !important; }

/* Inputs, textareas, selects zone principale */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea { color: #1E293B !important; background: white !important; }

/* Selectbox zone principale */
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] [data-baseweb="select"] [data-baseweb="value"],
[data-testid="stSelectbox"] [data-baseweb="select"] input { color: #1E293B !important; background: white !important; }

/* Multiselect zone principale */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] input { color: #1E293B !important; background: white !important; }
[data-testid="stMultiSelect"] [data-baseweb="tag"] span { color: #1E293B !important; }

/* Radio boutons */
[data-testid="stRadio"] label, [data-testid="stRadio"] p { color: #1E293B !important; }

/* Expander */
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span { color: #1E293B !important; }

/* Texte dans les dataframes */
[data-testid="stDataFrame"] * { color: #1E293B; }

/* ══════════════════════════════════════════════════════════════════
   SIDEBAR — fond sombre, texte clair
══════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] { background: #1B2B4B !important; }

/* Texte courant sidebar — SANS div (trop large) */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #CBD5E1 !important; }

/* Titres sidebar */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #E8714A !important; }

/* Inputs sidebar — fond bleu foncé + texte clair */
[data-testid="stSidebar"] input { background: #253859 !important; color: #E2E8F0 !important; border-color: #3A5278 !important; }

/* Selectbox sidebar */
[data-testid="stSidebar"] [data-baseweb="select"] > div { background: #253859 !important; border-color: #3A5278 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] [data-baseweb="value"],
[data-testid="stSidebar"] [data-baseweb="select"] input { color: #E2E8F0 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] [data-baseweb="placeholder"] { color: #94A3B8 !important; }

/* Multiselect sidebar — tags */
[data-testid="stSidebar"] [data-baseweb="tag"] { background: #3A5278 !important; }
[data-testid="stSidebar"] [data-baseweb="tag"] span { color: #E2E8F0 !important; }

/* Slider sidebar */
[data-testid="stSidebar"] [data-testid="stTickBarMin"],
[data-testid="stSidebar"] [data-testid="stTickBarMax"] { color: #94A3B8 !important; }

/* ─── Header ─── */
.aimmo-header {
    background: linear-gradient(135deg, #1B2B4B 0%, #2C4A8A 100%);
    padding: 28px 32px;
    border-radius: 16px;
    margin-bottom: 28px;
    box-shadow: 0 6px 24px rgba(27,43,75,0.25);
}
.aimmo-header h1 { color: white; margin: 0 0 6px 0; font-size: 26px; font-weight: 700; letter-spacing: -0.3px; }
.aimmo-header .subtitle { color: #93B4D4; font-size: 13px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.aimmo-header .badge { background: rgba(255,255,255,0.12); padding: 3px 10px; border-radius: 20px; font-size: 12px; color: #BDD4EC; }

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
[data-testid="stMetricDelta"]  { color: #64748B !important; }

/* ══════════════════════════════════════════════════════════════════
   ONGLETS — 4 boutons pleine largeur + égaux
══════════════════════════════════════════════════════════════════ */
[data-baseweb="tab-list"] {
    display: flex !important;
    gap: 6px;
    background: white;
    padding: 8px 10px;
    border-radius: 14px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    margin-bottom: 28px;
}
[data-baseweb="tab"] {
    flex: 1 !important;
    justify-content: center !important;
    text-align: center !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    color: #64748B !important;
    padding: 10px 6px !important;
    transition: background 0.15s, color 0.15s !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: #1B2B4B !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(27,43,75,0.3) !important;
}

/* ─── Contenu onglets — padding généreux ─── */
[data-baseweb="tab-panel"] { padding-top: 4px !important; }
[data-baseweb="tab-panel"] > div:first-child { padding: 20px 8px 16px 8px !important; }

/* ─── Tags NLP ─── */
.tag { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; margin: 2px 2px 2px 0; }
.tag-blue   { background: #DBEAFE; color: #1D4ED8; }
.tag-green  { background: #DCFCE7; color: #16A34A; }
.tag-orange { background: #FEF3C7; color: #D97706; }
.tag-sea    { background: #CFFAFE; color: #0E7490; }

/* ─── Badge marché ─── */
.badge-opport  { background:#DCFCE7; color:#15803D; border:1px solid #86EFAC; font-weight:700; font-size:13px; padding:5px 14px; border-radius:8px; display:inline-block; }
.badge-bonne   { background:#D1FAE5; color:#065F46; border:1px solid #6EE7B7; font-weight:600; font-size:12px; padding:4px 12px; border-radius:8px; display:inline-block; }
.badge-normal  { background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE; font-weight:500; font-size:12px; padding:4px 12px; border-radius:8px; display:inline-block; }
.badge-eleve   { background:#FEF3C7; color:#B45309; border:1px solid #FDE68A; font-weight:600; font-size:12px; padding:4px 12px; border-radius:8px; display:inline-block; }

/* ─── Assistant conversationnel ─── */
.chat-wrap { max-width: 680px; margin: 0 auto; padding: 8px 0; }
.bot-bubble {
    background: white; border: 1px solid #E2E8F0;
    border-radius: 18px 18px 18px 4px; padding: 12px 18px;
    margin: 6px 0 10px 0; display: inline-block; max-width: 82%;
    font-size: 14px; color: #1E293B !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05); line-height: 1.5;
}
.user-bubble {
    background: linear-gradient(135deg, #1B2B4B, #2C4A8A);
    border-radius: 18px 18px 4px 18px; padding: 10px 18px;
    margin: 6px 0 10px auto; display: block; width: fit-content;
    margin-left: auto; font-size: 14px; color: white !important; font-weight: 500;
}
.result-card {
    background: white; border-radius: 12px; padding: 14px 18px;
    margin: 8px 0; border-left: 4px solid #E8714A;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.result-card b, .result-card span { color: #1E293B !important; }
.result-card.opport  { border-left-color: #16A34A; }
.result-card.bonne   { border-left-color: #22C55E; }
.result-card.normal  { border-left-color: #3B82F6; }
.result-card.eleve   { border-left-color: #F59E0B; }

/* ─── Section card ─── */
.section-card {
    background: white; border-radius: 14px; padding: 22px 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-bottom: 20px;
}
.section-card h4, .section-card p, .section-card span { color: #1E293B; }

/* ─── Prix badge ─── */
.prix-badge { background: #FFF7ED; border: 1px solid #FED7AA; color: #C2410C !important; font-weight: 700; padding: 4px 12px; border-radius: 8px; font-size: 15px; }
.pm2-badge  { background: #EFF6FF; border: 1px solid #BFDBFE; color: #1D4ED8 !important; font-size: 12px; padding: 2px 8px; border-radius: 6px; }

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

# ── Coefficients DVF Toulon (pré-calculés) ────────────────────────────────────
# Source : data/dvf_toulon.csv — ventes 2023-2025 (nature_mutation = Vente)
# Filtre appliqué : surface > 10 m², prix 10 000–500 000 €, Toulon uniquement
# Appartement : n=3 725, R²=0.141  |  Maison : n=393, R²=0.139
DVF_REGRESSION: dict[str, dict] = {
    "Appartement": {"slope": 1_661.0, "intercept":  76_761.0, "r2": 0.141, "n": 3_725},
    "Maison":      {"slope": 1_685.0, "intercept": 200_407.0, "r2": 0.139, "n":   393},
}

def extract_tags(description: str) -> list:
    if not isinstance(description, str):
        return []
    d = description.lower()
    return [(lbl, css) for lbl, (kws, css) in NLP_TAGS.items() if any(k in d for k in kws)]

def extract_tags(description: str) -> list:
    if not isinstance(description, str):
        return []
    d = description.lower()
    return [(lbl, css) for lbl, (kws, css) in NLP_TAGS.items() if any(k in d for k in kws)]


def tags_html(tags: list) -> str:
    return "".join(f'<span class="tag {css}">{lbl}</span>' for lbl, css in tags)


def market_badge_html(ecart_pct: float) -> str:
    """Retourne un badge HTML selon la classification marché (4 niveaux)."""
    if ecart_pct < -10:
        return f'<span class="badge-opport">🎯 OPPORTUNITÉ &nbsp;{ecart_pct:.0f}%</span>'
    elif ecart_pct < -5:
        return f'<span class="badge-bonne">✅ Bonne affaire &nbsp;{ecart_pct:.0f}%</span>'
    elif ecart_pct <= 5:
        return f'<span class="badge-normal">✅ Prix normal &nbsp;{ecart_pct:+.0f}%</span>'
    else:
        return f'<span class="badge-eleve">⚠️ Prix élevé &nbsp;{ecart_pct:+.0f}%</span>'


# ── Régression linéaire ─────────────────────────────────────────────────────────
def compute_regression(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Régression linéaire prix ~ surface par type de bien (pure pandas, sans numpy/scipy).
    Enrichit le DataFrame avec :
      - prix_predit : prix attendu selon la droite de régression
      - ecart       : prix réel − prix prédit (négatif = sous-évalué)
      - ecart_pct   : écart en % du prix prédit
      - _slope / _intercept : coefficients pour tracer la droite
    """
    results = []
    for ttype, grp in df_input.groupby("type_local"):
        grp = grp.dropna(subset=["valeur_fonciere", "surface_reelle_bati"]).copy()
        # Filtre les cas aberrants
        grp = grp[(grp["surface_reelle_bati"] > 10) & (grp["valeur_fonciere"] > 10_000)]
        if len(grp) < 2:
            for col in ["prix_predit", "ecart", "ecart_pct", "_slope", "_intercept"]:
                grp[col] = float("nan")
            results.append(grp)
            continue

        x, y  = grp["surface_reelle_bati"], grp["valeur_fonciere"]
        n      = len(x)
        denom  = n * (x ** 2).sum() - x.sum() ** 2

        if denom == 0:
            slope, intercept = 0.0, float(y.mean())
        else:
            slope     = (n * (x * y).sum() - x.sum() * y.sum()) / denom
            intercept = (y.sum() - slope * x.sum()) / n

        grp["_slope"]      = slope
        grp["_intercept"]  = intercept
        grp["prix_predit"] = (slope * x + intercept).round(0)
        grp["ecart"]       = (y - grp["prix_predit"]).round(0)
        grp["ecart_pct"]   = (grp["ecart"] / grp["prix_predit"] * 100).round(1)
        results.append(grp)

    if not results:
        return pd.DataFrame()
    return pd.concat(results, ignore_index=True)


def compute_dvf_scores(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Applique les coefficients DVF pré-calculés (dvf_toulon.csv — 4 118 ventes Toulon)
    à chaque annonce pour évaluer son écart vs le marché historique.

    Colonnes ajoutées :
      dvf_prix_predit  : prix attendu selon le modèle DVF
      dvf_ecart        : prix réel − dvf_prix_predit  (négatif = sous-évalué)
      dvf_ecart_pct    : écart en % (négatif = bonne affaire)
      _dvf_slope / _dvf_intercept : coefficients utilisés (pour tracer la droite)
    """
    df = df_input.copy()
    for col in ["dvf_prix_predit", "dvf_ecart", "dvf_ecart_pct",
                "_dvf_slope", "_dvf_intercept"]:
        df[col] = float("nan")

    for ttype, coef in DVF_REGRESSION.items():
        mask = (
            df["type_local"].eq(ttype)
            & df["surface_reelle_bati"].notna()
            & df["valeur_fonciere"].notna()
            & (df["surface_reelle_bati"] > 10)
            & (df["valeur_fonciere"] > 10_000)
        )
        if not mask.any():
            continue
        x = df.loc[mask, "surface_reelle_bati"]
        y = df.loc[mask, "valeur_fonciere"]
        predicted = (coef["slope"] * x + coef["intercept"]).round(0)
        df.loc[mask, "_dvf_slope"]      = coef["slope"]
        df.loc[mask, "_dvf_intercept"]  = coef["intercept"]
        df.loc[mask, "dvf_prix_predit"] = predicted
        df.loc[mask, "dvf_ecart"]       = (y - predicted).round(0)
        df.loc[mask, "dvf_ecart_pct"]   = ((y - predicted) / predicted * 100).round(1)

    return df


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

# ── Session state — Assistant conversationnel ──────────────────────────────────
for _k, _v in [("asst_step", 0), ("asst_type", None),
               ("asst_budget", None), ("asst_surface", None)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏠 NidDouillet")
    st.markdown(
        '<span style="color:#E8714A;font-size:13px;font-weight:600;letter-spacing:0.3px;">'
        'by AImmo</span>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    st.markdown("### 🎯 Filtres")

    types_dispo = sorted(df_raw["type_local"].dropna().unique()) if not df_raw.empty else []
    type_filtre = st.selectbox("Type de bien", ["Tous"] + list(types_dispo))

    budget_max = st.slider("Budget max (€)", 50_000, 500_000, 500_000, 10_000, format="%d €")

    # Filtre Quartier / Commune
    if not df_raw.empty and "nom_commune" in df_raw.columns:
        _quartiers_dispo = sorted(df_raw["nom_commune"].dropna().unique().tolist())
    else:
        _quartiers_dispo = []
    if _quartiers_dispo:
        quartier_filtre = st.multiselect(
            "📍 Quartier / Commune",
            options=_quartiers_dispo,
            default=[],
            placeholder="Tous les quartiers",
        )
    else:
        quartier_filtre = []

    surface_min = st.number_input("Surface min (m²)", 0, 300, 0, 5)
    pieces_min  = st.number_input("Pièces min",        0, 8,   0, 1)

    sources_dispo = sorted(df_raw["source"].dropna().unique()) if not df_raw.empty else []
    source_filtre = st.selectbox(
        "Source",
        ["Toutes"] + list(sources_dispo),
        help="Sources actives : PAP · LeBonCoin · SeLoger",
    )

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
if quartier_filtre and "nom_commune" in df.columns:
    df = df[df["nom_commune"].isin(quartier_filtre)]
if keyword:
    mask_kw = (
        df["description"].fillna("").str.contains(keyword, case=False) |
        df["titre"].fillna("").str.contains(keyword, case=False)
    )
    df = df[mask_kw]

# ── Régression (calculée une fois après filtrage) ────────────────────────────────
df_scored = compute_regression(df[df["type_local"].notna()].copy()) if not df.empty else pd.DataFrame()

# Rattacher ecart_pct/ecart/prix_predit à df (pour les fiches tab_liste)
if (not df_scored.empty and "ecart_pct" in df_scored.columns
        and "url" in df_scored.columns and "url" in df.columns):
    _reg_cols = df_scored[["url", "ecart_pct", "ecart", "prix_predit"]].dropna(subset=["url"])
    df = df.merge(_reg_cols, on="url", how="left", suffixes=("", "_reg"))

# DVF statique — coefficients pré-calculés sur dvf_toulon.csv (4 118 ventes Toulon)
df_dvf = (
    compute_dvf_scores(df[df["type_local"].notna()].copy())
    if not df.empty else pd.DataFrame()
)

# ── Header ─────────────────────────────────────────────────────────────────────
last_upd_str = "—"
if not df_raw.empty and "date_mutation" in df_raw.columns:
    lu = df_raw["date_mutation"].max()
    if pd.notna(lu):
        last_upd_str = lu.strftime("%d/%m/%Y à %H:%M")

st.markdown(f"""
<div class="aimmo-header">
  <h1>🏠 Observatoire Immobilier — Toulon — Temps réel</h1>
  <div class="subtitle">
    <span class="badge">≤ 500 000 €</span>
    <span class="badge">PAP · LeBonCoin · SeLoger</span>
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
tab_analyse, tab_liste, tab_opps, tab_asst = st.tabs([
    "📊  Marché",
    "📋  Liste des biens",
    "💡  Opportunités",
    "🤖  Assistant",
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYSE
# ════════════════════════════════════════════════════════════════════════════════
with tab_analyse:

    col_l, col_r = st.columns(2, gap="medium")

    # ── 1. Types de biens (Pie chart) ────────────────────────────────────────
    with col_l:
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
                height=280, margin=dict(t=10, b=10, l=0, r=0),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                paper_bgcolor="white",
            )
            fig4.update_traces(textinfo="percent+label", textfont_size=13)
            st.plotly_chart(fig4, use_container_width=True)
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

    # ── 3. Prix vs Surface (Scatter plot) ────────────────────────────────────
    with col_l2:
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

    # ── 4. Répartition par Sources (Bar chart) ───────────────────────────────
    with col_r2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 📡 Répartition par Sources")
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
                height=300, margin=dict(t=20, b=10, l=0, r=0),
                showlegend=False, paper_bgcolor="white", plot_bgcolor="white",
            )
            st.plotly_chart(fig3, use_container_width=True)
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
            ep_lst  = row.get("ecart_pct")   # disponible si merge réussi
            tags    = row.get("tags", [])
            source  = str(row.get("source", "")).upper()

            # Label expander — ajoute le badge marché si dispo
            lbl = titre
            if pd.notna(prix):    lbl += f"  ·  {prix:,.0f} €"
            if pd.notna(surface): lbl += f"  ·  {surface:.0f} m²"
            if pd.notna(ep_lst):
                ep_f = float(ep_lst)
                if ep_f < -10:   lbl += "  🎯"
                elif ep_f < -5:  lbl += "  ✅"
                elif ep_f > 10:  lbl += "  ⚠️"

            with st.expander(lbl):
                left, right = st.columns([1, 2], gap="medium")

                with left:
                    # Badge marché (classification 4 niveaux)
                    if pd.notna(ep_lst):
                        st.markdown(market_badge_html(float(ep_lst)), unsafe_allow_html=True)
                        prix_p  = row.get("prix_predit")
                        ecart_e = row.get("ecart")
                        if pd.notna(prix_p) and pd.notna(ecart_e):
                            st.caption(f"Prix attendu : {prix_p:,.0f} €  ·  Écart : {ecart_e:+,.0f} €")
                        st.markdown("")

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


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — OPPORTUNITÉS (régression linéaire prix ~ surface)
# ════════════════════════════════════════════════════════════════════════════════
with tab_opps:

    # ── Sélecteur de méthode ─────────────────────────────────────────────────
    col_meth, _ = st.columns([3, 2])
    with col_meth:
        methode = st.radio(
            "Référence d'évaluation",
            [
                "📚 DVF historique — 4 118 ventes Toulon",
                "📊 Dynamique — annonces actuelles",
            ],
            index=0,
            horizontal=True,
        )
    use_dvf = "DVF" in methode

    # ── Aliases selon la méthode ─────────────────────────────────────────────
    if use_dvf:
        _df_ref    = df_dvf
        _col_ep    = "dvf_ecart_pct"
        _col_e     = "dvf_ecart"
        _col_pp    = "dvf_prix_predit"
        _col_slope = "_dvf_slope"
        _col_inter = "_dvf_intercept"
    else:
        _df_ref    = df_scored
        _col_ep    = "ecart_pct"
        _col_e     = "ecart"
        _col_pp    = "prix_predit"
        _col_slope = "_slope"
        _col_inter = "_intercept"

    _ref_empty = _df_ref.empty or _col_ep not in _df_ref.columns

    if _ref_empty:
        st.info("😕 Pas assez de données pour calculer la régression.")
    else:
        # ── Boîte explication méthodo ─────────────────────────────────────────
        if use_dvf:
            _n_app   = DVF_REGRESSION["Appartement"]["n"]
            _n_mais  = DVF_REGRESSION["Maison"]["n"]
            _r2_app  = DVF_REGRESSION["Appartement"]["r2"]
            _r2_mais = DVF_REGRESSION["Maison"]["r2"]
            _sl_app  = DVF_REGRESSION["Appartement"]["slope"]
            _sl_mais = DVF_REGRESSION["Maison"]["slope"]
            st.markdown(f"""
            <div class="section-card" style="border-top-color:#8B5CF6;">
            <strong>📚 Référence DVF historique</strong> — Prix comparé aux
            <strong>{_n_app + _n_mais:,} ventes réelles</strong> enregistrées à Toulon
            (DVF 2023-2025, source DGFiP).<br>
            Modèles : Appartement = <b>{_sl_app:,.0f} €/m²</b> (n={_n_app:,}, R²={_r2_app})
            &nbsp;|&nbsp; Maison = <b>{_sl_mais:,.0f} €/m²</b> (n={_n_mais:,}, R²={_r2_mais})<br>
            <span style="color:#64748B;font-size:12px;">
            Coefficients fixes — robustes statistiquement, mais ne capturent pas les
            variations de prix récentes (données ≤ 3 mois).
            </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="section-card" style="border-top-color:#27AE60;">
            <strong>🔬 Régression dynamique</strong> — Pour chaque type de bien (Appartement / Maison),
            on calcule une droite de régression linéaire <em>Prix = a × Surface + b</em> à partir
            de toutes les annonces filtrées. L'<strong>écart</strong> = Prix réel − Prix prédit :
            un écart <span style="color:#16A34A;font-weight:600">négatif</span> signifie que le bien est
            <strong>moins cher que ce que le marché laisserait attendre</strong> pour sa surface.<br>
            <span style="color:#64748B;font-size:12px;">
            Sensible aux filtres — recalculée à chaque sélection. Moins robuste si peu d'annonces.
            </span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Opportunités = écart < -10 % ──────────────────────────────────────
        df_opps = _df_ref[_df_ref[_col_ep] < -10].sort_values(_col_ep)
        n_opps  = len(df_opps)

        econ_med = df_opps[_col_e].median() if n_opps > 0 else None
        best_row  = df_opps.iloc[0] if n_opps > 0 else None

        # ── KPIs ──────────────────────────────────────────────────────────────
        ko1, ko2, ko3 = st.columns(3)
        ko1.metric("🎯 Opportunités détectées",
                   f"{n_opps}",
                   delta=f"écart > 10 % sous le marché")
        if best_row is not None and pd.notna(best_row[_col_ep]):
            ko2.metric("🏆 Meilleure affaire",
                       f"{best_row[_col_ep]:.1f} %",
                       delta=f"{best_row[_col_e]:,.0f} € sous le marché")
        else:
            ko2.metric("🏆 Meilleure affaire", "—")
        ko3.metric("💰 Économie médiane",
                   f"{abs(econ_med):,.0f} €" if econ_med else "—",
                   delta="par rapport au prix attendu")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Scatter prix vs surface + droite de régression ─────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### 📈 Prix vs Surface — avec droite de régression")

        COLORS_TYPE = {"Appartement": "#E8714A", "Maison": "#1B2B4B"}
        fig_reg = go.Figure()

        for ttype, grp in _df_ref.groupby("type_local"):
            c = COLORS_TYPE.get(ttype, "#8B5CF6")
            grp_valid = grp.dropna(subset=[_col_slope, _col_inter,
                                            "surface_reelle_bati", "valeur_fonciere"])
            if grp_valid.empty:
                continue

            # Points — couleur selon sur/sous-évaluation
            fig_reg.add_trace(go.Scatter(
                x=grp_valid["surface_reelle_bati"].tolist(),
                y=grp_valid["valeur_fonciere"].tolist(),
                mode="markers",
                name=ttype,
                marker=dict(
                    color=grp_valid[_col_ep].tolist(),
                    colorscale="RdYlGn_r",
                    cmin=-30, cmax=30,
                    size=8,
                    opacity=0.75,
                    line=dict(width=0),
                    showscale=False,
                ),
                text=grp_valid["titre"].fillna("").tolist(),
                customdata=list(zip(
                    grp_valid[_col_ep].tolist(),
                    grp_valid[_col_e].fillna(0).tolist(),
                    grp_valid[_col_pp].fillna(0).tolist(),
                )),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Surface : %{x:.0f} m²<br>"
                    "Prix réel : %{y:,.0f} €<br>"
                    "Prix attendu : %{customdata[2]:,.0f} €<br>"
                    "Écart : <b>%{customdata[0]:.1f} %</b> (%{customdata[1]:+,.0f} €)"
                    "<extra>" + ttype + "</extra>"
                ),
            ))

            # Droite de régression
            slope     = float(grp_valid[_col_slope].iloc[0])
            intercept = float(grp_valid[_col_inter].iloc[0])
            x_min     = float(grp_valid["surface_reelle_bati"].min())
            x_max     = float(grp_valid["surface_reelle_bati"].max())
            fig_reg.add_trace(go.Scatter(
                x=[x_min, x_max],
                y=[slope * x_min + intercept, slope * x_max + intercept],
                mode="lines",
                name=f"Tendance {ttype}" + (" (DVF)" if use_dvf else ""),
                line=dict(color=c, width=2, dash="dash"),
            ))

        # Colorbar légende
        fig_reg.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(
                colorscale="RdYlGn_r", cmin=-30, cmax=30,
                color=[0], showscale=True,
                colorbar=dict(
                    title="Écart (%)",
                    tickvals=[-30, -15, 0, 15, 30],
                    ticktext=["-30 %", "-15 %", "0 %", "+15 %", "+30 %"],
                    thickness=12, len=0.6,
                ),
            ),
            showlegend=False,
        ))

        fig_reg.update_layout(
            height=380, margin=dict(t=10, b=10, l=0, r=0),
            paper_bgcolor="white", plot_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
            xaxis_title="Surface (m²)", yaxis_title="Prix (€)",
        )
        fig_reg.update_yaxes(tickformat=",.0f", ticksuffix=" €")
        st.plotly_chart(fig_reg, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Graphique top 15 + tableau ─────────────────────────────────────────
        col_bar, col_tbl = st.columns([1, 1], gap="large")

        with col_bar:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown("#### 🏅 Top 15 meilleures affaires")
            top15 = df_opps.head(15).copy()
            if not top15.empty:
                top15["label"] = (
                    top15["titre"].fillna("Annonce").str[:35] + "…"
                )
                fig_bar = px.bar(
                    top15,
                    x=_col_ep,
                    y="label",
                    orientation="h",
                    color=_col_ep,
                    color_continuous_scale="RdYlGn_r",
                    range_color=[-40, 0],
                    text=top15[_col_ep].apply(lambda v: f"{v:.1f} %"),
                    labels={_col_ep: "Écart (%)", "label": ""},
                    template="simple_white",
                )
                fig_bar.update_traces(textposition="outside")
                fig_bar.update_layout(
                    height=420, margin=dict(t=10, b=10, l=0, r=10),
                    paper_bgcolor="white", plot_bgcolor="white",
                    showlegend=False, coloraxis_showscale=False,
                    yaxis=dict(autorange="reversed"),
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Aucune opportunité détectée avec les filtres actuels.")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_tbl:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown("#### 📋 Tableau des opportunités")
            if not df_opps.empty:
                COLS_OPP = {
                    "titre":               "Titre",
                    "type_local":          "Type",
                    "valeur_fonciere":     "Prix réel (€)",
                    _col_pp:               "Prix attendu (€)",
                    _col_e:                "Économie (€)",
                    _col_ep:               "Écart (%)",
                    "surface_reelle_bati": "Surface (m²)",
                    "url":                 "Lien",
                }
                df_tbl = df_opps[[c for c in COLS_OPP if c in df_opps.columns]].copy()
                df_tbl = df_tbl.rename(columns=COLS_OPP)

                st.dataframe(
                    df_tbl,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Lien":           st.column_config.LinkColumn("Lien", display_text="🔗 Voir"),
                        "Titre":          st.column_config.TextColumn("Titre", width="medium"),
                        "Prix réel (€)":  st.column_config.NumberColumn(format="%.0f €"),
                        "Prix attendu (€)": st.column_config.NumberColumn(format="%.0f €"),
                        "Économie (€)":   st.column_config.NumberColumn(format="%.0f €"),
                        "Écart (%)":      st.column_config.NumberColumn(format="%.1f %%"),
                        "Surface (m²)":   st.column_config.NumberColumn(format="%.0f m²"),
                    },
                    height=420,
                )
            else:
                st.info("Aucune opportunité pour les filtres actuels.")
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Fiches des top opportunités ─────────────────────────────────────────
        # ── Export ────────────────────────────────────────────────────────────
        if not df_opps.empty:
            st.markdown("---")
            st.markdown("#### 📥 Exporter les opportunités du jour")
            _export_cols = {
                "titre":               "Titre",
                "type_local":          "Type",
                "valeur_fonciere":     "Prix réel (€)",
                _col_pp:               "Prix attendu (€)",
                _col_e:                "Économie (€)",
                _col_ep:               "Écart (%)",
                "surface_reelle_bati": "Surface (m²)",
                "nombre_pieces_principales": "Pièces",
                "nom_commune":         "Commune",
                "source":              "Source",
                "url":                 "Lien",
            }
            _df_export = (
                df_opps[[c for c in _export_cols if c in df_opps.columns]]
                .copy()
                .rename(columns=_export_cols)
            )
            _fname_base = f"opportunites_toulon_{pd.Timestamp.today().strftime('%Y%m%d')}"

            _col_ex1, _col_ex2, _ = st.columns([1, 1, 3])

            with _col_ex1:
                _buf = io.BytesIO()
                _df_export.to_excel(_buf, index=False, engine="openpyxl")
                st.download_button(
                    label="📊 Télécharger Excel",
                    data=_buf.getvalue(),
                    file_name=f"{_fname_base}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            with _col_ex2:
                _csv_bytes = _df_export.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="📄 Télécharger CSV",
                    data=_csv_bytes,
                    file_name=f"{_fname_base}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

        # ── Fiches détaillées ─────────────────────────────────────────────────
        if not df_opps.empty:
            st.markdown("---")
            st.markdown("#### 🔍 Fiches détaillées — Meilleures opportunités")
            for _, row in df_opps.head(20).iterrows():
                titre   = str(row.get("titre", "Annonce sans titre"))
                prix    = row.get("valeur_fonciere")
                surface = row.get("surface_reelle_bati")
                pm2     = row.get("prix_m2")
                ecart_p = row.get(_col_ep)
                ecart_e = row.get(_col_e)
                tags    = row.get("tags", [])
                source  = str(row.get("source", "")).upper()

                lbl = titre
                if pd.notna(prix):    lbl += f"  ·  {prix:,.0f} €"
                if pd.notna(surface): lbl += f"  ·  {surface:.0f} m²"
                if pd.notna(ecart_p): lbl += f"  ·  🟢 {ecart_p:.1f} %"

                with st.expander(lbl):
                    left, right = st.columns([1, 2], gap="medium")

                    with left:
                        # Badge marché 4 niveaux
                        if pd.notna(ecart_p):
                            st.markdown(market_badge_html(float(ecart_p)), unsafe_allow_html=True)
                            if pd.notna(ecart_e):
                                prix_p = row.get(_col_pp)
                                st.markdown(
                                    f'<div style="background:#F0FDF4;border:1px solid #BBF7D0;'
                                    f'border-radius:8px;padding:6px 12px;margin:6px 0;">'
                                    f'<span style="color:#475569;font-size:12px;">'
                                    f'Prix attendu : <b>{prix_p:,.0f} €</b><br>'
                                    f'💰 Économie : <b>{abs(ecart_e):,.0f} €</b></span></div>',
                                    unsafe_allow_html=True,
                                )
                            st.markdown("")

                        if pd.notna(prix):
                            st.markdown(
                                f'<span class="prix-badge">{prix:,.0f} €</span>'
                                + (f' <span class="pm2-badge">{pm2:,.0f} €/m²</span>'
                                   if pd.notna(pm2) else ""),
                                unsafe_allow_html=True,
                            )
                            st.markdown("")

                        info_lines = [
                            ("🏷️ Source",  source),
                            ("🏠 Type",    row.get("type_local", "—")),
                            ("📐 Surface", f"{surface:.0f} m²" if pd.notna(surface) else "—"),
                            ("🚪 Pièces",  f"{int(row['nombre_pieces_principales'])}"
                             if pd.notna(row.get("nombre_pieces_principales")) else "—"),
                            ("📍 Commune", row.get("nom_commune", "—")),
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


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — ASSISTANT CONVERSATIONNEL (wizard rule-based)
# ════════════════════════════════════════════════════════════════════════════════
with tab_asst:

    # ── Helpers bulles ──────────────────────────────────────────────────────────
    def bot(text: str) -> None:
        st.markdown(f'<div class="bot-bubble">🤖 {text}</div>', unsafe_allow_html=True)

    def usr(text: str) -> None:
        st.markdown(f'<div class="user-bubble">{text}</div>', unsafe_allow_html=True)

    # ── Conteneur centré ────────────────────────────────────────────────────────
    _, center, _ = st.columns([1, 3, 1])

    with center:
        st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)

        # ── MESSAGE D'ACCUEIL (toujours visible) ────────────────────────────────
        bot("Bonjour ! Je suis votre assistant AIMMO. 👋")
        bot("Je vais vous aider à trouver les <b>meilleures opportunités</b> "
            "sur le marché toulonnais selon vos critères.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ════════════ ÉTAPE 0 — TYPE DE BIEN ════════════════════════════════════
        bot("Vous cherchez quel type de bien ?")

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

        # ════════════ ÉTAPE 1+ — BUDGET ═════════════════════════════════════════
        if st.session_state.asst_step >= 1:
            usr(f"{'🏢 Appartement' if st.session_state.asst_type == 'Appartement' else '🏡 Maison'}")
            st.markdown("<br>", unsafe_allow_html=True)
            bot("Quel est votre <b>budget maximum</b> ?")

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

        # ════════════ ÉTAPE 2+ — SURFACE ════════════════════════════════════════
        if st.session_state.asst_step >= 2:
            _bud_lbl = {200_000: "< 200 000 €", 300_000: "200–300 000 €",
                        400_000: "300–400 000 €", 500_000: "≤ 500 000 €"}
            usr(f"💶 {_bud_lbl.get(st.session_state.asst_budget, '')}")
            st.markdown("<br>", unsafe_allow_html=True)
            bot("Quelle <b>surface minimum</b> vous faut-il ?")

            if st.session_state.asst_step == 2:
                _surfaces = [
                    ("📐 Peu importe",  0),
                    ("📐 ≥ 30 m²",     30),
                    ("📐 ≥ 50 m²",     50),
                    ("📐 ≥ 70 m²",     70),
                ]
                cols = st.columns(2)
                for i, (lbl, val) in enumerate(_surfaces):
                    if cols[i % 2].button(lbl, key=f"asst_surf_{i}", use_container_width=True):
                        st.session_state.asst_surface = val
                        st.session_state.asst_step = 3
                        st.rerun()

        # ════════════ ÉTAPE 3 — RÉSULTATS ═══════════════════════════════════════
        if st.session_state.asst_step >= 3:
            _surf_lbl = {0: "Peu importe", 30: "≥ 30 m²", 50: "≥ 50 m²", 70: "≥ 70 m²"}
            usr(f"📐 {_surf_lbl.get(st.session_state.asst_surface, '')}")
            st.markdown("<br>", unsafe_allow_html=True)

            # ── Filtrage sur df_scored ────────────────────────────────────────
            _t  = st.session_state.asst_type
            _b  = st.session_state.asst_budget
            _s  = st.session_state.asst_surface

            if df_scored.empty or "ecart_pct" not in df_scored.columns:
                bot("😕 Pas assez de données pour la régression. Réessayez après le prochain scraping.")
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
                    bot(f"😕 Aucune annonce ne correspond à ces critères. "
                        f"Essayez d'élargir votre budget ou surface.")
                else:
                    bot(f"J'ai trouvé <b>{n_res} bien(s)</b> correspondant à votre recherche, "
                        f"dont <b>{n_opp} opportunité(s)</b> sous-évaluée(s) par le marché. 👇")

                    # ── Résultats ─────────────────────────────────────────────
                    st.markdown("<br>", unsafe_allow_html=True)
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

                        # Classe CSS carte selon badge
                        if pd.notna(ecart_p):
                            ep = float(ecart_p)
                            card_cls = ("opport" if ep < -10 else
                                        "bonne"  if ep < -5  else
                                        "normal" if ep <= 5  else "eleve")
                        else:
                            card_cls = "normal"

                        # Titre de la carte
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
                                    st.markdown(
                                        market_badge_html(float(ecart_p)),
                                        unsafe_allow_html=True,
                                    )
                                if pd.notna(prix_p) and pd.notna(ecart_e):
                                    st.caption(
                                        f"Prix attendu : {prix_p:,.0f} €  ·  "
                                        f"Économie : {abs(ecart_e):,.0f} €"
                                    )
                                if pd.notna(prix):
                                    st.markdown(
                                        f'<span class="prix-badge">{prix:,.0f} €</span>'
                                        + (f' <span class="pm2-badge">{pm2:,.0f} €/m²</span>'
                                           if pd.notna(pm2) else ""),
                                        unsafe_allow_html=True,
                                    )
                                st.markdown("")
                                for icon_lbl, val in [
                                    ("🏷️ Source",  str(row.get("source", "")).upper()),
                                    ("📐 Surface", surface_str),
                                    ("🚪 Pièces",  f"{int(row['nombre_pieces_principales'])}"
                                     if pd.notna(row.get("nombre_pieces_principales")) else "—"),
                                    ("📍 Commune", row.get("nom_commune", "—")),
                                ]:
                                    st.markdown(f"**{icon_lbl}** : {val}")
                                if pd.notna(url) and url:
                                    st.markdown(
                                        f"<br>[🔗 Voir l'annonce →]({url})",
                                        unsafe_allow_html=True,
                                    )
                            with right:
                                if tags:
                                    st.markdown(tags_html(tags), unsafe_allow_html=True)
                                    st.markdown("<br>", unsafe_allow_html=True)
                                desc = str(row.get("description", "")).strip()
                                if desc and desc != "nan":
                                    st.markdown(
                                        f"<small style='color:#475569;line-height:1.6'>"
                                        f"{desc[:600]}{'…' if len(desc) > 600 else ''}"
                                        f"</small>",
                                        unsafe_allow_html=True,
                                    )
                                else:
                                    st.caption("Pas de description disponible.")

                    if n_res > 15:
                        bot(f"… et {n_res - 15} autre(s) bien(s). "
                            f"Affinez vos critères pour voir moins de résultats.")

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Bouton reset ─────────────────────────────────────────────────
            if st.button("🔄 Nouvelle recherche", use_container_width=False, key="asst_reset"):
                st.session_state.asst_step    = 0
                st.session_state.asst_type    = None
                st.session_state.asst_budget  = None
                st.session_state.asst_surface = None
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
