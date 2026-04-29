"""
routers/chat.py — Endpoint /api/chat
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

from llm_chain import (
    call_main_llm,
    call_bridging_llm,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Modèles Pydantic ──────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str        # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    cv_text: Optional[str] = None


class InterviewRequest(BaseModel):
    cv_text: str
    cv_data: Optional[dict] = None   # Données extraites (nom, poste, etc.)


class BridgingRequest(BaseModel):
    cv_text: str
    answered_so_far: str             # Résumé des réponses collectées


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint principal de chat.

    Reçoit :
      - messages : historique complet [{role, content}]
      - cv_text  : texte du CV si disponible (optionnel)

    Retourne le JSON structuré MACMIA :
      {persona_id, persona_confidence, message, formations[], quick_replies[], profile_tags[], ...}
    """
    try:
        # Convertir les objets Pydantic en dicts
        history = [{"role": m.role, "content": m.content} for m in request.messages]

        # Si CV disponible, l'injecter dans le contexte du premier message user
        # — seulement si le CV n'est pas déjà présent dans le message (évite la double injection)
        CV_MARKERS = ("CV de l'utilisateur", "Voici mon CV", "mon CV :", "CV :")
        if request.cv_text and history:
            cv_prefix = f"[CV de l'utilisateur]\n{request.cv_text[:2000]}\n\n[Fin du CV]\n\n"
            for msg in history:
                if msg["role"] == "user":
                    already_has_cv = any(marker in msg["content"] for marker in CV_MARKERS)
                    if not already_has_cv:
                        msg["content"] = cv_prefix + msg["content"]
                    break  # Toujours s'arrêter au premier message user

        result = await call_main_llm(history)
        return result

    except Exception as e:
        logger.error(f"Erreur /chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"❌ Erreur LLM : {str(e)}",
                "formations": [],
                "quick_replies": ["Réessayer"],
                "persona_id": None,
            }
        )


