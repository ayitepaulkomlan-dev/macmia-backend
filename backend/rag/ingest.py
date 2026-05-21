"""
rag/ingest.py — Pipeline d'ingestion data.gouv.fr → ChromaDB
=============================
Lance UNE SEULE FOIS (ou pour mettre à jour le catalogue).

Usage :
    cd backend
    python rag/ingest.py

Ce script :
  1. Télécharge le CSV du catalogue CPF depuis data.gouv.fr (~726 Mo)
  2. Filtre les formations IA / Data / Industrie du Futur (~15 000 lignes)
  3. Crée les embeddings avec nomic-embed-text (via Ollama)
  4. Indexe tout dans ChromaDB (base vectorielle locale)
"""

import os
import sys
import time
import requests
import pandas as pd
from pathlib import Path

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Configuration ─────────────────────────────────────────────────────────────
CHROMA_DIR   = str(Path(__file__).parent.parent / "chroma_db")
DATA_DIR     = str(Path(__file__).parent.parent / "data")
CSV_PATH     = os.path.join(DATA_DIR, "mcf_offre.csv")
EMBED_MODEL  = "nomic-embed-text"
OLLAMA_URL   = "http://localhost:11434"
COLLECTION   = "macmia_formations"
BATCH_SIZE   = 200   # Formations par batch (adapter selon la RAM)

# URL du fichier CSV sur data.gouv.fr (MAJ quotidienne)
DATA_GOUV_CSV_URL = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "r/205a72c5-725a-40c0-9c39-073454bdd553"
)

# Mots-clés pour filtrer IA / Data / Industrie du Futur
KEYWORDS_IA = [
    # IA & Machine Learning
    "intelligence artificielle", "machine learning", "deep learning",
    "apprentissage automatique", "apprentissage profond", "réseau de neurones",
    "ia générative", "llm", "large language model", "prompt engineering",
    "nlp", "traitement du langage", "traitement langage naturel",
    "vision artificielle", "vision par ordinateur", "computer vision",
    "mlops", "data science", "data scientist",
    # Data
    "data engineer", "data analyst", "big data", "données massives",
    "analyse de données", "analyse données", "science des données",
    "business intelligence", "power bi", "tableau", "data visualisation",
    "data warehouse", "data lake", "pipeline de données",
    "bases de données", "sql avancé", "nosql",
    # Industrie du Futur
    "industrie 4.0", "industrie du futur", "cobotique", "robotique",
    "automatisation industrielle", "jumeaux numériques", "iot industriel",
    "maintenance prédictive", "systèmes embarqués",
    # Cybersécurité & Cloud
    "cybersécurité", "cyber sécurité", "sécurité informatique",
    "cloud computing", "devops", "mlops", "kubernetes", "docker",
    # Reconversion / générique IA
    "python pour", "python data", "transformation digitale",
    "transformation numérique", "compétences numériques ia",
]

# Formations hors-sujet à EXCLURE lors de l'ingestion
KEYWORDS_EXCLUDE = [
    # Bureautique / Office
    "powerpoint", "excel avancé", "excel vba", "excel tableaux",
    "word avancé", "outlook", "teams formation", "office 365 bureautique",
    "bureautique", "photoshop", "illustrator", "indesign", "canva",
    # Permis / Bilan
    "permis de conduire", "bilan de compétences",
    # Fonctions support non-tech
    "secrétariat", "assistant de direction", "assistant administratif",
    "comptabilité générale", "comptabilité débutant", "gestion de la paie",
    "paie et charges", "rh généraliste", "ressources humaines généraliste",
    # Soft skills purs
    "prise de parole en public", "gestion du stress", "sophrologie",
    "cohésion d'équipe", "management général débutant",
    # Certifications bureautiques
    "tosa excel", "tosa word", "tosa powerpoint", "pix certification",
    "mos excel", "mos word", "mos powerpoint",
    # Langues générales
    "anglais général", "anglais débutant", "espagnol débutant",
    "français langue étrangère",
]

# Colonnes qu'on garde dans ChromaDB (métadonnées filtrables)
METADATA_COLS = {
    "numero_formation":              "id_formation",
    "code_rncp":                     "rncp",
    "nom_of":                        "organisme",
    "nom_region":                    "region",
    "nom_departement":               "departement",
    "libelle_niveau_sortie_formation": "niveau",
    "frais_ttc_tot_mean":            "prix",
    "nb_session_a_distance":         "nb_distanciel",
    "nombre_heures_total_mean":      "duree_heures",
    "intitule_formation":            "titre_formation",
    "intitule_certification":        "titre_certification",
    "code_rome_1":                   "rome_1",
    "code_rome_2":                   "rome_2",
    "code_rome_3":                   "rome_3",
}


