"""
llm_chain.py — Chaîne LangChain + Ollama / Anthropic pour MACMIA
Supporte deux fournisseurs LLM : Anthropic Claude API ou Ollama local.
Configurez LLM_PROVIDER dans .env ou config.py.
"""

import asyncio
import json
import re
import logging
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from config import settings
from catalogue import (
    FORMATIONS, PERSONAS, JOBS_REF, OPIIEC_STATS,
    build_catalogue_summary, build_personas_summary,
)
import json as _json

logger = logging.getLogger(__name__)


# ── Factory LLM ──────────────────────────────────────────────────────────────
def _create_llm(temperature: float, max_tokens: int, model_key: str = "main"):
    """
    Crée l'instance LLM selon le fournisseur configuré.
    - LLM_PROVIDER=anthropic → Claude API (recommandé)
    - LLM_PROVIDER=ollama    → Ollama local (open-source)
    """
    if settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        from langchain_anthropic import ChatAnthropic
        logger.info(f"LLM: Anthropic {settings.ANTHROPIC_MODEL}")
        return ChatAnthropic(
            model=settings.ANTHROPIC_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        from langchain_ollama import ChatOllama
        ollama_model = settings.MAIN_MODEL if model_key == "main" else settings.EXTRACTION_MODEL
        logger.info(f"LLM: Ollama {ollama_model}")
        # num_ctx=12288 : le prompt système seul dépasse 7000 tokens (catalogue + RAG),
        # il faut au minimum 12k de contexte pour laisser de la place à l'historique + réponse
        return ChatOllama(
            model=ollama_model,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=temperature,
            num_predict=max_tokens,
            num_ctx=12288,
            format="json",
        )


# Instances LLM — créées au démarrage selon la config
llm_main    = _create_llm(settings.MAIN_TEMPERATURE,       settings.MAIN_MAX_TOKENS,       model_key="main")
llm_extract = _create_llm(settings.EXTRACTION_TEMPERATURE, settings.EXTRACTION_MAX_TOKENS, model_key="extraction")


# ── Extraction profil Q&A ─────────────────────────────────────────────────────
def _extract_qa_profile(history: list[dict]) -> tuple[str, list[str]]:
    """
    Extrait les réponses d'interview depuis l'historique.
    Supporte deux formats :
      - Format → : "→ réponse" (CV + questionnaire)
      - Format - Key : Value : "- Objectif : data science" (formulaire seul)
    Returns: (answers_joined_lower, list_of_raw_answers)
    """
    PROFILE_MARKERS = (
        "Réponses au questionnaire de qualification",
        "Voici le profil d'un utilisateur",
        "Voici mon CV",
    )
    for msg in history:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if any(m in content for m in PROFILE_MARKERS):
                # Format 1 : → réponse (CV + questionnaire)
                answers = re.findall(r'→\s*(.+)', content)
                if answers:
                    return " ".join(answers).lower(), answers
                # Format 2 : - Clé : Valeur (formulaire seul)
                answers = re.findall(r'-\s*\w[^:\n]+:\s*(.+)', content)
                answers = [a.strip() for a in answers if a.strip() and len(a.strip()) > 2]
                if answers:
                    return " ".join(answers).lower(), answers
                # Fallback : premiers 800 chars
                return content[:800].lower(), []
    return "", []


def _prefilter_formations(answers_lower: str, answers_list: list[str]) -> list:
    """
    Pré-filtre le catalogue aux ~12 formations les plus pertinentes pour ce profil.
    Réduit la charge cognitive du LLM (32 formations → 10-12 ciblées).
    """
    if not answers_lower:
        return FORMATIONS

    def score(f: dict) -> int:
        s = 0
        f_txt = (
            f.get("titre", "") + " " +
            f.get("theme", "") + " " +
            f.get("ecole", "") + " " +
            " ".join(f.get("kw", [])) + " " +
            f.get("desc", "") + " " +
            f.get("format", "") + " " +
            " ".join(f.get("fin", []))
        ).lower()

        # ── Financement ──────────────────────────────────────────────────────
        if "cpf" in answers_lower and f.get("rncp_eligible_cpf"):
            s += 3
        if any(w in answers_lower for w in ("opco", "employeur", "plan de formation")):
            if "opco" in " ".join(f.get("fin", [])).lower():
                s += 2
        if "alternance" in answers_lower and "alternance" in " ".join(f.get("fin", [])).lower():
            s += 2

        # ── Modalité ────────────────────────────────────────────────────────
        fmt = f.get("format", "").lower()
        if any(w in answers_lower for w in ("distanciel", "distance", "en ligne", "100%")):
            if "distanciel" in fmt or "ligne" in fmt:
                s += 4
        if "hybride" in answers_lower and "hybride" in fmt:
            s += 3
        if "présentiel" in answers_lower and "présentiel" in fmt:
            s += 1

        # ── Domaines techniques (forte pondération) ──────────────────────────
        TECH_MAP = [
            (("ia générative", "llm", "gpt", "prompt engineering"), ["ia générative", "llm", "gpt", "generative"]),
            (("mlops", "déploiement", "production", "mise en production"), ["mlops", "déploiement"]),
            (("data engineer", "etl", "pipeline", "big data"), ["data engineer", "etl", "pipeline", "big data"]),
            (("data scientist", "data science", "machine learning", "ml engineer", "analyse de données", "ia", "intelligence artificielle"), ["machine learning", "data science", "ml", "deep learning", "ia"]),
            (("cybersécurité", "cyber", "rssi", "sécurité"), ["cybersécurité", "cyber", "rssi"]),
            (("cloud", "aws", "azure", "devops"), ["cloud", "aws", "azure", "devops"]),
            (("industrie", "robotique", "cobotique", "iot"), ["industrie", "robotique", "cobotique", "iot"]),
            (("5g", "réseau", "télécoms"), ["5g", "réseaux", "télécoms"]),
            (("management", "leadership", "innovation", "transformation"), ["management", "leadership", "innovation"]),
            (("marketing", "crm", "data marketing"), ["marketing", "crm", "programmatic"]),
        ]
        for answer_kws, formation_kws in TECH_MAP:
            if any(k in answers_lower for k in answer_kws):
                if any(k in f_txt for k in formation_kws):
                    s += 5

        # ── Match direct des réponses brutes ─────────────────────────────────
        for ans in answers_list:
            ans_l = ans.lower().strip()
            words = [w for w in ans_l.split() if len(w) > 3]
            for w in words:
                if w in f_txt:
                    s += 1

        return s

    scored = sorted([(score(f), f) for f in FORMATIONS], key=lambda x: x[0], reverse=True)

    # Top 12 avec score > 0 minimum, ou les 10 premières si pas assez de match
    top = [f for s, f in scored if s > 0]
    if len(top) < 5:
        top = [f for _, f in scored[:10]]
    return top[:12]


def _build_profile_summary(answers_list: list[str]) -> str:
    """Construit un résumé lisible du profil à injecter dans le prompt."""
    if not answers_list:
        return ""
    lines = [f"• {a.strip()}" for a in answers_list[:8] if a.strip()]
    return "\n".join(lines)


# ── Prompt Système ────────────────────────────────────────────────────────────
def build_system_prompt(formations_subset=None, profile_summary=None) -> str:
    """
    Construit le prompt système complet.
    - formations_subset : liste pré-filtrée selon le profil (optionnel)
    - profile_summary   : résumé structuré des réponses Q&A (optionnel)
    """
    target_formations = formations_subset if formations_subset is not None else FORMATIONS
    catalogue_json = build_catalogue_summary(formations=target_formations)
    personas_json  = build_personas_summary()
    n_formations   = len(target_formations)
    n_total        = len(FORMATIONS)
    n_personas     = len(PERSONAS)

    json_format = (
        '{"persona_id":"id|null","persona_confidence":0.0,'
        '"message":"texte avec **gras** et sauts de ligne",'
        '"formations":[{"id":N,"titre":"titre exact copié du catalogue"}],'
        '"quick_replies":["..."],'
        '"profile_tags":["..."],'
        '"profile_name":"...","profile_role":"..."}'
    )

    # Bloc profil synthétisé (uniquement quand on a des données Q&A)
    profile_block = ""
    if profile_summary:
        profile_block = f"""
## PROFIL UTILISATEUR — CRITÈRES EXTRAITS DES RÉPONSES
{profile_summary}

⚠️ INSTRUCTION CRITIQUE : Tu DOIS respecter ces critères pour choisir les formations.
- Si l'utilisateur veut du **distanciel** → ne propose PAS de formations en présentiel uniquement
- Si l'utilisateur veut du **CPF** → ne propose PAS de formations sans éligibilité CPF
- Si l'utilisateur a un domaine cible (ex: MLOps, Data Science) → reste dans ce domaine
"""

    catalogue_header = (
        f"## CATALOGUE PRÉSÉLECTIONNÉ — {n_formations} formations adaptées à ce profil"
        if formations_subset is not None
        else f"## CATALOGUE COMPLET — {n_total} formations (toutes écoles confondues)"
    )
    catalogue_note = (
        "⚠️ Ces formations ont été pré-sélectionnées pour correspondre au profil ci-dessus. Choisis parmi celles-ci."
        if formations_subset is not None
        else "⚠️ RÈGLE CRITIQUE : explore TOUTES les formations avant de choisir. Ne pas se limiter à IMT-BS ExeD."
    )

    return f"""Tu es l'assistant MACMIA, expert en orientation formation IA, Data et Industrie du Futur pour les 8 Grandes Écoles IMT (France 2030) : IMT-BS, Télécom Paris, Télécom SudParis, IMT Atlantique, IMT Mines Albi, IMT Nord Europe, IMT Mines Alès, EURECOM.

REGLE ABSOLUE : Tu ne recommandes QUE des formations du catalogue ci-dessous (ids 1 à {n_total}). N'invente aucune autre formation.

CONTEXTE MARCHE (OPIIEC 2025) : +45 000 emplois IA d'ici 3 ans, 88% des entreprises prévoient d'utiliser l'IA, 287 000 salariés à former.

## PERSONAS ({n_personas})
{personas_json}
{profile_block}
{catalogue_header}
{catalogue_note}
{catalogue_json}

## INSTRUCTIONS
1. Detecte le persona le plus proche (persona_id) avec un score 0-1 (persona_confidence)
2. Recommande 2-4 formations — privilégie la pertinence au profil et aux critères ci-dessus
3. Si CPF est demandé, ne recommande QUE des formations avec cpf:true
4. Si distanciel est demandé, ne recommande QUE des formations en distanciel ou hybride
5. Si financement CPF possible (cpf:true), mentionne-le explicitement
6. Si aucune formation ne correspond aux critères, dis-le clairement
7. Adapte le ton : jeunes=dynamique ; experts=concis ; fragiles=rassurant ; RH=professionnel
8. Ne mentionne jamais le prénom ou le nom de la personne
9. Si manque d'infos, pose UNE seule question et laisse formations:[]
10. Ne recommande jamais deux fois la même formation (même id). Le champ "titre" DOIT être le titre exact du catalogue. Explique pourquoi chaque formation correspond dans le champ "message".
11. quick_replies = questions liées aux formations recommandées (ex: "Conditions d'admission ?", "Financement CPF ?", "Comparer ces formations", "Quels débouchés ?"). JAMAIS "Recommencer" si des formations ont déjà été recommandées.
12. Pour les questions de suivi (financement, admission, programme, débouchés, comparaison), réponds en détail dans "message" et laisse formations:[]. Utilise le contexte des formations déjà mentionnées dans la conversation.
13. Message d'accueil (bonjour, comment ça marche, etc.) sans profil connu → présente MACMIA chaleureusement, laisse formations:[], quick_replies=["📄 Je dépose mon CV","📋 Je remplis le questionnaire","💬 Je pose ma question"].

## FORMAT JSON STRICT (retourne UNIQUEMENT ce JSON, rien d'autre)
{json_format}

⚠️ IMPORTANT : Ta réponse doit commencer par {{ et se terminer par }}. Aucun texte avant ou après. JSON valide uniquement."""


# ── Prompt compact pour le mode RAG (économise ~4000 tokens) ─────────────────
def build_rag_system_prompt() -> str:
    """
    Prompt système allégé pour le endpoint /rag/chat.
    N'inclut pas les personas ni les descriptions complètes du catalogue,
    pour laisser de la place au profil utilisateur + contexte RAG data.gouv.fr.
    """
    # Catalogue en liste texte — plus facile à suivre pour llama3.2 qu'un JSON imbriqué
    lines = []
    for f in FORMATIONS:
        cpf_tag = "CPF" if f.get("rncp_eligible_cpf") else ""
        fins = " ".join(f.get("fin") or [])
        funding = " | ".join(filter(None, [cpf_tag, fins]))
        lines.append(
            f"ID={f['id']} | {f['titre']} | {f['ecole']} | {f['theme']} | "
            f"{f['format']} | {f['niveau']} | {funding} | {f['reg']}"
        )
    catalogue_list = "\n".join(lines)
    n = len(FORMATIONS)

    # Exemples concrets avec 2 vraies formations
    ex1 = FORMATIONS[0]
    ex2 = FORMATIONS[min(4, n - 1)]

    return f"""Tu es MACMIA, conseiller expert en formation IA, Data et Industrie du Futur.

## CATALOGUE IMT ({n} formations)
{catalogue_list}

## TÂCHE
Lis le profil de l'utilisateur et sélectionne 2 à 4 formations ci-dessus adaptées à son besoin.

## FORMAT DE RÉPONSE — JSON uniquement, rien d'autre
{{
  "message": "Explication courte : pourquoi ces formations correspondent au profil",
  "formations": [{{"id": {ex1['id']}, "titre": "{ex1['titre']}"}}, {{"id": {ex2['id']}, "titre": "{ex2['titre']}"}}],
  "quick_replies": ["Financement CPF ?", "Conditions d'admission ?", "Comparer ces formations"],
  "persona_id": null,
  "persona_confidence": 0.0,
  "profile_tags": [],
  "profile_name": "",
  "profile_role": ""
}}

## RÈGLES
- Utilise UNIQUEMENT les IDs entiers du catalogue (1 à {n})
- Ne mentionne jamais le prénom ou nom
- formations:[] uniquement si question de suivi sans nouveau profil

⚠️ Commence par {{ et termine par }}. JSON valide uniquement."""


# ── Nettoyage surrogates (caractères Unicode invalides) ───────────────────────
def _sanitize(obj):
    """Nettoie récursivement les surrogates Unicode dans les valeurs string."""
    if isinstance(obj, str):
        return obj.encode("utf-8", errors="replace").decode("utf-8")
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(i) for i in obj]
    return obj


