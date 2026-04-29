"""
config.py — Configuration centrale MACMIA Local
Modifie le fichier .env pour choisir le fournisseur LLM.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── Fournisseur LLM ──────────────────────────────────────────────────────
    # "anthropic" → utilise Claude API (recommandé, meilleure qualité)
    # "ollama"    → utilise Ollama local (open-source, sans clé API)
    LLM_PROVIDER: str = "anthropic"

    # ── Anthropic Claude API ─────────────────────────────────────────────────
    # Clé API (obligatoire si LLM_PROVIDER = "anthropic")
    # Obtenir sur : https://console.anthropic.com/
    ANTHROPIC_API_KEY: str = ""

    # Modèle Claude à utiliser
    # Options : "claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # ── Ollama (si LLM_PROVIDER = "ollama") ──────────────────────────────────
    # URL de ton serveur Ollama (local ou distant)
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Modèle principal pour les recommandations et le chat
    # Recommandés (du plus léger au plus puissant) :
    #   - "mistral"            (7B  — bon équilibre vitesse/qualité, 4 Go VRAM)
    #   - "llama3.1"           (8B  — excellent en français, 5 Go VRAM)
    #   - "llama3.1:70b"       (70B — qualité max, nécessite 40+ Go VRAM)
    #   - "mixtral"            (8x7B MoE — très bon, 24 Go VRAM)
    #   - "qwen2.5"            (7B  — très bon en multilingue, 5 Go VRAM)
    #   - "gemma2"             (9B  — Google, bon en instruction following)
    MAIN_MODEL: str = "llama3.1"

    # Modèle léger pour l'extraction CV
    # Doit être rapide, la tâche est simple (extraction structurée)
    #   - "mistral"    (rapide, suffisant pour l'extraction)
    #   - "phi3"       (3.8B — très léger, parfait pour cette tâche)
    #   - "qwen2.5:3b" (3B   — ultra-léger)
    EXTRACTION_MODEL: str = "phi3"

    # ── Paramètres de génération ─────────────────────────────────────────────
    # Température : 0.0 = déterministe, 1.0 = créatif
    # Pour le JSON structuré, garder bas (0.1-0.3)
    MAIN_TEMPERATURE: float = 0.2
    EXTRACTION_TEMPERATURE: float = 0.1

    # Nombre max de tokens générés
    MAIN_MAX_TOKENS: int = 2500
    EXTRACTION_MAX_TOKENS: int = 400

    # ── Serveur ──────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True

    # ── Logs ─────────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "info"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instance globale
settings = Settings()


# ── Vérification au démarrage ────────────────────────────────────────────────
def check_ollama_connection():
    """Vérifie qu'Ollama est accessible au démarrage."""
    import httpx
    try:
        r = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        models = [m["name"] for m in r.json().get("models", [])]
        print(f"✅ Ollama connecté — Modèles disponibles : {models}")

        # Vérifier que les modèles configurés sont présents
        for model_name, model_key in [
            (settings.MAIN_MODEL, "MAIN_MODEL"),
            (settings.EXTRACTION_MODEL, "EXTRACTION_MODEL"),
        ]:
            # Ollama peut avoir le tag :latest implicite
            base = model_name.split(":")[0]
            found = any(base in m for m in models)
            if not found:
                print(f"⚠️  Modèle '{model_name}' ({model_key}) non trouvé.")
                print(f"   → Lance : ollama pull {model_name}")
            else:
                print(f"✅ Modèle '{model_name}' disponible.")

        return True
    except Exception as e:
        print(f"❌ Ollama non accessible sur {settings.OLLAMA_BASE_URL}")
        print(f"   Erreur : {e}")
        print(f"   → Lance : ollama serve")
        return False
