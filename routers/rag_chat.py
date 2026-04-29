"""
routers/rag_chat.py — Endpoints RAG
POST /api/rag/chat   → Recommandations unifiées IMT + Catalogue CPF complet
GET  /api/rag/status → État de la base vectorielle
GET  /api/rag/search → Recherche directe dans ChromaDB (debug)

Architecture :
  - RAG (ChromaDB, 43k formations CPF) = source principale via similarité vectorielle
  - Catalogue IMT (32 formations curatées) = source complémentaire via scoring Python
  - LLM = génère uniquement le message d'explication (ne choisit plus les formations)
  - Questions de suivi = traitées par call_main_llm (a le contexte complet)
"""

import asyncio
import logging
import re as _re
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from llm_chain import (
    call_main_llm,
    call_recommendation_message_llm,
    _extract_qa_profile,
    _prefilter_formations,
    _build_profile_summary,
)
from rag.retriever import search_formations, get_stats, is_ready
from rag.enrichment import enrich_formation
from rag.mcf_api import enrich_cards_from_api

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Convertit un doc ChromaDB en format carte formation frontend ───────────────
def _doc_to_formation_data(doc, idx: int) -> dict:
    m = doc.metadata

    # Extraire l'objectif depuis le page_content
    desc = ""
    for line in doc.page_content.split("\n"):
        if line.startswith("Objectif :"):
            desc = line[10:].strip()[:350]
            break
    if not desc and doc.page_content:
        # Fallback : premiers 200 chars du contenu
        desc = doc.page_content[:200].strip()

    # Enrichissement depuis la base MCF (prix réels, modalité, lieu, durée, métiers)
    titre_formation = (m.get("titre_formation") or "").strip()
    rncp_val = (m.get("rncp") or "").strip()
    enriched = enrich_formation(titre_formation, rncp_val)

    # Toutes les formations du catalogue MCF sont éligibles CPF
    cpf_eligible = True

    # Durée — depuis enrichissement (rncp_metiers > mcf_lookup) ou métadonnées ChromaDB
    if enriched.get("duree_h_reel") and enriched["duree_h_reel"] != "NC":
        duree = enriched["duree_h_reel"]
    else:
        duree_h = (m.get("duree_heures") or "").strip()
        try:
            h = float(duree_h)
            duree = f"{int(h)} h" if h > 0 else "NC"
        except (ValueError, TypeError):
            duree = duree_h or "NC"

    # Prix réel depuis enrichissement
    prix = enriched.get("prix_reel") or "NC"

    # Modalité réelle + lieu si présentiel
    modalite = enriched.get("modalite_reelle") or (m.get("modalite") or "NC").strip()
    lieu_raw = enriched.get("lieu") or (m.get("region") or "").strip()
    lieu = lieu_raw.replace("nan", "").strip() if lieu_raw else ""
    if modalite not in ("NC", "") and lieu:
        format_display = f"{modalite} — {lieu}"
    else:
        format_display = modalite or "NC"

    # Niveau — nettoyer "nan" et former le label
    niveau_raw = (m.get("niveau") or "").strip()
    if not niveau_raw or niveau_raw.lower() in ("nan", "nc", ""):
        # Certification sans niveau officiel
        niveau = "(Certification)"
    else:
        niveau = niveau_raw

    # Métiers à l'issue — depuis enrichissement rncp_metiers
    metiers_raw = enriched.get("metiers", [])
    metiers_cibles = [
        {"id": f"rag_{idx}_{i}", "titre": t, "score": 100}
        for i, t in enumerate(metiers_raw)
    ]

    # Financement
    fin = ["CPF"]

    # URL Mon Compte Formation
    id_formation = (m.get("id_formation") or "").strip()
    titre_enc = _re.sub(r'\s+', '+', titre_formation[:80])
    if id_formation:
        url = f"https://www.moncompteformation.gouv.fr/espace-prive/html/#/formation/recherche/{id_formation}/details"
    elif titre_enc:
        url = f"https://www.moncompteformation.gouv.fr/espace-prive/html/#/formation/recherche?texte={titre_enc}"
    else:
        url = None

    return {
        "id":               f"rag_{idx}",
        "titre":            (titre_formation or m.get("titre_certification") or "Formation"),
        "ecole":            (m.get("organisme") or "").strip(),
        "theme":            (m.get("domaine") or "").strip(),
        "duree":            duree,
        "format":           format_display,
        "niveau":           niveau,
        "prix":             prix,
        "fin":              fin,
        "reg":              lieu or (m.get("region") or "").strip(),
        "rncp":             rncp_val,
        "rncp_niveau":      "",
        "rncp_eligible_cpf": cpf_eligible,
        "desc":             desc,
        "url":              url,
        "metiers_cibles":   metiers_cibles,
        "source":           "rag",
    }


