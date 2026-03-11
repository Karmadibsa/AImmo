# ============================================================
#  AIMMO — Scraping automatique + push GitHub
#  Lancer via Windows Task Scheduler (toutes les X heures)
#  Prérequis : Docker Desktop lancé, git configuré
# ============================================================

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile    = "$ProjectDir\scrape_and_push.log"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $msg" | Tee-Object -FilePath $LogFile -Append
}

Log "========== DEBUT SCRAPING =========="
Set-Location $ProjectDir

# ── 1. Démarre FlareSolverr si pas déjà actif ───────────────
Log "Verification FlareSolverr..."
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:8191/health" -TimeoutSec 3 -ErrorAction Stop
    Log "FlareSolverr deja actif (status: $($resp.StatusCode))"
} catch {
    Log "Demarrage FlareSolverr via Docker..."
    docker compose up flaresolverr -d 2>&1 | Out-File -Append $LogFile
    Start-Sleep -Seconds 15   # laisse le temps de démarrer
    Log "FlareSolverr demarre"
}

# ── 2. Lance le scraping ─────────────────────────────────────
Log "Lancement du scraping..."
$env:PYTHONIOENCODING = "utf-8"
try {
    python -m scraping.run_scraping 2>&1 | Tee-Object -FilePath $LogFile -Append
    Log "Scraping termine"
} catch {
    Log "ERREUR scraping: $_"
    exit 1
}

# ── 3. Compte les annonces récupérées ───────────────────────
$csv = "$ProjectDir\data\annonces.csv"
if (Test-Path $csv) {
    $lines = (Get-Content $csv | Measure-Object -Line).Lines - 1
    Log "$lines annonces dans annonces.csv"
} else {
    Log "ERREUR: annonces.csv introuvable"
    exit 1
}

# ── 4. Commit + push si le CSV a changé ─────────────────────
Log "Verification des changements git..."
$status = git status --porcelain data/annonces.csv
if ($status) {
    Log "CSV modifie, commit + push..."

    git add data/annonces.csv 2>&1 | Out-File -Append $LogFile

    $msg = "chore(data): $lines annonces mises a jour [skip ci]"
    git commit -m $msg 2>&1 | Out-File -Append $LogFile

    # Push sur les deux remotes
    git push origin feat/axel-verification 2>&1 | Out-File -Append $LogFile
    Log "Pousse sur origin (classroom) OK"

    git push fork feat/axel-verification 2>&1 | Out-File -Append $LogFile
    Log "Pousse sur fork (perso) OK"

    Log "Streamlit se mettra a jour dans ~5 min (cache TTL)"
} else {
    Log "Pas de changement dans annonces.csv, rien a pusher"
}

Log "========== FIN =========="
