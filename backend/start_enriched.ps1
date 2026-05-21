# ═══════════════════════════════════════════════════════════════════
# MACMIA Local avec RAG Enrichi — Script de démarrage Windows
# ═══════════════════════════════════════════════════════════════════

param(
    [switch]$Setup,      # Première installation complète
    [switch]$Ingest,     # Re-lancer l'ingestion
    [switch]$Enrich,     # Re-lancer l'enrichissement
    [switch]$Server      # Lancer uniquement le serveur (défaut)
)

$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND_DIR  = "$PROJECT_ROOT\backend"
$VENV_PYTHON  = "$PROJECT_ROOT\.venv\Scripts\python.exe"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════╗" -ForegroundColor Blue
Write-Host "║     MACMIA Local — RAG Enrichi v2        ║" -ForegroundColor Blue
Write-Host "╚═══════════════════════════════════════════╝" -ForegroundColor Blue
Write-Host ""

# ── Vérifier le venv ────────────────────────────────────────────────
if (-not (Test-Path $VENV_PYTHON)) {
    Write-Host "❌ Venv non trouvé. Lance d'abord :" -ForegroundColor Red
    Write-Host "   $env:LOCALAPPDATA\Python\bin\python.exe -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# ── Vérifier Ollama ──────────────────────────────────────────────────
try {
    $null = Invoke-RestMethod "http://localhost:11434/api/tags" -TimeoutSec 3
    Write-Host "✅ Ollama opérationnel" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Ollama non détecté — il tourne peut-être en arrière-plan" -ForegroundColor Yellow
}

Set-Location $BACKEND_DIR

# ── Mode SETUP complet (première fois) ──────────────────────────────
if ($Setup) {
    Write-Host "`n[1/5] Installation des dépendances..." -ForegroundColor Cyan
    & $VENV_PYTHON -m pip install -r requirements.txt -q

    Write-Host "`n[2/5] Création de la base SQLite enrichie..." -ForegroundColor Cyan
    & $VENV_PYTHON rag/db_schema.py

    Write-Host "`n[3/5] Chargement CSV CPF + données IMT vérifiées..." -ForegroundColor Cyan
    & $VENV_PYTHON rag/enrich.py --source csv
    & $VENV_PYTHON rag/enrich.py --source manual

    Write-Host "`n[4/5] Scraping France Compétences (200 RNCP, ~5 min)..." -ForegroundColor Cyan
    & $VENV_PYTHON rag/enrich.py --source scrape --limit 200 --delay 1.5

    Write-Host "`n[5/5] Complétion LLM pour les champs manquants..." -ForegroundColor Cyan
    & $VENV_PYTHON rag/enrich.py --source llm --limit 100
}

# ── Mode INGEST : re-indexer ChromaDB ───────────────────────────────
if ($Ingest -or $Setup) {
    Write-Host "`n🔢 Indexation ChromaDB enrichie..." -ForegroundColor Cyan
    & $VENV_PYTHON rag/ingest_enriched.py
}

# ── Mode ENRICH seul ────────────────────────────────────────────────
if ($Enrich -and -not $Setup) {
    Write-Host "`n📥 Re-enrichissement..." -ForegroundColor Cyan
    & $VENV_PYTHON rag/enrich.py --source manual
    & $VENV_PYTHON rag/enrich.py --source scrape --limit 100
    & $VENV_PYTHON rag/enrich.py --source llm --limit 50
}

# ── Lancement du serveur ─────────────────────────────────────────────
Write-Host ""
Write-Host "╔════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  🚀 MACMIA → http://localhost:8000             ║" -ForegroundColor Green
Write-Host "║  📊 RAG de base  → /api/rag/status             ║" -ForegroundColor Green
Write-Host "║  ⚡ RAG enrichi  → /api/rag/enriched/status    ║" -ForegroundColor Green
Write-Host "║  📖 API Docs     → http://localhost:8000/docs  ║" -ForegroundColor Green
Write-Host "║  Ctrl+C pour arrêter                          ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

& $VENV_PYTHON main.py
