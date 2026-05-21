from fastapi import APIRouter
from config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "llm": "Llama 3.1 8B — Tesla T4 GPU",
        "backend": "llama-cpp-python",
        "main_model": settings.MAIN_MODEL,
        "extraction_model": settings.EXTRACTION_MODEL,
    }

@router.get("/health/models")
async def health_models():
    return {"models": ["Meta-Llama-3.1-8B", "nomic-embed-text"]}
