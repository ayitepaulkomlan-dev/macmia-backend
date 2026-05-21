"""
routers/rag_enriched.py — Endpoints RAG enrichi
POST /api/rag/enriched/chat   → Chat enrichi avec base SQLite + ChromaDB enrichi
GET  /api/rag/enriched/status → État de la base enrichie
GET  /api/rag/enriched/search → Recherche avec filtres modalité, prix
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from langchain_core.messages import SystemMessage

from llm_chain import llm_main, parse_json_response, history_to_langchain
from llm_chain import build_system_prompt
from rag.retriever_enriched import (
    search_formations, format_context_enriched, get_stats, is_ready
)

router  = APIRouter()
logger  = logging.getLogger(__name__)


class EnrichedChatRequest(BaseModel):
    messages:  list[dict]
    cv_text:   Optional[str] = None
    region:    Optional[str] = None
    modalite:  Optional[str] = None   # Présentiel / Distanciel / Hybride
    cpf_only:  bool = False
    niveau:    Optional[str] = None   # "6", "7", "NIVEAU 6"
    prix_max:  Optional[int] = None   # Budget max en euros
    top_k:     int = 5


@router.post("/rag/enriched/chat")
async def enriched_chat(request: EnrichedChatRequest):
    """
    Chat RAG avec base enrichie — blocs compétences + métiers + prix + liens.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages vides")

    last_user = next(
    (m.content for m in reversed(request.messages) if m.role == "user"), "")

    # Recherche vectorielle enrichie
    rag_docs = []
    if is_ready():
        rag_docs = search_formations(
            query=last_user,
            region=request.region,
            cpf_only=request.cpf_only,
            niveau=request.niveau,
            modalite=request.modalite,
            prix_max=request.prix_max,
            top_k=request.top_k,
        )
        logger.info(f"RAG enrichi : {len(rag_docs)} formations pour '{last_user[:60]}'")

    # Prompt enrichi
    base_system = build_system_prompt()
    if rag_docs:
        rag_context = format_context_enriched(rag_docs)
        extra = f"""

════════════════════════════════════════════════════════
📊 BASE ENRICHIE — Formations avec blocs compétences + métiers + prix
    Source : data.gouv.fr + France Compétences + vérification manuelle
════════════════════════════════════════════════════════
INSTRUCTIONS SPÉCIALES :
- Cite les blocs de compétences développées pour chaque formation
- Mentionne les métiers accessibles après la formation
- Indique le prix et la modalité (Présentiel/Distanciel/Hybride)
- Fournis les liens catalogue quand disponibles
- Indique le niveau de fiabilité (4/4 = données vérifiées)

{rag_context}
════════════════════════════════════════════════════════
"""
        system_prompt = base_system + extra
    else:
        system_prompt = base_system

    lc_history = history_to_langchain(request.messages)
    messages   = [SystemMessage(content=system_prompt)] + lc_history

    try:
        response = await llm_main.ainvoke(messages)
        parsed   = parse_json_response(response.content)

        parsed["rag_used"]    = len(rag_docs) > 0
        parsed["rag_type"]    = "enriched"
        parsed["rag_sources"] = [
            {
                "organisme":        doc.metadata.get("organisme", ""),
                "titre_formation":  doc.metadata.get("titre_formation", ""),
                "rncp":             doc.metadata.get("rncp", ""),
                "region":           doc.metadata.get("region", ""),
                "modalite":         doc.metadata.get("modalite", ""),
                "duree":            doc.metadata.get("duree", ""),
                "prix":             doc.metadata.get("prix", ""),
                "cpf":              doc.metadata.get("cpf", ""),
                "lien_catalogue":   doc.metadata.get("lien_catalogue", ""),
                "lien_france_comp": doc.metadata.get("lien_france_comp", ""),
                "fiabilite":        doc.metadata.get("fiabilite", ""),
            }
            for doc in rag_docs
        ]
        return parsed

    except Exception as e:
        logger.error(f"Erreur enriched_chat : {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/enriched/status")
async def enriched_status():
    """État de la base ChromaDB enrichie."""
    stats = get_stats()
    if not stats["ready"]:
        stats["next_steps"] = [
            "1. python rag/enrich.py --source csv     (charge le CSV CPF)",
            "2. python rag/enrich.py --source manual  (données IMT vérifiées)",
            "3. python rag/enrich.py --source scrape  (scraping France Compétences)",
            "4. python rag/enrich.py --source llm     (complétion LLM pour les manquants)",
            "5. python rag/ingest_enriched.py          (indexation ChromaDB)",
        ]
    return stats


@router.get("/rag/enriched/search")
async def enriched_search(
    q:        str           = Query(...,  description="Requête"),
    region:   Optional[str] = Query(None, description="Région"),
    modalite: Optional[str] = Query(None, description="Présentiel / Distanciel / Hybride"),
    niveau:   Optional[str] = Query(None, description="6 ou 7 ou NIVEAU 6"),
    cpf:      bool          = Query(False, description="CPF uniquement"),
    prix_max: Optional[int] = Query(None,  description="Budget max en euros"),
    k:        int           = Query(5,     description="Nombre de résultats"),
):
    """Recherche enrichie avec tous les filtres disponibles."""
    if not is_ready():
        return {"error": "Base enrichie non disponible",
                "message": "Lance python rag/ingest_enriched.py"}

    docs = search_formations(
        query=q, region=region, modalite=modalite,
        niveau=niveau, cpf_only=cpf, prix_max=prix_max, top_k=k
    )
    return {
        "query":    q,
        "filters":  {"region": region, "modalite": modalite,
                     "niveau": niveau, "cpf_only": cpf, "prix_max": prix_max},
        "nb_results": len(docs),
        "results": [
            {
                "score_rank":   i + 1,
                "content":      doc.page_content[:500] + "...",
                "metadata":     doc.metadata,
            }
            for i, doc in enumerate(docs)
        ]
    }


@router.get("/rag/enriched/db/stats")
async def db_stats():
    """Statistiques de la base SQLite enrichie."""
    try:
        from rag.db_schema import get_stats as sqlite_stats
        return {"sqlite": sqlite_stats()}
    except Exception as e:
        return {"error": str(e)}
