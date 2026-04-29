"""
routers/health.py — Endpoint /api/health
Vérifie l'état d'Ollama et des modèles configurés
"""

from fastapi import APIRouter
import httpx
import logging

from config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """
    Vérifie :
    - Connexion à Ollama
    - Disponibilité des modèles configurés
    - Stats de base
    """
    result = {
        "status": "ok",
        "ollama_url": settings.OLLAMA_BASE_URL,
        "main_model": settings.MAIN_MODEL,
        "extraction_model": settings.EXTRACTION_MODEL,
        "ollama_connected": False,
        "models_available": [],
        "main_model_ready": False,
        "extraction_model_ready": False,
        "errors": [],
    }

    # Test connexion Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if r.status_code == 200:
                data = r.json()
                result["ollama_connected"] = True
                result["models_available"] = [m["name"] for m in data.get("models", [])]

                # Vérifier les modèles configurés
                for model_key, model_name in [
                    ("main_model_ready", settings.MAIN_MODEL),
                    ("extraction_model_ready", settings.EXTRACTION_MODEL),
                ]:
                    base = model_name.split(":")[0]
                    found = any(base in m for m in result["models_available"])
                    result[model_key] = found
                    if not found:
                        result["errors"].append(
                            f"Modèle '{model_name}' non trouvé. Lance : ollama pull {model_name}"
                        )
            else:
                result["errors"].append(f"Ollama répond avec le statut {r.status_code}")
    except Exception as e:
        result["status"] = "degraded"
        result["errors"].append(f"Ollama non accessible : {str(e)}")

    if result["errors"]:
        result["status"] = "degraded"

    return result


@router.get("/health/models")
async def list_models():
    """Liste tous les modèles Ollama disponibles."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            return r.json()
    except Exception as e:
        return {"error": str(e), "models": []}