# ── Modèles Pydantic ──────────────────────────────────────────────────────────
class RAGChatRequest(BaseModel):
    messages: list[dict]
    cv_text: Optional[str] = None
    region: Optional[str] = None
    cpf_only: bool = False
    niveau: Optional[str] = None
    top_k: int = 8  # Augmenté à 8 (source principale)


# ── POST /api/rag/chat ────────────────────────────────────────────────────────
@router.post("/rag/chat")
async def rag_chat(request: RAGChatRequest):
    """
    Recommandations unifiées depuis le catalogue CPF complet (RAG) + formations IMT curatées.

    Flux :
      1. Détection profil/suivi
      2a. Suivi → call_main_llm (contexte complet, formations supprimées par règle #13)
      2b. Profil → RAG (top 8) + IMT scoring (top 4) + message LLM
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages vides")

    # ── Injection CV ──────────────────────────────────────────────────────────
    messages = [dict(m) for m in request.messages]
    cv_text = request.cv_text or ""
    if cv_text:
        CV_MARKERS = ("CV de l'utilisateur", "Voici mon CV", "mon CV :", "CV :")
        cv_prefix = f"[CV de l'utilisateur]\n{cv_text[:2000]}\n\n[Fin du CV]\n\n"
        for msg in messages:
            if msg["role"] == "user":
                if not any(marker in msg["content"] for marker in CV_MARKERS):
                    msg["content"] = cv_prefix + msg["content"]
                break

    last_user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        ""
    )

    # ── Détection question de suivi vs soumission profil ──────────────────────
    msg_count = sum(1 for m in messages if m.get("role") in ("user", "assistant"))
    CV_SUBMISSION_MARKERS = (
        "Voici mon CV", "Réponses au questionnaire",
        "[CV de l'utilisateur]", "brique technique",
        "Voici le profil d'un utilisateur",
    )
    WANTS_NEW_RECO = (
        "autre formation", "autres formations", "plus de formations",
        "d'autres formations", "nouvelles formations", "recommande",
        "cherche une formation", "recommencer", "nouveau profil",
    )

    is_profile_submission = any(m in last_user for m in CV_SUBMISSION_MARKERS)
    # Suivi dès qu'il y a eu au moins 1 échange complet (profil + réponse IA)
    # msg_count >= 2 = au moins 1 message user + 1 assistant
    is_followup = (
        msg_count >= 2
        and len(last_user.strip()) < 400
        and not is_profile_submission
        and not any(t in last_user.lower() for t in WANTS_NEW_RECO)
    )

    try:
        # ── CAS 1 : Question de suivi ─────────────────────────────────────────
        # call_main_llm a le contexte complet + l'enforcement règle #13
        if is_followup:
            logger.info("💬 Question de suivi — call_main_llm")
            parsed = await call_main_llm(messages)
            parsed.setdefault("rag_used", False)
            parsed.setdefault("rag_sources", [])
            return parsed

        # ── CAS 2 : Soumission profil → Recommandations RAG + IMT ─────────────

        # 1. Extraire le profil Q&A
        answers_lower, answers_list = _extract_qa_profile(messages)
        profile_summary = _build_profile_summary(answers_list)

        # 2. Construire la requête RAG — mots-clés techniques propres pour l'embedding
        #    Stratégie : chercher champs structurés Objectif + Domaines en priorité,
        #    sinon extraire les tokens thématiques des réponses Q&A.
        STOP_TERMS = (
            "distanciel", "présentiel", "hybride", "en ligne",
            "cpf", "opco", "alternance", "financement", "éligible", "eligible",
            "île-de-france", "ile-de-france", "paris", "lyon", "marseille",
            "bac+", "débutant", "confirmé", "intermédiaire",
            "temps plein", "temps partiel", "région", "reconversion",
            "reconvertir", "cherchant", "salarie", "salarié",
        )
        if answers_list:
            # Priorité 1 : extraire Objectif et Domaines depuis last_user (champs structurés)
            m_obj = _re.search(r'[Oo]bjectif\s*:\s*(.+?)(?:\n|$)', last_user)
            m_dom = _re.search(r'[Dd]omaines?\s*:\s*(.+?)(?:\n|$)', last_user)
            domain_parts = []
            if m_obj:
                # Supprimer les mots stop de l'objectif
                obj_words = [w for w in m_obj.group(1).strip().split() if w.lower() not in STOP_TERMS and len(w) > 3]
                if obj_words:
                    domain_parts.append(" ".join(obj_words))
            if m_dom:
                # Les domaines : remplacer virgules par espaces
                dom_clean = m_dom.group(1).strip().replace(",", " ").replace("  ", " ")
                domain_parts.append(dom_clean)
            if domain_parts:
                rag_query = " ".join(domain_parts)
            else:
                # Priorité 2 : filtrer tokens stop de toutes les réponses
                tokens = []
                for a in answers_list[:5]:
                    for w in a.strip().split():
                        if len(w) > 4 and w.lower() not in STOP_TERMS:
                            tokens.append(w)
                rag_query = " ".join(tokens[:12]) if tokens else " ".join(answers_list[:2])
        elif cv_text:
            rag_query = f"{last_user[:200]}\n\nCV:\n{cv_text[:300]}"
        else:
            rag_query = last_user

        # 3. Recherche vectorielle RAG — source principale (top 8)
        rag_docs = []
        rag_available = is_ready()
        if rag_available:
            logger.info(f"🔍 RAG search : '{rag_query[:120]}'")
            rag_docs = search_formations(
                query=rag_query,
                region=request.region,
                cpf_only=request.cpf_only,
                niveau=request.niveau,
                top_k=request.top_k,
            )
            logger.info(f"   → {len(rag_docs)} formations CPF trouvées")
        else:
            logger.warning("⚠️ ChromaDB non disponible — fallback catalogue IMT uniquement")

        # 4. Pré-filtrer le catalogue IMT (Python scoring) — source curatée (top 4)
        imt_filtered = _prefilter_formations(answers_lower, answers_list)[:4]

        # Écoles appartenant au groupe IMT (seules celles-ci reçoivent source="imt")
        IMT_SCHOOLS_KW = (
            "imt", "mines-télécom", "mines-telecom",
            "télécom paris", "telecom paris",
            "télécom sudparis", "telecom sudparis",
            "eurecom",
        )

        # 5. Construire les cartes IMT (enrichir prix si NC depuis la base enrichissement)
        imt_cards = []
        for f in imt_filtered:
            ecole_lower = (f.get("ecole") or "").lower()
            is_imt_exed = any(kw in ecole_lower for kw in IMT_SCHOOLS_KW)
            fd = {**f, "source": "imt" if is_imt_exed else "rag"}
            if not fd.get("prix") or fd["prix"] == "NC":
                # Chercher par RNCP numérique dans la base enrichissement
                rncp_num = str(fd.get("rncp", "")).replace("RNCP", "").strip()
                if rncp_num and rncp_num.isdigit():
                    enriched = enrich_formation("", rncp_num)
                    if enriched.get("prix_reel") and enriched["prix_reel"] != "NC":
                        fd["prix"] = enriched["prix_reel"]
            imt_cards.append({
                "id": f["id"],
                "formation_data": fd,
                "raison_match": f.get("desc", "")[:120],
            })

        # 6. Dédupliquer les docs RAG : même RNCP → garder un seul doc (la certification complète
        #    si dispo, sinon le premier bloc). Même titre → garder le premier.
        seen_rncps  = set()
        seen_titles = set()
        rag_docs_unique = []
        for doc in rag_docs:
            rncp = str(doc.metadata.get("rncp") or "").strip()
            t = (doc.metadata.get("titre_formation") or doc.metadata.get("titre_certification") or "").lower().strip()
            # Dédup par RNCP (ignorer RNCP -1 ou vide)
            if rncp and rncp not in ("", "-1", "nan"):
                if rncp in seen_rncps:
                    continue
                seen_rncps.add(rncp)
            # Dédup par titre
            if t and t not in seen_titles:
                seen_titles.add(t)
                rag_docs_unique.append(doc)

        # 7. Construire les cartes RAG
        rag_cards = [
            {
                "id": f"rag_{i}",
                "formation_data": _doc_to_formation_data(doc, i),
                "raison_match": "Formation certifiée Qualiopi — Catalogue CPF officiel data.gouv.fr",
            }
            for i, doc in enumerate(rag_docs_unique)
        ]

        # 8. Dédupliquer : supprimer des cartes RAG celles qui doublonnent les IMT
        imt_titles_lower = {c["formation_data"]["titre"].lower() for c in imt_cards}
        rag_cards_clean = [
            c for c in rag_cards
            if c["formation_data"]["titre"].lower() not in imt_titles_lower
        ]

        # 9. Combiner : IMT (curatées, avec métiers + liens directs) en premier
        all_formations = imt_cards + rag_cards_clean

        # 9b. Enrichissement API CDC (Caisse des Dépôts) — comble les NC prix/durée
        #     Timeout global de 8s pour ne jamais bloquer la réponse si l'API est lente
        try:
            all_formations = await asyncio.wait_for(
                enrich_cards_from_api(all_formations), timeout=8.0
            )
        except Exception as e:
            logger.warning(f"Enrichissement API CDC ignoré : {e}")

        # 10. Construire le contexte formations pour le LLM
        ctx_lines = []
        for c in all_formations[:10]:
            fd = c["formation_data"]
            src = "IMT" if fd.get("source") == "imt" else "CPF data.gouv.fr"
            cpf_tag = "✓ CPF" if fd.get("rncp_eligible_cpf") else ""
            rncp = fd.get("rncp") or ""
            ctx_lines.append(
                f"[{src}] {fd['titre']} | {fd.get('ecole','')} | "
                f"{fd.get('format','')} | {fd.get('niveau','')} | {cpf_tag} {rncp}"
            )
        formations_context = "\n".join(ctx_lines) if ctx_lines else "Aucune formation trouvée"

        # 10. Générer le message LLM
        if all_formations:
            parsed = await call_recommendation_message_llm(
                history=messages,
                formations_context=formations_context,
                profile_summary=profile_summary,
            )
        else:
            # Aucune formation trouvée → fallback call_main_llm
            logger.warning("Aucune formation trouvée — fallback call_main_llm")
            parsed = await call_main_llm(messages)

        parsed["formations"] = all_formations
        parsed["rag_used"] = rag_available and len(rag_docs) > 0
        parsed["rag_sources"] = []
        return parsed

    except Exception as e:
        logger.error(f"Erreur rag_chat : {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/rag/status ───────────────────────────────────────────────────────
@router.get("/rag/status")
async def rag_status():
    """Vérifie l'état de la base vectorielle ChromaDB."""
    stats = get_stats()
    if not stats["ready"]:
        stats["next_step"] = (
            "Lance : cd backend && python rag/ingest.py\n"
            "Durée estimée : 30-90 min (téléchargement + indexation)"
        )
    return stats


# ── GET /api/rag/search ───────────────────────────────────────────────────────
@router.get("/rag/search")
async def rag_search_debug(
    q: str = Query(..., description="Requête de recherche"),
    region: Optional[str] = Query(None, description="Filtre région"),
    cpf: bool = Query(False, description="CPF uniquement"),
    k: int = Query(5, description="Nombre de résultats")
):
    """
    Recherche directe dans ChromaDB (endpoint de debug/test).
    Exemple : GET /api/rag/search?q=data scientist python&region=Paris&k=3
    """
    if not is_ready():
        return {
            "error": "Base RAG non disponible",
            "message": "Lance python rag/ingest.py pour indexer le catalogue"
        }

    docs = search_formations(query=q, region=region, cpf_only=cpf, top_k=k)
    return {
        "query": q,
        "filters": {"region": region, "cpf_only": cpf},
        "nb_results": len(docs),
        "results": [
            {
                "score_rank": i + 1,
                "content": doc.page_content[:300] + "...",
                "metadata": doc.metadata,
            }
            for i, doc in enumerate(docs)
        ]
    }
