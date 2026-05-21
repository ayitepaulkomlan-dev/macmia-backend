"""
routers/rncp.py — Endpoint /api/rncp/questions et /api/rncp/evaluate
Utilise les blocs de compétences RNCP pour poser des questions ciblées
et calculer un score d'adéquation par bloc avant de recommander une formation.
"""

import json
import re
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage
from llm_chain import llm_main
from catalogue import RNCP_BLOCS, ROME_TO_RNCP_PRIORITY, FORMATIONS, JOBS_REF

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Modèles Pydantic ──────────────────────────────────────────────────────────
class RncpQuestionsRequest(BaseModel):
    metier_rome: Optional[str] = None     # ex: "M1889"
    rncp_code: Optional[str] = None       # ex: "RNCP38587" (si déjà ciblé)
    profil_texte: Optional[str] = None    # Description libre du profil
    cv_text: Optional[str] = None


class RncpEvaluateRequest(BaseModel):
    rncp_code: str                        # ex: "RNCP38587"
    reponses: list[dict]                  # [{"bloc": "BC01", "reponse": "Oui, en entreprise"}, ...]
    cv_text: Optional[str] = None
    profil_texte: Optional[str] = None


class DetectRncpRequest(BaseModel):
    message: str                          # Message utilisateur
    cv_text: Optional[str] = None
    metiers_detectes: Optional[list[str]] = None  # ROMEs déjà détectés


# ── Helper : convertir une réponse en score ───────────────────────────────────
SCORE_MAP = {
    # Réponses positives fortes → score élevé
    "oui": 85, "oui,": 85, "oui en": 85,
    "oui régulièrement": 90, "oui au quotidien": 90,
    "oui, chef": 85, "oui, tech lead": 90,
    "oui, expertise": 90, "oui, très à l'aise": 90,
    "oui, plusieurs": 85, "oui en production": 95,
    "solide": 85, "+5 ans": 90, "1-5 ans": 70,
    # Réponses intermédiaires
    "notions": 40, "notions solides": 55, "notions générales": 35,
    "occasionnellement": 50, "ponctuellement": 45, "partiellement": 50,
    "en cours": 30, "j'ai fait": 55, "quelques": 45,
    "une fois": 50, "junior": 35, "peut-être": 40,
    "moins d'1 an": 35, "contributeur": 55,
    # Réponses négatives
    "non": 10, "non,": 10, "pas encore": 15,
    "non mais je veux": 20, "non, débutant": 15,
    "tutoriels seulement": 25, "cours/tutoriels": 25,
    "à renforcer": 20, "rarement": 25, "peu": 25,
    "ni l'un": 10,
}

def reponse_to_score(reponse: str) -> int:
    """Convertit une réponse chips en score 0-100."""
    r = reponse.lower().strip()
    # Cherche le match le plus long en premier
    for key in sorted(SCORE_MAP.keys(), key=len, reverse=True):
        if r.startswith(key) or key in r:
            return SCORE_MAP[key]
    return 50  # Score neutre par défaut


