"""
MACMIA Chatbot — Backend Local
FastAPI + LangChain + Ollama
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import os

from routers import chat, cv, health, skills, rncp, rag_chat, rag_enriched

# ── Application ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="MACMIA Chatbot Local",
    description="Backend LangChain + Ollama pour le chatbot MACMIA",
    version="1.0.0"
)

# ── CORS (autoriser le frontend HTML servi localement) ───────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # En prod, restreindre à l'IP du serveur
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(chat.router,   prefix="/api", tags=["Chat"])
app.include_router(cv.router,     prefix="/api", tags=["CV"])
app.include_router(skills.router,  prefix="/api", tags=["Skills"])
app.include_router(rncp.router,    prefix="/api", tags=["RNCP"])
app.include_router(rag_chat.router,      prefix="/api", tags=["RAG"])
app.include_router(rag_enriched.router, prefix="/api", tags=["RAG Enrichi"])

# ── Servir le frontend statique ──────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# ── Lancement ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
