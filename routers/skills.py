"""
routers/skills.py — Endpoint /api/skills
Extraction des compétences depuis le texte CV via LLM léger
"""

import re
import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from llm_chain import llm_extract
from langchain_core.messages import SystemMessage, HumanMessage

router = APIRouter()
logger = logging.getLogger(__name__)


class SkillsRequest(BaseModel):
    cv_text: str


SKILLS_SYSTEM = """Analyse ce CV et extrait les compétences clés.
Réponds UNIQUEMENT avec du JSON valide, sans texte avant ni après, sans backticks markdown.

Format exact :
{"skills":[{"name":"Python","level":80},{"name":"Machine Learning","level":45}]}

RÈGLES :
- 8 à 12 compétences maximum
- level : entier 0-100 calibré sur 3 paliers selon les preuves CONCRÈTES dans le CV :
  * 70-100 → Expert : années d'expérience significatives (5+), certifications obtenues, projets aboutis en production, responsabilités confirmées sur cette compétence
  * 40-69  → Intermédiaire : 1-4 ans d'expérience, quelques projets mentionnés, formation suivie ou usage régulier sans spécialisation
  * 0-39   → Débutant : notions théoriques seulement, aucune preuve concrète, compétence absente ou très marginale dans le CV
- Mix hard skills techniques ET soft skills pertinents au profil
- Ne pas inventer de compétences non présentes dans le CV
- JSON pur uniquement, rien d'autre"""


@router.post("/skills")
async def extract_skills(request: SkillsRequest):
    """
    Extrait les compétences du CV avec le modèle léger.

    Retourne : {"skills": [{"name": "...", "level": 0-100}, ...]}
    """
    cv_snippet = request.cv_text[:3000]  # Limiter pour le modèle léger

    messages = [
        SystemMessage(content=SKILLS_SYSTEM),
        HumanMessage(content=f"CV :\n\n{cv_snippet}"),
    ]

    try:
        response = await llm_extract.ainvoke(messages)
        # Nettoyer les surrogates Unicode (fréquents avec Ollama/llama3.2)
        raw = response.content.encode("utf-8", errors="replace").decode("utf-8").strip()
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```", "", raw)

        skills = []

        # Passe 1 : parse direct
        try:
            data = json.loads(raw)
            skills = data.get("skills", [])
        except (json.JSONDecodeError, UnicodeEncodeError):
            pass

        # Passe 2 : extraire le premier bloc JSON valide
        if not skills:
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                try:
                    data = json.loads(match.group())
                    skills = data.get("skills", [])
                except (json.JSONDecodeError, UnicodeEncodeError):
                    pass

        # Passe 3 : extraire les paires name/level par regex (JSON partiel ou malformé)
        if not skills:
            pairs = re.findall(
                r'"name"\s*:\s*"([^"]+)"[^}]*?"level"\s*:\s*(\d+)',
                raw
            )
            if not pairs:
                pairs = re.findall(
                    r'"level"\s*:\s*(\d+)[^}]*?"name"\s*:\s*"([^"]+)"',
                    raw
                )
                skills = [{"name": n, "level": int(l)} for l, n in pairs]
            else:
                skills = [{"name": n, "level": int(l)} for n, l in pairs]

        # Valider et nettoyer
        skills = [
            {"name": str(s.get("name", "")), "level": max(0, min(100, int(s.get("level", 50))))}
            for s in skills if s.get("name")
        ][:12]

        if not skills:
            return {"skills": [], "error": "Aucune compétence extraite"}

        return {"skills": skills}

    except Exception as e:
        logger.error(f"Erreur /skills: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