# ── Parser JSON robuste ───────────────────────────────────────────────────────
def parse_json_response(raw: str) -> dict:
    """
    Parse la réponse brute du LLM en 3 passes successives.
    Les LLMs locaux ont tendance à ajouter du texte autour du JSON.
    """
    # Nettoyage initial + suppression des surrogates Unicode invalides
    raw = raw.strip()
    raw = raw.encode("utf-8", errors="replace").decode("utf-8")  # élimine \uDxxx
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```", "", raw)
    raw = raw.strip()

    # Passe 1 : parse direct
    try:
        return _sanitize(json.loads(raw))
    except json.JSONDecodeError:
        pass

    # Passe 2 : extraire le premier bloc JSON complet { ... }
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return _sanitize(json.loads(match.group()))
        except json.JSONDecodeError:
            pass

    # Passe 3 : extraire les champs clés par regex (JSON tronqué ou malformé)
    result = {
        "message": "",
        "formations": [],
        "quick_replies": ["Voir les formations", "Recommencer"],
        "persona_id": None,
        "persona_confidence": 0.0,
        "profile_tags": [],
        "profile_name": "",
        "profile_role": "",
    }
    msg_match = re.search(
        r'"message"\s*:\s*"([\s\S]*?)(?:"\s*,\s*"(?:formations|quick_replies|persona_id|profile)|"\s*\})',
        raw
    )
    if msg_match:
        result["message"] = (
            msg_match.group(1)
            .replace("\\n", "\n")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )
    # Tenter aussi d'extraire les formations si présentes
    formations_match = re.search(r'"formations"\s*:\s*(\[[\s\S]*?\])', raw)
    if formations_match:
        try:
            result["formations"] = json.loads(formations_match.group(1))
        except json.JSONDecodeError:
            pass
    quick_match = re.search(r'"quick_replies"\s*:\s*(\[[\s\S]*?\])', raw)
    if quick_match:
        try:
            result["quick_replies"] = json.loads(quick_match.group(1))
        except json.JSONDecodeError:
            pass
    if result["message"] or result["formations"]:
        return result

    # Passe 4 : fallback total — message générique mais jamais d'erreur visible
    logger.warning(f"Impossible de parser la réponse JSON. Raw: {raw[:300]}")
    return {
        "message": "Voici les formations sélectionnées pour votre profil. N'hésitez pas à cliquer sur chacune pour consulter les détails, conditions d'admission et modalités de financement.",
        "formations": [],
        "quick_replies": ["Conditions d'admission ?", "Financement CPF ?", "Comparer ces formations", "Quels débouchés ?"],
        "persona_id": None,
        "persona_confidence": 0.0,
        "profile_tags": [],
        "profile_name": "",
        "profile_role": "",
    }


# ── Conversion de l'historique JS → LangChain messages ──────────────────────
def history_to_langchain(history: list[dict]) -> list:
    """
    Convertit l'historique [{role:'user'|'assistant', content:'...'}]
    en liste de messages LangChain.
    """
    messages = []
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


# ── Déduplication des phrases répétées (comportement fréquent des LLMs locaux) ──
def _dedup_sentences(text: str) -> str:
    """Supprime les phrases consécutives identiques dans le message du LLM."""
    if not text:
        return text
    # Découper sur les fins de phrase ou les sauts de ligne
    parts = re.split(r'(?<=[.!?])\s+|\n', text)
    result, prev_clean = [], ""
    for p in parts:
        clean = p.strip().lower()
        if clean and clean != prev_clean:
            result.append(p.strip())
            prev_clean = clean
    return "\n".join(result) if "\n" in text else " ".join(result)


# ── Appel principal : recommandation / chat ───────────────────────────────────
async def call_main_llm(history: list[dict]) -> dict:
    """
    Prend l'historique complet et retourne le dict JSON parsé.
    Pré-filtre le catalogue et injecte un profil synthétisé quand des réponses Q&A sont détectées.
    """
    # ── Détection profil + pré-filtrage catalogue ────────────────────────────
    answers_lower, answers_list = _extract_qa_profile(history)
    if answers_lower:
        filtered_formations = _prefilter_formations(answers_lower, answers_list)
        profile_summary = _build_profile_summary(answers_list)
        logger.info(f"Profil détecté — catalogue réduit à {len(filtered_formations)}/{len(FORMATIONS)} formations")
        system_prompt = build_system_prompt(
            formations_subset=filtered_formations,
            profile_summary=profile_summary,
        )
    else:
        system_prompt = build_system_prompt()

    lc_history = history_to_langchain(history)

    # Construction du prompt avec historique
    # Le système est injecté comme SystemMessage, l'historique suit
    messages = [SystemMessage(content=system_prompt)] + lc_history

    try:
        provider = f"Anthropic/{settings.ANTHROPIC_MODEL}" if settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY else f"Ollama/{settings.MAIN_MODEL}"
        logger.info(f"Appel {provider} — {len(lc_history)} messages dans l'historique")
        response = await llm_main.ainvoke(messages)
        raw = response.content.encode("utf-8", errors="replace").decode("utf-8")
        logger.debug(f"Réponse brute ({len(raw)} chars): {raw[:200]}")
        result = parse_json_response(raw)

        # Dédupliquer les formations par ID et enrichir avec formation_data complet
        # (le LLM retourne {"id": N, "titre": "..."} — on injecte les données complètes
        #  pour que le frontend puisse afficher la carte sans lookup JS type-unsafe)
        if result.get("formations"):
            seen = set()
            deduped = []
            for f in result["formations"]:
                if not isinstance(f, dict):  # llama3.2 retourne parfois [1, 2, 3]
                    continue
                fid = f.get("id") or f.get("formation_id")
                fid_key = str(fid)
                if fid_key not in seen:
                    seen.add(fid_key)
                    # Enrichir avec formation_data si pas déjà présent
                    if not f.get("formation_data"):
                        full = next(
                            (cat for cat in FORMATIONS if str(cat["id"]) == fid_key),
                            None
                        )
                        if full:
                            ecole_lower = (full.get("ecole") or "").lower()
                            _IMT_KW = (
                                "imt", "mines-télécom", "mines-telecom",
                                "télécom paris", "telecom paris",
                                "télécom sudparis", "telecom sudparis",
                                "eurecom",
                            )
                            src = "imt" if any(kw in ecole_lower for kw in _IMT_KW) else "rag"
                            f = {
                                "id": full["id"],
                                "formation_data": {**full, "source": src},
                                "raison_match": f.get("titre", full.get("titre", "")),
                            }
                    deduped.append(f)
            result["formations"] = deduped

        # Garantir que le champ "message" est toujours présent
        if not result.get("message"):
            result["message"] = "Voici les formations recommandées pour votre profil :"

        # Retry automatique si aucune formation recommandée malgré un profil fourni
        # Ne pas retenter si c'est une question de suivi (après au moins un échange)
        last_user = next((m.content for m in reversed(lc_history) if hasattr(m, 'content') and m.__class__.__name__ == 'HumanMessage'), "")
        # Marqueurs stricts : uniquement présents dans une soumission de profil/CV, jamais dans une question de suivi
        CV_SUBMISSION_MARKERS = ("Voici mon CV", "mon CV :", "[CV de l'utilisateur]", "Réponses au questionnaire", "brique technique prioritaire")
        conversation_established = len(lc_history) >= 2  # dès qu'il y a eu au moins 1 réponse IA → suivi possible
        is_followup = conversation_established or (
            len(last_user.strip()) < 300
            and not any(m in last_user for m in CV_SUBMISSION_MARKERS)
        )
        if not result.get("formations") and lc_history and not is_followup:
            logger.warning("Aucune formation retournée — retry avec historique complet")
            # Retry avec l'historique complet pour ne pas perdre le contexte des formations précédentes
            import re as _re
            last_user_clean = _re.sub(r'Voici mon CV \(extrait\) :.*?---', '', last_user, flags=_re.DOTALL).strip()
            if not last_user_clean:
                last_user_clean = last_user[:500]
            retry_messages = (
                [SystemMessage(content=system_prompt)]
                + lc_history[:-1]  # historique sans le dernier message user
                + [HumanMessage(content=(
                    last_user_clean[:1500] +
                    "\n\nATTENTION : tu n'as retourné aucune formation. "
                    "Recommande OBLIGATOIREMENT 2 à 3 formations qui respectent les critères ci-dessus, "
                    "en priorité les formations IMT partenaires, puis CPF si besoin. Inclus-les maintenant."
                ))]
            )
            retry_response = await llm_main.ainvoke(retry_messages)
            retry_result = parse_json_response(retry_response.content.encode("utf-8", errors="replace").decode("utf-8"))
            if retry_result.get("formations"):
                retry_result.setdefault("message", "Voici les formations recommandées pour votre profil :")
                # Enrichir les formations du retry également
                enriched = []
                for f in retry_result["formations"]:
                    fid = str(f.get("id") or f.get("formation_id") or "")
                    if not f.get("formation_data") and fid:
                        full = next((c for c in FORMATIONS if str(c["id"]) == fid), None)
                        if full:
                            ecole_lower = (full.get("ecole") or "").lower()
                            _IMT_KW = (
                                "imt", "mines-télécom", "mines-telecom",
                                "télécom paris", "telecom paris",
                                "télécom sudparis", "telecom sudparis",
                                "eurecom",
                            )
                            src = "imt" if any(kw in ecole_lower for kw in _IMT_KW) else "rag"
                            f = {"id": full["id"], "formation_data": {**full, "source": src},
                                 "raison_match": f.get("titre", full.get("titre", ""))}
                    enriched.append(f)
                retry_result["formations"] = enriched
                return retry_result

        # ── Enforcement règle #13 : pas de formations sur questions de suivi ────
        # llama3.2 (3B) ignore souvent l'instruction — on l'applique en post-processing.
        # Ne s'active que quand la conversation est ÉTABLIE (>= 2 échanges complets).
        WANTS_NEW_RECO = (
            "autre formation", "autres formations", "plus de formations",
            "d'autres formations", "nouvelles formations", "recommande",
            "cherche une formation", "cherche des formations",
            "besoin d'une formation", "besoin de formation",
            "recommencer", "nouveau profil", "changer de domaine",
            "différent", "autres options", "quelles formations",
        )
        if conversation_established and result.get("formations"):
            is_short_followup = (
                len(last_user.strip()) < 300
                and not any(m in last_user for m in CV_SUBMISSION_MARKERS)
            )
            wants_new = any(t in last_user.lower() for t in WANTS_NEW_RECO)
            if is_short_followup and not wants_new:
                result["formations"] = []
                logger.info("ℹ️  Règle #13 enforcée — formations supprimées (question de suivi)")

        # Nettoyer les phrases en double dans le message (comportement fréquent des LLMs locaux)
        if result.get("message"):
            result["message"] = _dedup_sentences(result["message"])

        return result

    except Exception as e:
        logger.error(f"Erreur LLM principal: {e}")
        return {
            "message": "⚠️ Le modèle IA n'est pas disponible. Vérifiez votre configuration : ANTHROPIC_API_KEY dans .env (si LLM_PROVIDER=anthropic) ou qu'Ollama est lancé (`ollama serve`) si LLM_PROVIDER=ollama.",
            "formations": [],
            "quick_replies": ["Réessayer", "Voir le catalogue"],
            "persona_id": None,
            "persona_confidence": 0.0,
            "profile_tags": [],
            "profile_name": "",
            "profile_role": "",
        }


# ── Génération message pour formations pré-sélectionnées ──────────────────────
async def call_recommendation_message_llm(
    history: list[dict],
    formations_context: str,
    profile_summary: str = "",
) -> dict:
    """
    Génère un message d'explication structuré pour des formations déjà sélectionnées.
    Le LLM NE choisit PAS les formations — il écrit uniquement l'explication.
    """
    profile_block = f"\nPROFIL UTILISATEUR :\n{profile_summary}\n" if profile_summary else ""

    system = f"""Tu es MACMIA, conseiller expert en formation IA, Data et Industrie du Futur (IMT / France 2030).
{profile_block}
FORMATIONS PRÉSÉLECTIONNÉES :
{formations_context}

Rédige un message de recommandation structuré en **markdown** qui :
1. Accroche : 1 phrase qui résume le profil et l'enjeu de montée en compétences
2. Pour chaque formation (2-3 max) : 1-2 phrases expliquant pourquoi elle correspond — mention du format, RNCP, CPF si applicable
3. Conclusion : 1 phrase invitant à consulter les détails (prix, planning, admission)

Ton : professionnel, direct, bienveillant. Pas de liste à puces sauf pour les formations.
Longueur : 80-150 mots.

⚠️ Retourne UNIQUEMENT ce JSON (commence par {{ finit par }}) :
{{"message":"texte en **markdown**","quick_replies":["Conditions d'admission ?","Financement CPF ?","Comparer ces formations","Quels débouchés métiers ?"],"persona_id":null,"persona_confidence":0.0,"profile_tags":[],"profile_name":"","profile_role":""}}"""

    lc_history = history_to_langchain(history)
    recent = lc_history[-4:] if len(lc_history) > 4 else lc_history

    try:
        response = await asyncio.wait_for(
            llm_main.ainvoke([SystemMessage(content=system)] + recent),
            timeout=45.0,
        )
        raw = response.content.encode("utf-8", errors="replace").decode("utf-8")
        result = parse_json_response(raw)
        result.setdefault("formations", [])
        result.setdefault("quick_replies", ["Conditions d'admission ?", "Financement CPF ?", "Comparer ces formations", "Quels débouchés ?"])

        # Garantir un message jamais vide
        if not result.get("message") or len(result["message"].strip()) < 20:
            result["message"] = _build_fallback_message(formations_context, profile_summary)
        else:
            result["message"] = _dedup_sentences(result["message"])
        return result
    except asyncio.TimeoutError:
        logger.warning("Timeout LLM recommendation (45s) — utilisation du fallback structuré")
        return {
            "message": _build_fallback_message(formations_context, profile_summary),
            "formations": [],
            "quick_replies": ["Conditions d'admission ?", "Financement CPF ?", "Comparer ces formations"],
            "persona_id": None, "persona_confidence": 0.0,
            "profile_tags": [], "profile_name": "", "profile_role": "",
        }
    except Exception as e:
        logger.error(f"Erreur call_recommendation_message_llm: {e}")
        return {
            "message": _build_fallback_message(formations_context, profile_summary),
            "formations": [],
            "quick_replies": ["Conditions d'admission ?", "Financement CPF ?", "Comparer ces formations"],
            "persona_id": None, "persona_confidence": 0.0,
            "profile_tags": [], "profile_name": "", "profile_role": "",
        }


def _build_fallback_message(formations_context: str, profile_summary: str = "") -> str:
    """
    Construit un message de recommandation structuré sans LLM,
    à partir du contexte des formations sélectionnées.
    """
    lines = [l.strip() for l in formations_context.splitlines() if l.strip()]
    n = len(lines)
    if n == 0:
        return "Voici les formations sélectionnées pour votre profil. Consultez chaque fiche pour les détails, prix et conditions d'admission."

    intro = "Sur la base de votre profil, voici les formations les mieux adaptées à votre projet :"
    body_parts = []
    for line in lines[:3]:
        # Extraire le titre (2e segment après [source])
        parts = line.split("|")
        titre = parts[1].strip() if len(parts) > 1 else line
        cpf = "✓ CPF" in line
        cpf_tag = " — **éligible CPF**" if cpf else ""
        body_parts.append(f"- **{titre}**{cpf_tag}")

    body = "\n".join(body_parts)
    footer = "\nCliquez sur chaque formation pour consulter le programme, les conditions d'admission et les modalités de financement."
    return f"{intro}\n\n{body}{footer}"


# ── Appel extraction CV (modèle léger) ───────────────────────────────────────
EXTRACTION_SYSTEM = """Tu es un extracteur de CV. Analyse le texte du CV fourni et retourne UNIQUEMENT un JSON avec cette structure exacte :
{"nom":"...","poste_actuel":"...","niveau_etudes":"...","annees_experience":0,"competences_cles":["...","...","..."]}

Règles :
- Si une information est absente, utilise null ou 0
- annees_experience : nombre entier estimé
- competences_cles : 3 à 5 compétences principales détectées
- Réponds UNIQUEMENT avec le JSON, rien d'autre"""

async def call_extraction_llm(cv_text: str) -> dict:
    """
    Extrait les informations structurées d'un CV via le modèle léger.
    """
    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM),
        HumanMessage(content=f"CV à analyser :\n\n{cv_text[:3000]}"),  # Limiter la taille
    ]

    try:
        logger.info(f"Extraction CV avec {settings.EXTRACTION_MODEL}")
        response = await llm_extract.ainvoke(messages)
        raw = response.content.encode("utf-8", errors="replace").decode("utf-8")

        # Parser le JSON retourné
        raw = raw.strip()
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```", "", raw)

        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group())

        return {"nom": None, "poste_actuel": None, "niveau_etudes": None,
                "annees_experience": 0, "competences_cles": []}

    except Exception as e:
        logger.error(f"Erreur extraction CV: {e}")
        return {"nom": None, "poste_actuel": None, "niveau_etudes": None,
                "annees_experience": 0, "competences_cles": []}