@router.post("/interview/questions")
async def get_interview_questions(request: InterviewRequest):
    """
    Retourne 4 questions d'interview ciblées selon le profil détecté dans le CV.
    Chaque profil cible les dimensions inconnues utiles pour recommander les bonnes formations.
    Sans appel LLM — stable, rapide, reproductible.

    Retourne : {"questions": [{"q": "...", "chips": ["A", "B", "C"]}, ...]}
    """
    cv = (request.cv_text or "").lower()

    # ── Signaux de domaine ────────────────────────────────────────────────────
    is_data     = any(w in cv for w in ["data scientist", "data analyst", "data engineer", "machine learning",
                                         "deep learning", "power bi", "tableau", "spark", "hadoop", "mlops"])
    is_cyber    = any(w in cv for w in ["cybersécurité", "cybersecurite", "sécurité informatique", "rssi",
                                         "pentest", "soc ", "firewall", "anssi", "cryptographie", "vulnerability"])
    is_industry = any(w in cv for w in ["industrie", "production", "maintenance", "automatisation", "robotique",
                                         "usine", "procédé", "mécanique", "électronique", "iot", "scada", "plc"])
    is_cloud    = any(w in cv for w in ["cloud", "aws", "azure", "gcp", "devops", "kubernetes", "docker",
                                         "terraform", "ci/cd", "infrastructure"])
    is_health   = any(w in cv for w in ["médecin", "infirmier", "santé", "hôpital", "chu", "clinique",
                                         "pharmacien", "médical", "e-santé", "dpc", "urgentiste"])
    is_marketing = any(w in cv for w in ["marketing", "communication", "commercial", "crm", "seo",
                                          "growth", "digital marketing", "brand", "campagne"])
    is_rh       = any(w in cv for w in ["ressources humaines", "rh ", "recrutement", "drh", "grh",
                                         "talent", "paie", "gpec", "sirh"])
    is_student  = any(w in cv for w in ["étudiant", "licence", "bachelor", "bts", "alternance",
                                         "apprenti", "stage ", "master 1", "master 2", "école d'ingénieur"])

    # ── Signaux de niveau / rôle ─────────────────────────────────────────────
    is_tech     = any(w in cv for w in ["python", "sql", "java", "javascript", "développeur", "ingénieur",
                                         "engineer", "developer", "backend", "frontend", "fullstack"])
    is_manager  = any(w in cv for w in ["manager", "directeur", "responsable", "chef de projet",
                                         "head of", "cto", "dsi", "lead "])
    is_senior   = any(w in cv for w in ["10 ans", "12 ans", "15 ans", "20 ans", "senior", "expert",
                                         "confirmé", "architecte", "principal"])

    # ── Sélection des questions par profil ───────────────────────────────────

    # Profil : Data Scientist / Data Analyst / Data Engineer
    if is_data:
        return {"questions": [
            {"q": "Vers quel rôle Data souhaitez-vous évoluer ?",
             "chips": ["Data Scientist / ML Engineer", "Data Engineer / MLOps", "Data Analyst / BI", "Chief Data Officer"]},
            {"q": "Quel est votre niveau actuel en Machine Learning ?",
             "chips": ["Je débute (notions théoriques)", "Intermédiaire (modèles en production)", "Avancé (fine-tuning, LLM)", "Expert (recherche, publication)"]},
            {"q": "Sur quelle brique technique voulez-vous progresser en priorité ?",
             "chips": ["IA Générative & LLM", "MLOps & déploiement en production", "Big Data & pipelines", "Gouvernance & qualité des données"]},
            {"q": "Quelle modalité vous convient le mieux ?",
             "chips": ["100% distanciel (en emploi)", "Hybride (quelques jours en présentiel)", "Temps plein (Mastère Spécialisé)", "Alternance diplômante"]},
            {"q": "Comment envisagez-vous le financement ?",
             "chips": ["CPF (droits personnels)", "OPCO / plan de formation employeur", "Alternance (rémunéré)", "Financement personnel"]},
        ]}

    # Profil : Cybersécurité
    if is_cyber:
        return {"questions": [
            {"q": "Quel aspect de la cybersécurité vous attire le plus ?",
             "chips": ["Audit & pentest offensif", "RSSI & gouvernance (NIS2, RGPD)", "SOC & détection d'incidents", "Conformité & certification (ANSSI)"]},
            {"q": "Quel est votre niveau d'expérience en sécurité ?",
             "chips": ["Je veux me spécialiser (transition)", "Technicien sécurité (2-5 ans)", "Ingénieur confirmé (5-10 ans)", "Expert / RSSI (10+ ans)"]},
            {"q": "Quel type de certification visez-vous ?",
             "chips": ["Mastère Spécialisé RNCP (1 an)", "Certifiant court intensif", "Formation compatible emploi", "Double diplôme grande école"]},
            {"q": "Comment envisagez-vous le financement ?",
             "chips": ["CPF (droits personnels)", "OPCO / plan de formation", "Alternance", "Financement personnel"]},
        ]}

    # Profil : Industrie du Futur / IoT / Robotique
    if is_industry:
        return {"questions": [
            {"q": "Quel est votre objectif dans la transformation de votre secteur ?",
             "chips": ["Intégrer l'IA dans les procédés industriels", "Robotique & cobotique", "Industrie 4.0 & IoT / maintenance prédictive", "Pilotage de projets de transformation"]},
            {"q": "Quelle est votre position dans l'entreprise ?",
             "chips": ["Technicien / Opérateur", "Ingénieur process / méthodes", "Responsable production / maintenance", "Directeur industriel / DSI"]},
            {"q": "Avez-vous des contraintes de déplacement pour la formation ?",
             "chips": ["Je préfère rester dans ma région", "Déplacement possible en Île-de-France", "100% distanciel uniquement", "Peu importe — mobilité nationale"]},
            {"q": "Quel financement est disponible pour vous ?",
             "chips": ["OPCO 2i / employeur", "CPF personnel", "Plan de formation entreprise", "Je cherche encore un financement"]},
        ]}

    # Profil : Cloud / DevOps / Infrastructure
    if is_cloud:
        return {"questions": [
            {"q": "Quelle direction cloud souhaitez-vous approfondir ?",
             "chips": ["Architecture cloud multi-cloud (AWS/Azure/GCP)", "DevOps & CI/CD avancé", "IA sur cloud & MLOps", "Sécurité cloud & conformité"]},
            {"q": "Quel est votre niveau actuel en cloud ?",
             "chips": ["Notions de base (IaaS/PaaS)", "Certifié cloud junior (AWS/Azure)", "Ingénieur cloud confirmé", "Architecte / Tech Lead cloud"]},
            {"q": "Souhaitez-vous une certification reconnue ?",
             "chips": ["Oui — RNCP ou MS grande école", "Certification éditeur (AWS, Azure)", "Formation courte sans certification", "Diplôme Mastère Spécialisé"]},
            {"q": "Quelle est votre situation professionnelle actuelle ?",
             "chips": ["En poste — formation en parallèle", "En poste — mon employeur finance", "En recherche d'emploi", "Freelance / indépendant"]},
        ]}

    # Profil : Santé / Médical
    if is_health:
        return {"questions": [
            {"q": "Dans quel contexte souhaitez-vous utiliser l'IA ?",
             "chips": ["Diagnostic & imagerie médicale", "Gestion et analyse des données patients", "IA pour la recherche clinique", "Pilotage stratégique en établissement de santé"]},
            {"q": "Quel est votre objectif de montée en compétences ?",
             "chips": ["Comprendre l'IA pour collaborer avec des équipes tech", "Devenir référent IA dans mon service", "Me reconvertir vers la santé numérique", "Piloter un projet IA dans mon établissement"]},
            {"q": "Quel format est compatible avec votre emploi du temps médical ?",
             "chips": ["Soirs & week-ends (distanciel)", "Quelques jours intensifs entre gardes", "Temps partiel sur 6 mois", "DPC — formation médicale continue"]},
            {"q": "Comment envisagez-vous le financement ?",
             "chips": ["DPC (financement médical)", "CPF personnel", "Établissement / GHT", "Financement personnel"]},
        ]}

    # Profil : Marketing / Communication / Digital
    if is_marketing:
        return {"questions": [
            {"q": "Comment souhaitez-vous intégrer l'IA dans votre métier ?",
             "chips": ["Data marketing & CRM prédictif", "IA générative pour le contenu & SEO", "Analytics & mesure de performance", "Transformation digitale de l'équipe"]},
            {"q": "Quel est votre niveau de connaissance en data ?",
             "chips": ["Aucune notion (Excel uniquement)", "À l'aise avec les outils BI", "Notions de SQL / Python", "Expérience en data marketing"]},
            {"q": "Quel type de formation correspond à votre agenda ?",
             "chips": ["Formation courte (2-5 jours)", "Parcours de 3-6 mois en distanciel", "Executive / soirs & week-ends", "Mastère Spécialisé diplômant"]},
            {"q": "Votre entreprise finance-t-elle la formation ?",
             "chips": ["Oui — OPCO / plan de formation", "Partiellement", "Non — CPF personnel", "Je suis indépendant / freelance"]},
        ]}

    # Profil : RH / Formation / Talent
    if is_rh:
        return {"questions": [
            {"q": "Quel est votre objectif principal avec l'IA ?",
             "chips": ["Automatiser le recrutement & sourcing", "Piloter la formation avec des outils IA", "Comprendre l'IA pour accompagner mes équipes", "Me reconvertir vers un rôle Data RH"]},
            {"q": "Quel est votre niveau de connaissance technique actuel ?",
             "chips": ["Aucune notion technique", "Quelques bases (Excel, SIRH)", "À l'aise avec les outils data RH", "Notions de programmation"]},
            {"q": "Quelle modalité correspond à votre emploi du temps ?",
             "chips": ["Quelques jours intensifs", "Distanciel flexible (soirs/week-ends)", "Temps plein sur 3-6 mois", "Alternance diplômante"]},
            {"q": "Votre entreprise finance-t-elle cette montée en compétences ?",
             "chips": ["Oui — OPCO / plan de formation", "Partiellement", "Non — CPF personnel", "Je cherche encore"]},
        ]}

    # Profil : Étudiant / Jeune diplômé
    if is_student:
        return {"questions": [
            {"q": "Quel métier IA / Data vous attire le plus ?",
             "chips": ["Data Scientist / ML Engineer", "Développeur IA / Ingénieur IA", "Data Analyst / BI", "Chef de projet IA / transformation digitale"]},
            {"q": "Quel type de formation vous correspond ?",
             "chips": ["Mastère Spécialisé (1 an, Bac+6)", "Alternance diplômante (2 ans)", "Bootcamp intensif (3-6 mois)", "Certification courte + emploi"]},
            {"q": "Avez-vous déjà une expérience en programmation ou en data ?",
             "chips": ["Non — je pars de zéro", "Quelques notions (Python, stats)", "Oui — formation tech en cours", "Oui — projets / stages réalisés"]},
            {"q": "Comment envisagez-vous le financement de votre formation ?",
             "chips": ["Alternance (rémunéré)", "CPF si droits disponibles", "Financement familial / personnel", "Bourse ou aide Pôle Emploi"]},
        ]}

    # Profil : Ingénieur / Dev senior (10+ ans)
    if is_tech and is_senior:
        return {"questions": [
            {"q": "Souhaitez-vous évoluer vers un rôle de leadership ou approfondir votre expertise ?",
             "chips": ["Expertise technique IA / Data avancée", "Architecture & direction technique", "Management d'équipe tech", "Conseil / Freelance expert"]},
            {"q": "Quelle spécialisation IA vous intéresse le plus ?",
             "chips": ["IA Générative & LLM", "MLOps & IA en production", "Data Engineering à grande échelle", "IA embarquée / Edge AI"]},
            {"q": "Quel format de formation correspond à votre situation ?",
             "chips": ["Formation courte intensive (compatible emploi)", "Mastère Spécialisé diplômant (1 an)", "Parcours certifiant RNCP (6 mois)", "Quelques jours — Executive / séminaire"]},
            {"q": "Comment envisagez-vous le financement ?",
             "chips": ["CPF (droits personnels)", "OPCO / plan de formation employeur", "Budget personnel", "Je cherche encore"]},
            {"q": "Dans quel délai souhaitez-vous être opérationnel sur ces nouvelles compétences ?",
             "chips": ["Très vite — moins de 3 mois", "6 mois", "1 an (parcours complet)", "Pas de contrainte de délai"]},
        ]}

    # Profil : Manager / Décideur
    if is_manager:
        return {"questions": [
            {"q": "Quel est votre objectif avec une formation IA ?",
             "chips": ["Piloter des projets IA dans mon organisation", "Comprendre l'IA pour prendre de meilleures décisions", "Transformer mon entreprise par la donnée", "Constituer et manager une équipe IA / Data"]},
            {"q": "Quel est votre niveau de connaissance technique actuel ?",
             "chips": ["Aucune notion technique", "Quelques bases (Excel, outils BI)", "Notions de programmation ou data", "À l'aise avec les outils numériques avancés"]},
            {"q": "Quelle modalité correspond le mieux à votre agenda ?",
             "chips": ["Quelques jours intensifs (Executive)", "Distanciel flexible — soirs & week-ends", "Parcours 6-12 mois en cours d'emploi", "Séminaires + suivi à distance"]},
            {"q": "Comment votre formation sera-t-elle financée ?",
             "chips": ["Plan de formation / OPCO", "Budget personnel de direction", "CPF", "Je cherche encore"]},
        ]}

    # Profil : Ingénieur / Dev junior (< 10 ans d'expérience)
    if is_tech:
        return {"questions": [
            {"q": "Quelle direction souhaitez-vous prendre dans votre carrière tech ?",
             "chips": ["Spécialisation IA / Machine Learning", "Data Engineering & pipelines", "Cloud & architecture", "Lead tech / management d'équipe"]},
            {"q": "Quel est votre niveau actuel en IA / Data ?",
             "chips": ["Débutant — je veux découvrir", "Quelques projets personnels", "Expérience pro en cours", "Compétences solides à valider (RNCP)"]},
            {"q": "Quel format de formation s'adapte le mieux à votre situation ?",
             "chips": ["100% distanciel (en emploi)", "Hybride — quelques jours en présentiel", "Alternance diplômante", "Bootcamp intensif à plein temps"]},
            {"q": "Comment envisagez-vous le financement ?",
             "chips": ["CPF (droits personnels)", "Mon employeur via OPCO", "Financement personnel", "Je suis demandeur d'emploi (ARE)"]},
        ]}

    # Profil par défaut : reconversion ou profil mixte
    return {"questions": [
        {"q": "Quel est votre objectif prioritaire avec une formation IA / Data ?",
         "chips": ["Obtenir un emploi dans le secteur", "Monter en compétences dans mon poste actuel", "Reconversion complète vers un nouveau métier", "Lancer un projet ou une startup"]},
        {"q": "Quel niveau de formation correspond à votre projet ?",
         "chips": ["Certifiant court (< 6 mois)", "Mastère Spécialisé diplômant (1 an)", "Executive / temps partiel", "Titre Professionnel RNCP accessible"]},
        {"q": "Quelle modalité vous convient ?",
         "chips": ["100% distanciel", "Hybride (présentiel + distanciel)", "Présentiel Paris / grandes villes", "Alternance"]},
        {"q": "Comment envisagez-vous le financement ?",
         "chips": ["CPF (compte personnel de formation)", "OPCO / employeur", "Pôle Emploi / ARE", "Financement personnel"]},
    ]}


