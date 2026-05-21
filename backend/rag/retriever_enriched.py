"""
rag/retriever_enriched.py — Recherche dans la base ChromaDB enrichie
Remplace retriever.py : utilise chroma_db_enriched + métadonnées riches.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

CHROMA_DIR  = str(Path(__file__).parent.parent / "chroma_db_enriched")
EMBED_MODEL = "nomic-embed-text"
COLLECTION  = "macmia_formations_enriched"

_db = None


def get_db():
    global _db
    if _db is not None:
        return _db
    if not os.path.exists(CHROMA_DIR):
        logger.warning(f"ChromaDB enrichi introuvable : {CHROMA_DIR}")
        return None
    try:
        from langchain_chroma import Chroma
        from langchain_ollama import OllamaEmbeddings
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from config import settings

        embeddings = OllamaEmbeddings(model=EMBED_MODEL,
                                      base_url=settings.OLLAMA_BASE_URL)
        _db = Chroma(persist_directory=CHROMA_DIR,
                     embedding_function=embeddings,
                     collection_name=COLLECTION)
        count = _db._collection.count()
        logger.info(f"✅ ChromaDB enrichi chargé — {count:,} formations")
        return _db
    except Exception as e:
        logger.error(f"Erreur chargement ChromaDB enrichi : {e}")
        return None


def is_ready() -> bool:
    return os.path.exists(CHROMA_DIR) and get_db() is not None


def search_formations(
    query: str,
    region: Optional[str] = None,
    cpf_only: bool = False,
    niveau: Optional[str] = None,
    modalite: Optional[str] = None,   # Présentiel / Distanciel / Hybride
    prix_max: Optional[int] = None,   # Prix maximum en euros
    top_k: int = 5,
) -> list[Document]:
    """
    Recherche sémantique enrichie avec filtres sur modalité, prix, région, niveau.
    """
    db = get_db()
    if db is None:
        return []

    filters = []

    if region:
        filters.append({"region": {"$contains": region}})
    if cpf_only:
        filters.append({"cpf": {"$in": ["oui", "Oui", "true", "True", "1"]}})
    if niveau:
        niv = niveau.strip().upper()
        if not niv.startswith("NIVEAU"):
            niv = f"NIVEAU {niv}"
        filters.append({"niveau": {"$contains": niv}})
    if modalite:
        filters.append({"modalite": {"$eq": modalite}})

    kwargs = {"k": top_k}
    if len(filters) == 1:
        kwargs["filter"] = filters[0]
    elif len(filters) > 1:
        kwargs["filter"] = {"$and": filters}

    try:
        results = db.similarity_search(query, **kwargs)
        # Filtre prix côté Python (ChromaDB ne supporte pas $lte sur string)
        if prix_max and results:
            filtered = []
            for doc in results:
                prix_min_str = doc.metadata.get("prix_min", "")
                try:
                    if int(prix_min_str) <= prix_max:
                        filtered.append(doc)
                except (ValueError, TypeError):
                    filtered.append(doc)  # On garde si prix inconnu
            results = filtered
        return results
    except Exception as e:
        logger.warning(f"Recherche enrichie échouée ({e}), fallback sans filtre")
        try:
            return db.similarity_search(query, k=top_k)
        except Exception as e2:
            logger.error(f"Recherche vectorielle échouée : {e2}")
            return []


def format_context_enriched(docs: list[Document]) -> str:
    """Formate les résultats enrichis pour le prompt LLM."""
    if not docs:
        return "Aucune formation trouvée dans la base enrichie pour cette requête."

    lines = ["=== FORMATIONS CPF ENRICHIES (data.gouv.fr + France Compétences) ===\n"]
    for i, doc in enumerate(docs, 1):
        m = doc.metadata
        # Ajouter les liens si disponibles
        liens = []
        if m.get("lien_catalogue") and m["lien_catalogue"] != "":
            liens.append(f"Catalogue : {m['lien_catalogue']}")
        if m.get("lien_france_comp") and m["lien_france_comp"] != "":
            liens.append(f"France Compétences : {m['lien_france_comp']}")

        content = doc.page_content
        if liens:
            content += "\n" + "\n".join(liens)

        lines.append(f"[Formation #{i} — Fiabilité {m.get('fiabilite','?')}/4]\n{content}\n{'─'*50}")
    return "\n".join(lines)


def get_stats() -> dict:
    if not os.path.exists(CHROMA_DIR):
        return {"ready": False,
                "message": "Base enrichie non indexée — lance python rag/ingest_enriched.py"}
    db = get_db()
    if db is None:
        return {"ready": False, "message": "Erreur chargement ChromaDB enrichi"}
    try:
        count = db._collection.count()
        return {
            "ready": True,
            "formations_indexed": count,
            "embed_model": EMBED_MODEL,
            "chroma_dir": CHROMA_DIR,
            "collection": COLLECTION,
            "type": "enriched",
        }
    except Exception as e:
        return {"ready": False, "message": str(e)}