# ── Génération questions d'interview CV ──────────────────────────────────────
INTERVIEW_SYSTEM = """Tu es un conseiller en orientation formation expert. Tu dois générer 4 questions d'interview HAUTEMENT PERSONNALISÉES à partir du CV fourni.

ÉTAPE 1 — Analyse silencieuse du CV :
Identifie mentalement : secteur d'activité, niveau d'expérience, compétences techniques déjà présentes, type de poste actuel, lacunes visibles, orientation probable.

ÉTAPE 2 — Règles de personnalisation STRICTES :
- NE pose PAS de question dont la réponse est déjà évidente dans le CV (ex: ne demande pas le niveau technique à un ingénieur senior Python, ne demande pas le domaine à quelqu'un dont le CV est entièrement Data)
- Chaque question doit être spécifique au profil lu : mentionne le secteur, le poste ou les compétences détectées dans la formulation
- Les chips doivent être des options RÉALISTES pour ce profil précis, pas des listes génériques
- Ne mentionne jamais le prénom, le nom ni aucune donnée personnelle

ÉTAPE 3 — Objectif des questions :
Chaque question doit réduire l'incertitude sur UNE dimension clé pour choisir la bonne formation IMT :
- Ambition de montée en compétences (expert technique vs manager vs stratège)
- Urgence et contraintes de temps (formation courte intensive vs longue certifiante)
- Contraintes financières réelles (CPF disponible ? employeur impliqué ?)
- Priorité personnelle (certification reconnue vs compétences opérationnelles rapides vs réseau grandes écoles)

Retourne UNIQUEMENT ce JSON valide :
{"questions":[{"q":"question personnalisée ?","chips":["Option A adaptée","Option B adaptée","Option C adaptée"]},...]}"

Exemple pour un Data Engineer senior :
- Mauvaise question : "Quel est votre niveau en Data ?" (déjà évident)
- Bonne question : "Avec votre expérience en pipelines de données, souhaitez-vous évoluer vers l'architecture de systèmes IA ou piloter une équipe Data ?"
  chips: ["Architecte IA / MLOps", "Lead Data / Management", "Expert technique pur", "Reconversion vers le conseil"]"""