# ── Endpoint 1 : Détecter le RNCP cible et retourner ses questions ─────────
@router.post("/rncp/questions")
async def get_rncp_questions(request: RncpQuestionsRequest):
    """
    Détermine le(s) RNCP les plus pertinents pour le profil
    et retourne les questions des blocs de compétences correspondants.

    Logique :
    1. Si rncp_code fourni → utilise directement ses blocs
    2. Si metier_rome fourni → trouve le RNCP prioritaire via ROME_TO_RNCP_PRIORITY
    3. Sinon → demande au LLM de détecter le RNCP le plus adapté au profil
    """

    # Cas 1 : RNCP explicitement ciblé
    if request.rncp_code and request.rncp_code in RNCP_BLOCS:
        rncp = RNCP_BLOCS[request.rncp_code]
        return {
            "rncp_code": request.rncp_code,
            "rncp_intitule": rncp["intitule"],
            "niveau": rncp["niveau_fr"],
            "cpf": rncp["cpf"],
            "questions": rncp["blocs"],
            "source": "direct",
        }

    # Cas 2 : Métier ROME connu → RNCP prioritaire
    if request.metier_rome and request.metier_rome in ROME_TO_RNCP_PRIORITY:
        rncp_codes = ROME_TO_RNCP_PRIORITY[request.metier_rome]
        # Prendre le 1er RNCP disponible dans nos blocs
        for code in rncp_codes:
            if code in RNCP_BLOCS:
                rncp = RNCP_BLOCS[code]
                metier = JOBS_REF.get(request.metier_rome, {})
                return {
                    "rncp_code": code,
                    "rncp_intitule": rncp["intitule"],
                    "niveau": rncp["niveau_fr"],
                    "cpf": rncp["cpf"],
                    "metier_cible": metier.get("titre", ""),
                    "questions": rncp["blocs"],
                    "source": "rome_mapping",
                }

    # Cas 3 : Détection LLM du RNCP le plus adapté
    available_rncp = [
        f"{code} : {data['intitule']} (Niv.{data['niveau_fr']})"
        for code, data in RNCP_BLOCS.items()
    ]

    sys_detect = f"""Tu es expert en certifications RNCP françaises pour les métiers IA/Data.
Analyse le profil fourni et sélectionne LE RNCP le plus adapté parmi cette liste :

{chr(10).join(available_rncp)}

Réponds UNIQUEMENT avec ce JSON :
{{"rncp_code": "RNCP38587", "raison": "explication courte en 1 phrase"}}"""

    profil = request.profil_texte or ""
    if request.cv_text:
        profil += f"\n\nCV : {request.cv_text[:1000]}"

    try:
        response = await llm_main.ainvoke([
            SystemMessage(content=sys_detect),
            HumanMessage(content=f"Profil : {profil}"),
        ])
        raw = response.content.strip()
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```", "", raw)
        match = re.search(r"\{[\s\S]*\}", raw)

        if match:
            data = json.loads(match.group())
            code = data.get("rncp_code", "")
            if code in RNCP_BLOCS:
                rncp = RNCP_BLOCS[code]
                return {
                    "rncp_code": code,
                    "rncp_intitule": rncp["intitule"],
                    "niveau": rncp["niveau_fr"],
                    "cpf": rncp["cpf"],
                    "raison_selection": data.get("raison", ""),
                    "questions": rncp["blocs"],
                    "source": "llm_detection",
                }
    except Exception as e:
        logger.error(f"Erreur détection RNCP: {e}")

    # Fallback : RNCP38587 (le plus polyvalent)
    rncp = RNCP_BLOCS["RNCP38587"]
    return {
        "rncp_code": "RNCP38587",
        "rncp_intitule": rncp["intitule"],
        "niveau": rncp["niveau_fr"],
        "cpf": rncp["cpf"],
        "questions": rncp["blocs"],
        "source": "fallback",
    }


# ── Endpoint 2 : Évaluer les réponses et scorer chaque bloc ───────────────
@router.post("/rncp/evaluate")
async def evaluate_rncp_responses(request: RncpEvaluateRequest):
    """
    Calcule un score par bloc de compétences à partir des réponses de l'utilisateur.
    Identifie les blocs forts, les lacunes, et recommande les formations adaptées.

    Retourne :
    - score_global : 0-100
    - blocs_evalues : [{code, intitule, score, niveau, commentaire}]
    - formations_recommandees : [ids des formations du catalogue]
    - message_bilan : texte de synthèse pour le chat
    - gaps_principaux : blocs où il y a le plus à progresser
    """
    rncp_code = request.rncp_code
    if rncp_code not in RNCP_BLOCS:
        return {"error": f"RNCP {rncp_code} non trouvé"}

    rncp_data = RNCP_BLOCS[rncp_code]

    # Calculer le score pour chaque bloc
    blocs_evalues = []
    scores = []

    for reponse_item in request.reponses:
        bloc_code = reponse_item.get("bloc", "")
        reponse_text = reponse_item.get("reponse", "")

        # Trouver le bloc correspondant
        bloc_info = next((b for b in rncp_data["blocs"] if b["code"] == bloc_code), None)
        if not bloc_info:
            continue

        score = reponse_to_score(reponse_text)
        scores.append(score)

        niveau = "Fort" if score >= 70 else "Intermédiaire" if score >= 40 else "À développer"
        commentaire = (
            f"✅ Compétence maîtrisée" if score >= 70
            else f"⚠️ Compétence partielle — à renforcer en formation"
            if score >= 40
            else f"🎯 Bloc prioritaire à développer via la formation"
        )

        blocs_evalues.append({
            "code": bloc_code,
            "intitule": bloc_info["intitule"],
            "reponse": reponse_text,
            "score": score,
            "niveau": niveau,
            "commentaire": commentaire,
        })

    score_global = round(sum(scores) / len(scores)) if scores else 0

    # Identifier les lacunes principales
    gaps = [b for b in blocs_evalues if b["score"] < 50]
    gaps_principaux = [f"{b['code']} : {b['intitule']}" for b in sorted(gaps, key=lambda x: x["score"])]

    # Trouver les formations du catalogue alignées sur ce RNCP
    formations_ids = []
    for f in FORMATIONS:
        if f.get("rncp") == rncp_code or rncp_code in (f.get("rncp") or ""):
            formations_ids.append(f["id"])
        # Aussi via métiers ROME alignés
        elif any(rome in (f.get("metiers_cibles") or []) for rome in rncp_data["metiers_rome"]):
            if f["id"] not in formations_ids:
                formations_ids.append(f["id"])

    # Générer le message de bilan via LLM
    bilan_context = f"""RNCP visé : {rncp_data['intitule']} ({rncp_code})
Score global : {score_global}/100
Blocs évalués :
{chr(10).join(f"- {b['code']} {b['intitule']} : {b['score']}/100 ({b['niveau']})" for b in blocs_evalues)}
Lacunes principales : {', '.join(gaps_principaux) if gaps_principaux else 'aucune lacune majeure'}
"""

    sys_bilan = """Tu es conseiller en formation. Génère un bilan personnalisé en 3-4 phrases :
1. Félicite les points forts (blocs score >= 70)
2. Identifie les 1-2 blocs prioritaires à développer
3. Indique que les formations recommandées couvrent précisément ces lacunes
4. Ton encourageant et professionnel. Réponds en texte simple, pas de JSON."""

    try:
        response = await llm_main.ainvoke([
            SystemMessage(content=sys_bilan),
            HumanMessage(content=bilan_context),
        ])
        message_bilan = response.content.strip()
    except Exception as e:
        logger.error(f"Erreur génération bilan: {e}")
        message_bilan = (
            f"Votre score global est de **{score_global}/100** sur le référentiel {rncp_code}. "
            + (f"Points à renforcer : {', '.join(gaps_principaux[:2])}. " if gaps_principaux else "Excellent niveau sur l'ensemble des blocs ! ")
            + "Les formations recommandées ci-dessous couvrent précisément vos axes de progression."
        )

    return {
        "rncp_code": rncp_code,
        "rncp_intitule": rncp_data["intitule"],
        "score_global": score_global,
        "niveau_global": "Expert" if score_global >= 75 else "Intermédiaire" if score_global >= 45 else "Débutant",
        "blocs_evalues": blocs_evalues,
        "gaps_principaux": gaps_principaux,
        "formations_recommandees_ids": formations_ids[:5],
        "message_bilan": message_bilan,
    }


# ── Endpoint 3 : Liste de tous les RNCP disponibles ───────────────────────
@router.get("/rncp/list")
async def list_rncp():
    """Retourne la liste de tous les RNCP avec leurs blocs."""
    return {
        "rncp": [
            {
                "code": code,
                "intitule": data["intitule"],
                "niveau": data["niveau_fr"],
                "cpf": data["cpf"],
                "nb_blocs": len(data["blocs"]),
                "metiers_rome": data["metiers_rome"],
            }
            for code, data in RNCP_BLOCS.items()
        ]
    }
