"""
rag/retriever.py — Recherche sémantique dans ChromaDB
Chargé une seule fois au démarrage du serveur (singleton).
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

CHROMA_DIR  = str(Path(__file__).parent.parent / "chroma_db")
EMBED_MODEL = "nomic-embed-text"
COLLECTION  = "macmia_formations"

_db = None   # Singleton ChromaDB


def get_db():
    """Charge ChromaDB une seule fois et le met en cache."""
    global _db
    if _db is not None:
        return _db

    # Vérifier que la base existe
    if not os.path.exists(CHROMA_DIR):
        logger.warning(
            f"ChromaDB introuvable : {CHROMA_DIR}\n"
            "Lance d'abord : python rag/ingest.py"
        )
        return None

    try:
        from langchain_chroma import Chroma

        # Récupérer la config
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from config import settings

        # Choisir le modèle d'embeddings selon le fournisseur LLM
        if False:  # Ollama désactivé
            from langchain_ollama import OllamaEmbeddings
            embeddings = OllamaEmbeddings(
                model=EMBED_MODEL,
                base_url=settings.OLLAMA_BASE_URL
            )
            logger.info(f"Embeddings: Ollama/{EMBED_MODEL}")
        else:
            from langchain_huggingface import HuggingFaceEmbeddings
            from langchain.embeddings.base import Embeddings
            from llama_cpp import Llama
            class LlamaCppEmbeddings(Embeddings):
                def __init__(self):
                    self.model = Llama(
                        model_path="/home/docker/models/nomic-embed-text-v1.5.Q4_K_M.gguf",
                        embedding=True, n_gpu_layers=33, n_ctx=2048, verbose=False
                    )
                def embed_documents(self, texts):
                    return [self.model.create_embedding(f"search_document: {t}")["data"][0]["embedding"] for t in texts]
                def embed_query(self, text):
                    return self.model.create_embedding(f"search_query: {text}")["data"][0]["embedding"]
            embeddings = LlamaCppEmbeddings()
            logger.info("Embeddings: HuggingFace/all-MiniLM-L6-v2")
        _db = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION
        )
        count = _db._collection.count()
        logger.info(f"✅ ChromaDB chargé — {count:,} formations indexées")
        return _db

    except Exception as e:
        logger.error(f"Erreur chargement ChromaDB : {e}")
        return None


def is_ready() -> bool:
    """Retourne True si la base vectorielle est disponible."""
    return os.path.exists(CHROMA_DIR) and get_db() is not None


# Formations hors-sujet à exclure des résultats RAG
_BLACKLIST = [
    # Bureautique & outils génériques
    "powerpoint", "excel", "word", "outlook", "teams", "office",
    "bureautique", "photoshop", "illustrator", "indesign",
    "tosa", "pix ", "mos excel", "mos word",
    # Permis & transport
    "permis de conduire", "permis b", "permis c", "caces",
    "transport de personnes", "transport de marchandises",
    "conducteur routier", "chauffeur",
    # RH & admin généralistes
    "bilan de compétences", "secrétariat",
    "assistant de direction", "assistant administratif",
    "comptabilité générale", "paie", "bulletin de salaire",
    "ressources humaines généraliste", "rh généraliste",
    "gestion administrative", "secrétaire médical",
    # Langues & soft skills génériques
    "anglais général", "langue générale", "fle ",
    "français langue étrangère", "espagnol général",
    "prise de parole", "gestion du stress", "sophrologie",
    "développement personnel", "confiance en soi",
    "communication interpersonnelle", "team building",
    # Santé & sécurité non-tech
    "secourisme", "sst ", "premiers secours", "psc1",
    "gestes et postures", "sauveteur secouriste",
    "habilitation électrique", "travail en hauteur",
    "incendie", "évacuation", "epi ",
    # BTP & industrie non-numérique
    "maçonnerie", "plomberie", "électricité bâtiment",
    "charpente", "menuiserie", "peinture bâtiment",
    "carrelage", "couverture", "génie civil",
    # Commerce & vente généraliste
    "techniques de vente", "prospection commerciale",
    "relation client générale", "merchandising",
    "accueil physique", "réception hôtel",
    # Blocs partiels
    "bloc de compétences", "bloc de competences",
    # Autres hors-scope
    "cuisine", "pâtisserie", "restauration",
    "coiffure", "esthétique", "bien-être",
    "aide à domicile", "auxiliaire de vie",
    "petite enfance", "bafa",
]


def search_formations(
    query: str,
    region: Optional[str] = None,
    cpf_only: bool = False,
    niveau: Optional[str] = None,
    top_k: int = 5,
) -> list[Document]:
    """
    Recherche sémantique dans le catalogue CPF.
    Enrichit la requête avec des mots-clés IA/Data et filtre les hors-sujets.
    """
    db = get_db()
    if db is None:
        return []

    # ── Enrichir la requête pour guider les embeddings vers IA/Data ──────
    ia_boost = (
        " intelligence artificielle machine learning data science python "
        "deep learning nlp mlops data engineer data scientist algorithme "
        "modèle IA RNCP certification professionnelle formation numérique"
    )
    enriched_query = query + ia_boost

    # ── Construction des filtres Chroma ───────────────────────────────────
    filters = []
    if cpf_only:
        filters.append({"cpf": {"$in": ["true", "True", "1", "Oui", "oui"]}})
    if region:
        filters.append({"region": {"$contains": region}})
    if niveau:
        niv = niveau.strip().upper()
        if not niv.startswith("NIVEAU"):
            niv = f"NIVEAU {niv}"
        filters.append({"niveau": {"$contains": niv}})

    # Récupérer plus de résultats pour compenser le filtrage post-hoc
    fetch_k = min(top_k * 3, 20)
    kwargs = {"k": fetch_k}
    if len(filters) == 1:
        kwargs["filter"] = filters[0]
    elif len(filters) > 1:
        kwargs["filter"] = {"$and": filters}

    try:
        raw_results = db.similarity_search(enriched_query, **kwargs)
    except Exception as e:
        logger.warning(f"Recherche avec filtre échouée ({e}), fallback sans filtre")
        try:
            raw_results = db.similarity_search(enriched_query, k=fetch_k)
        except Exception as e2:
            logger.error(f"Recherche vectorielle échouée : {e2}")
            return []

    # ── Whitelist : mots-clés IA/Data/Tech obligatoires ─────────────────────
    _WHITELIST = [
        "data", "intelligence artificielle", "ia ", " ia,", "machine learning",
        "deep learning", "python", "cloud", "devops", "mlops", "nlp",
        "big data", "data science", "data engineer", "data analyst",
        "cybersécurité", "cyber", "réseau", "5g", "iot", "numérique",
        "digital", "informatique", "algorithme", "développeur",
        "logiciel", "applicatif", "système d'information", "si ",
        "rncp38", "rncp37", "rncp36", "rncp41", "rncp35",
        "industrie 4.0", "industrie du futur", "robotique", "automatisation",
        "transformation digitale", "transformation numérique",
        "manager ia", "chef de projet ia", "architecte",
        "blockchain", "métavers", "réalité augmentée", "réalité virtuelle",
    ]
    # ── Filtrer les formations hors-sujet ─────────────────────────────────
    filtered = []
    for doc in raw_results:
        titre = doc.metadata.get("titre_formation", "").lower()
        cert  = doc.metadata.get("titre_certification", "").lower()
        text  = (titre + " " + cert + " " + doc.page_content[:200]).lower()
        # Exclure blacklist
        if any(kw in text for kw in _BLACKLIST):
            continue
        # Inclure uniquement si whitelist match
        if any(kw in text for kw in _WHITELIST):
            filtered.append(doc)

    # Si trop peu de résultats après filtrage, garder les non-filtrés
    if len(filtered) < 2:
        logger.warning("Filtrage trop agressif — retour aux résultats bruts")
        filtered = raw_results

    # Dédoublonner par titre et privilégier les docs avec département
    seen_titres = {}
    for doc in filtered:
        titre = doc.metadata.get("titre_formation", "").strip().lower()
        dept = str(doc.metadata.get("departement", "") or "")
        has_dept = dept.lower() not in ("nan", "", "none")
        if titre not in seen_titres:
            seen_titres[titre] = doc
        elif has_dept:
            existing_dept = str(seen_titres[titre].metadata.get("departement","") or "")
            if existing_dept.lower() in ("nan", "", "none"):
                seen_titres[titre] = doc
    deduped = list(seen_titres.values())
    return deduped[:top_k]


def format_context(docs: list[Document]) -> str:
    """
    Formate les documents récupérés en bloc de contexte
    à injecter dans le prompt système du LLM.
    """
    if not docs:
        return "Aucune formation trouvée dans la base RAG pour cette requête."

    lines = ["=== FORMATIONS CPF OFFICIELLES (data.gouv.fr — MAJ quotidienne) ===\n"]
    for i, doc in enumerate(docs, 1):
        m = doc.metadata
        lines.append(
            f"[Formation #{i}]\n"
            f"{doc.page_content}\n"
            f"{'─' * 50}"
        )
    return "\n".join(lines)


def get_stats() -> dict:
    """Retourne les statistiques de la base vectorielle."""
    if not os.path.exists(CHROMA_DIR):
        return {"ready": False, "message": "Base non indexée — lance python rag/ingest.py"}
    db = get_db()
    if db is None:
        return {"ready": False, "message": "Erreur chargement ChromaDB"}
    try:
        count = db._collection.count()
        return {
            "ready": True,
            "formations_indexed": count,
            "embed_model": EMBED_MODEL,
            "chroma_dir": CHROMA_DIR,
            "collection": COLLECTION,
        }
    except Exception as e:
        return {"ready": False, "message": str(e)}