async def call_interview_questions_llm(cv_text: str, cv_data: dict) -> list[dict]:
    """
    Génère les questions d'interview personnalisées à partir du CV.
    """
    # Construire un contexte riche même si cv_data est vide
    cv_snippet = cv_text[:2500].strip()

    context = f"""Voici le CV à analyser :

{cv_snippet}

Génère 5 questions d'interview personnalisées et intelligentes pour orienter cette personne vers les meilleures formations IMT.
Les questions doivent être adaptées à CE profil spécifique — pas des questions génériques applicables à n'importe qui."""

    messages = [
        SystemMessage(content=INTERVIEW_SYSTEM),
        HumanMessage(content=context),
    ]

    try:
        response = await llm_main.ainvoke(messages)
        raw = response.content.encode("utf-8", errors="replace").decode("utf-8").strip()
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```", "", raw)

        # Passe 1 : parse direct
        try:
            data = json.loads(raw)
            questions = data.get("questions", [])
            if questions:
                return questions
        except json.JSONDecodeError:
            pass

        # Passe 2 : extraire le bloc JSON
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            data = json.loads(match.group())
            return data.get("questions", [])

        return []

    except Exception as e:
        logger.error(f"Erreur génération questions: {e}")
        return []


# ── Question de bridging (Je ne sais pas) ────────────────────────────────────
BRIDGING_SYSTEM = """Tu aides quelqu'un à choisir une formation. Il hésite encore.
Génère UNE seule question très ciblée pour débloquer son choix.
Retourne UNIQUEMENT : {"q":"ta question","chips":["Option A","Option B","Option C"]}"""

async def call_bridging_llm(cv_text: str, answered_so_far: str) -> dict:
    """Génère une question de relance quand l'utilisateur dit 'Je ne sais pas'."""
    messages = [
        SystemMessage(content=BRIDGING_SYSTEM),
        HumanMessage(content=f"CV :\n{cv_text[:800]}\n\nRéponses : {answered_so_far}\n\nGénère la relance."),
    ]
    try:
        response = await llm_main.ainvoke(messages)
        raw = response.content.encode("utf-8", errors="replace").decode("utf-8").strip()
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```", "", raw)
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group())
        return {"q": "Quel est votre principal objectif professionnel ?", "chips": ["Changer de métier", "Monter en compétences", "Obtenir une certification"]}
    except Exception as e:
        logger.error(f"Erreur bridging: {e}")
        return {"q": "Qu'est-ce qui vous attire le plus dans l'IA ?", "chips": ["Changer de métier", "Monter en compétences", "Valider des compétences"]}