@router.post("/interview/bridging")
async def get_bridging_question(request: BridgingRequest):
    """
    Génère une question de relance quand l'utilisateur dit 'Je ne sais pas'.
    Remplace showBridgingQuestion() du JS.

    Retourne : {"q": "...", "chips": ["A", "B", "C"]}
    """
    try:
        result = await call_bridging_llm(request.cv_text, request.answered_so_far)
        return result
    except Exception as e:
        logger.error(f"Erreur /interview/bridging: {e}", exc_info=True)
        return {
            "q": "Qu'est-ce qui vous attire le plus dans une formation IA ?",
            "chips": ["Changer de métier", "Évoluer dans mon poste actuel", "Valider mes compétences"]
        }


@router.post("/orientation")
async def get_orientation(request: BridgingRequest):
    """
    Génère la carte d'orientation marché (jobs tendances + questions de suivi).
    Remplace showOrientationCard() du JS.

    Retourne : {"insight":"...", "jobs":[{title, salary, trend, why}], "questions":[...]}
    """
    from llm_chain import llm_main
    from langchain_core.messages import SystemMessage, HumanMessage
    import json, re

    sys_orient = """Tu es un expert du marché de l'emploi IA/Data en France.
Analyse le profil CV et génère :
1. Un insight personnalisé sur les opportunités marché (2-3 phrases)
2. Les 2-3 métiers les plus adaptés à ce profil avec tendances OPIIEC 2025
3. Des questions de suivi adaptées au contexte

Retourne UNIQUEMENT ce JSON :
{
  "insight": "...",
  "jobs": [
    {"title": "...", "salary": "XX–XXk€", "trend": "🔺 ...", "why": "..."}
  ],
  "questions": [
    {"q": "...", "chips": ["A", "B", "C"]}
  ]
}"""

    user_msg = f"CV :\n{request.cv_text[:1500]}\n\nRéponses collectées :\n{request.answered_so_far}"

    try:
        response = await llm_main.ainvoke([
            SystemMessage(content=sys_orient),
            HumanMessage(content=user_msg),
        ])
        raw = response.content.strip()
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```", "", raw)
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group())
        return {"insight": "Profil analysé.", "jobs": [], "questions": []}
    except Exception as e:
        logger.error(f"Erreur /orientation: {e}", exc_info=True)
        return {"insight": "Analyse temporairement indisponible.", "jobs": [], "questions": []}
