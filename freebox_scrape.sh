#!/bin/bash
# ============================================================
#  AIMMO — Scraping automatique sur Freebox Ultra
#  Lancer via cron toutes les 2h (IP résidentielle Free)
#
#  Prérequis :
#    - Python3 + venv installé dans /opt/aimmo/venv
#    - Docker installé (pour FlareSolverr)
#    - git configuré avec token GitHub
#
#  Installation cron :
#    crontab -e
#    0 */2 * * * /opt/aimmo/freebox_scrape.sh >> /opt/aimmo/cron.log 2>&1
# ============================================================

set -e

PROJECT_DIR="/opt/aimmo"
VENV="$PROJECT_DIR/venv"
LOG="$PROJECT_DIR/scrape.log"
BRANCH="feat/axel-verification"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"; }

log "========== DEBUT SCRAPING =========="
cd "$PROJECT_DIR"

# ── 1. Pull les derniers changements de code ─────────────────
log "Git pull..."
git fetch origin "$BRANCH" 2>&1 | tee -a "$LOG"
git checkout "$BRANCH" 2>&1 | tee -a "$LOG"
git merge "origin/$BRANCH" --no-edit 2>&1 | tee -a "$LOG" || true

# ── 2. Démarre FlareSolverr si pas actif ─────────────────────
log "Vérification FlareSolverr..."
if ! curl -sf http://localhost:8191/health > /dev/null 2>&1; then
    log "Démarrage FlareSolverr..."
    docker run -d \
        --name flaresolverr \
        --restart unless-stopped \
        -p 8191:8191 \
        ghcr.io/flaresolverr/flaresolverr:latest 2>&1 | tee -a "$LOG" || \
    docker start flaresolverr 2>&1 | tee -a "$LOG" || true
    sleep 20
    log "FlareSolverr prêt"
else
    log "FlareSolverr déjà actif"
fi

# ── 3. Lance le scraping ─────────────────────────────────────
log "Lancement du scraping (IP résidentielle Free)..."
source "$VENV/bin/activate"
python3 -m scraping.run_scraping 2>&1 | tee -a "$LOG"
log "Scraping terminé"

# ── 4. Compte les annonces ───────────────────────────────────
if [ -f "$PROJECT_DIR/data/annonces.csv" ]; then
    N=$(( $(wc -l < "$PROJECT_DIR/data/annonces.csv") - 1 ))
    log "$N annonces dans annonces.csv"
else
    log "ERREUR: annonces.csv introuvable"
    exit 1
fi

# ── 5. Commit + push si changement ───────────────────────────
if ! git diff --quiet data/annonces.csv; then
    log "CSV modifié — commit + push..."
    git add data/annonces.csv
    git commit -m "chore(data): $N annonces mises à jour [skip ci]"
    git push origin "$BRANCH"
    log "Pushé sur GitHub ✓ — Streamlit se mettra à jour dans ~5min"
else
    log "Pas de changement, rien à pusher"
fi

log "========== FIN =========="