# ── Étape 1 : Téléchargement ─────────────────────────────────────────────────
def download_dataset():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CSV_PATH):
        size_mb = os.path.getsize(CSV_PATH) / 1024 / 1024
        print(f"✅ CSV déjà présent ({size_mb:.0f} Mo) — {CSV_PATH}")
        print("   Pour forcer le re-téléchargement : supprime data/mcf_offre.csv")
        return

    print("📥 Téléchargement du catalogue CPF depuis data.gouv.fr...")
    print("   Taille estimée : ~726 Mo — patience (~5-15 min selon connexion)")

    r = requests.get(DATA_GOUV_CSV_URL, stream=True, timeout=300)
    r.raise_for_status()

    total = int(r.headers.get("content-length", 0))
    downloaded = 0
    start = time.time()

    with open(CSV_PATH, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                mb  = downloaded / 1024 / 1024
                elapsed = time.time() - start
                speed = mb / elapsed if elapsed > 0 else 0
                print(f"\r   {pct:.1f}% — {mb:.0f}/{total/1024/1024:.0f} Mo — {speed:.1f} Mo/s", end="")

    print(f"\n✅ Téléchargement terminé : {CSV_PATH}")


# ── Étape 2 : Chargement & filtrage ──────────────────────────────────────────
def load_and_filter() -> pd.DataFrame:
    print("\n📂 Chargement du CSV (peut prendre 1-2 min)...")

    # Essayer plusieurs encodages
    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(
                CSV_PATH, sep=";", encoding=enc,
                on_bad_lines="skip", low_memory=False,
                dtype=str  # Tout en string pour éviter les erreurs de type
            )
            print(f"✅ {len(df):,} lignes chargées (encodage: {enc})")
            print(f"   Colonnes disponibles : {list(df.columns[:10])}")
            break
        except Exception as e:
            print(f"   ⚠️  Encodage {enc} échoué : {e}")
            continue
    else:
        raise ValueError("Impossible de lire le CSV — vérifie le fichier téléchargé")

    # Colonnes textuelles à analyser pour le filtrage
    text_cols = [
        "intitule_formation", "intitule_certification",
        "domaine_sous_domaine", "objectif_formation",
        "contenu_formation", "modalite_pedagogiques",
    ]
    text_cols = [c for c in text_cols if c in df.columns]
    print(f"   Colonnes de filtrage : {text_cols}")

    # Construire le masque de filtrage
    mask = pd.Series(False, index=df.index)
    for col in text_cols:
        col_lower = df[col].fillna("").astype(str).str.lower()
        for kw in KEYWORDS_IA:
            mask |= col_lower.str.contains(kw, na=False)

    df_ia = df[mask].copy()
    print(f"✅ {len(df_ia):,} formations IA/Data filtrées (avant exclusions)")

    # ── Filtre négatif : exclure les formations hors-sujet ────────────────
    excl_mask = pd.Series(False, index=df_ia.index)
    for col in text_cols:
        col_lower = df_ia[col].fillna("").astype(str).str.lower()
        for kw in KEYWORDS_EXCLUDE:
            excl_mask |= col_lower.str.contains(kw, na=False)

    df_ia = df_ia[~excl_mask].copy()
    print(f"✅ {len(df_ia):,} formations après exclusion des hors-sujets")
    return df_ia


# ── Étape 3 : Conversion en Documents LangChain ───────────────────────────────
def make_documents(df: pd.DataFrame):
    from langchain_core.documents import Document

    docs = []
    for _, row in df.iterrows():
        # Texte principal du chunk (ce qui sera embeddi)
        content = "\n".join(filter(None, [
            f"Formation : {row.get('intitule_formation', '')}",
            f"Certification : {row.get('intitule_certification', '')} ({row.get('code_rncp', '')})",
            f"Organisme : {row.get('nom_of', '')}",
            f"Niveau : {row.get('libelle_niveau_sortie_formation', '')}",
            f"Domaine : {row.get('domaine_sous_domaine', '')}",
            f"Région : {row.get('nom_region', '')}",
            f"Département : {row.get('nom_departement', '')}",
            f"Durée : {row.get('duree_formation_heure', '')} heures",
            f"Prix : {row.get('prix_ttc_max', '')} €",
            f"CPF : {row.get('cpf_eligible', '')}",
            f"Modalité : {row.get('modalite_enseignement', '')}",
            f"Objectif : {str(row.get('objectif_formation', ''))[:400]}",
        ]))

        # Métadonnées filtrables (Chroma)
        metadata = {}
        for src_col, dest_key in METADATA_COLS.items():
            val = str(row.get(src_col, "") or "").strip()
            metadata[dest_key] = val[:200]  # Limiter la taille

        docs.append(Document(page_content=content, metadata=metadata))

    return docs


# ── Étape 4 : Indexation dans ChromaDB ───────────────────────────────────────
def index_documents(docs):
    from langchain_chroma import Chroma

    # Charger la config pour choisir les embeddings
    from config import settings

    print(f"\n🔢 Indexation de {len(docs):,} formations dans ChromaDB...")
    print(f"   Dossier ChromaDB : {CHROMA_DIR}")
    print(f"   Batch size       : {BATCH_SIZE}")
    print(f"   Durée estimée    : {len(docs) // BATCH_SIZE * 2}-{len(docs) // BATCH_SIZE * 5} min\n")

    # Choisir le modèle d'embeddings selon le fournisseur
    if False:  # Ollama désactivé — utilise HuggingFace
        # Embeddings Ollama (nomic-embed-text)
        from langchain_ollama import OllamaEmbeddings
        try:
            import httpx
            r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            models = [m["name"] for m in r.json().get("models", [])]
            if not any("nomic-embed-text" in m for m in models):
                print("❌ nomic-embed-text non trouvé dans Ollama !")
                print("   Lance : ollama pull nomic-embed-text")
                sys.exit(1)
            print(f"✅ Ollama OK — modèles : {models}")
        except Exception as e:
            print(f"❌ Ollama non accessible : {e}")
            print("   Lance : ollama serve")
            sys.exit(1)
        embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)
        print(f"   Modèle embeddings : Ollama/{EMBED_MODEL}")
    else:
        # Embeddings via llama-cpp-python (nomic-embed-text GGUF sur GPU)
        from langchain.embeddings.base import Embeddings
        from llama_cpp import Llama
        class LlamaCppEmbeddings(Embeddings):
            def __init__(self):
                print("   Chargement nomic-embed-text sur GPU...")
                self.model = Llama(
                    model_path="/home/docker/models/nomic-embed-text-v1.5.Q4_K_M.gguf",
                    embedding=True, n_gpu_layers=33, n_ctx=2048, verbose=False
                )
                print("   ✅ nomic-embed-text chargé sur GPU")
            def embed_documents(self, texts):
                return [self.model.create_embedding(f"search_document: {t}")["data"][0]["embedding"] for t in texts]
            def embed_query(self, text):
                return self.model.create_embedding(f"search_query: {text}")["data"][0]["embedding"]
        embeddings = LlamaCppEmbeddings()
        print("   Modèle embeddings : nomic-embed-text GPU")

    os.makedirs(CHROMA_DIR, exist_ok=True)
    db = None
    start = time.time()

    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i:i + BATCH_SIZE]
        n_batch = i // BATCH_SIZE + 1
        n_total = (len(docs) + BATCH_SIZE - 1) // BATCH_SIZE
        elapsed = time.time() - start
        eta = (elapsed / (i + 1)) * (len(docs) - i) if i > 0 else 0

        print(f"  Batch {n_batch:3d}/{n_total} — {i+len(batch):,}/{len(docs):,} formations"
              f" — {elapsed:.0f}s écoulées — ETA ~{eta:.0f}s")

        try:
            if db is None:
                db = Chroma.from_documents(
                    batch, embeddings,
                    persist_directory=CHROMA_DIR,
                    collection_name=COLLECTION
                )
            else:
                db.add_documents(batch)
        except Exception as e:
            print(f"    ⚠️  Erreur batch {n_batch}: {e} — on continue")
            continue

    total_time = time.time() - start
    count = db._collection.count() if db else 0
    print(f"\n✅ Indexation terminée en {total_time:.0f}s")
    print(f"   {count:,} formations indexées dans ChromaDB")
    return db


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("═" * 60)
    print("  MACMIA RAG — Ingestion catalogue CPF data.gouv.fr")
    print("═" * 60)

    # Vérifier si la base existe déjà
    if os.path.exists(CHROMA_DIR):
        print(f"\n⚠️  ChromaDB existe déjà : {CHROMA_DIR}")
        answer = input("   Re-indexer ? (o/n) : ").strip().lower()
        if answer != "o":
            print("   Annulé — base existante conservée.")
            return

    # Pipeline complet
    download_dataset()
    df_ia = load_and_filter()
    docs  = make_documents(df_ia)
    index_documents(docs)

    print("\n🎉 RAG prêt ! Lance le serveur : python main.py")
    print("   Endpoint RAG : http://localhost:8000/api/rag/chat")
    print("   Status RAG   : http://localhost:8000/api/rag/status")


if __name__ == "__main__":
    main()