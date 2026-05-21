"""
rag/ingest_enriched.py — Ré-indexation ChromaDB avec la base enrichie
======================================================================
Remplace ingest.py : utilise la base SQLite enrichie au lieu du CSV brut.

Chaque chunk contient maintenant :
  - Titre formation + certification + RNCP
  - Organisme + région + département
  - Niveau + modalité + durée + prix
  - Blocs de compétences développées
  - Métiers et débouchés accessibles
  - Lien catalogue + lien France Compétences
  - Objectif pédagogique

Usage :
    cd backend
    python rag/ingest_enriched.py
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from rag.db_schema import get_conn, DB_PATH

CHROMA_DIR  = str(Path(__file__).parent.parent / "chroma_db_enriched")
EMBED_MODEL = "nomic-embed-text"
COLLECTION  = "macmia_formations_enriched"
BATCH_SIZE  = 100   # Plus petit car les chunks sont plus longs


def build_chunk(row: dict) -> str:
    """
    Construit le texte du chunk à vectoriser.
    Plus riche = meilleure recherche sémantique.
    """
    parts = []

    # Identité formation
    if row.get("intitule_formation"):
        parts.append(f"Formation : {row['intitule_formation']}")
    if row.get("intitule_certification"):
        rncp = f" (RNCP {row['code_rncp']})" if row.get("code_rncp") else ""
        parts.append(f"Certification : {row['intitule_certification']}{rncp}")

    # Organisme et localisation
    if row.get("organisme"):
        parts.append(f"Organisme : {row['organisme']}")
    loc_parts = [x for x in [row.get("region"), row.get("departement")] if x and x != "nan"]
    if loc_parts:
        parts.append(f"Localisation : {' — '.join(loc_parts)}")

    # Caractéristiques pédagogiques
    if row.get("niveau"):
        parts.append(f"Niveau : {row['niveau']}")
    if row.get("modalite"):
        parts.append(f"Modalité : {row['modalite']}")
    if row.get("duree_affichee"):
        parts.append(f"Durée : {row['duree_affichee']}")
    if row.get("rythme"):
        parts.append(f"Rythme : {row['rythme']}")

    # Prix et financement
    if row.get("prix_affiche"):
        cpf = " — Éligible CPF" if row.get("cpf_eligible", "").lower() in ("oui", "true", "1") else ""
        parts.append(f"Prix : {row['prix_affiche']}{cpf}")

    # Public et prérequis
    if row.get("public_vise"):
        parts.append(f"Public visé : {row['public_vise']}")
    if row.get("prerequis"):
        parts.append(f"Prérequis : {row['prerequis']}")

    # Objectif pédagogique
    if row.get("objectif_general"):
        parts.append(f"Objectif : {str(row['objectif_general'])[:400]}")

    # ★ Blocs de compétences (cœur de la valeur ajoutée)
    if row.get("blocs_competences"):
        blocs = row["blocs_competences"].split(" | ")
        blocs_clean = [b.strip() for b in blocs if b.strip() and len(b.strip()) > 5]
        if blocs_clean:
            parts.append(f"Compétences développées : {' · '.join(blocs_clean[:8])}")

    # ★ Métiers et débouchés
    if row.get("metiers_debouches"):
        metiers = row["metiers_debouches"].split(" | ")
        metiers_clean = [m.strip() for m in metiers if m.strip() and len(m.strip()) > 3]
        if metiers_clean:
            parts.append(f"Métiers accessibles : {' · '.join(metiers_clean[:6])}")

    return "\n".join(parts)


def build_metadata(row: dict) -> dict:
    """Construit les métadonnées filtrables pour ChromaDB."""
    def safe(val, max_len=200):
        v = str(val or "").strip()
        return v[:max_len] if v and v != "nan" else ""

    return {
        "rncp":            safe(row.get("code_rncp")),
        "titre_formation": safe(row.get("intitule_formation"), 250),
        "titre_cert":      safe(row.get("intitule_certification"), 250),
        "organisme":       safe(row.get("organisme")),
        "region":          safe(row.get("region")),
        "departement":     safe(row.get("departement")),
        "niveau":          safe(row.get("niveau")),
        "modalite":        safe(row.get("modalite")),
        "duree":           safe(row.get("duree_affichee")),
        "prix":            safe(row.get("prix_affiche")),
        "prix_min":        str(row.get("prix_min") or ""),
        "cpf":             safe(row.get("cpf_eligible")),
        "lien_catalogue":  safe(row.get("lien_catalogue")),
        "lien_france_comp":safe(row.get("lien_france_comp")),
        "fiabilite":       str(row.get("fiabilite") or "1"),
        "source":          safe(row.get("source_enrichissement")),
    }


def ingest_enriched():
    print("═" * 60)
    print("  MACMIA RAG — Indexation base enrichie → ChromaDB")
    print("═" * 60)

    # Vérifier la base SQLite
    if not os.path.exists(DB_PATH):
        print(f"❌ Base SQLite introuvable : {DB_PATH}")
        print("   Lance d'abord : python rag/enrich.py --source all")
        sys.exit(1)

    conn = get_conn()

    # Récupérer toutes les formations enrichies via la vue
    rows = conn.execute("""
        SELECT * FROM v_formations_rag
        WHERE intitule_formation IS NOT NULL
          AND code_rncp IS NOT NULL
          AND code_rncp != ''
          AND code_rncp != 'nan'
        ORDER BY fiabilite DESC, code_rncp
    """).fetchall()

    conn.close()

    print(f"✅ {len(rows):,} formations enrichies récupérées depuis SQLite")

    # Convertir en dicts
    docs_data = [dict(row) for row in rows]

    # Construire les Documents LangChain
    from langchain_core.documents import Document
    docs = []
    for row in docs_data:
        content  = build_chunk(row)
        metadata = build_metadata(row)
        if len(content) > 50:  # Ignorer les chunks trop courts
            docs.append(Document(page_content=content, metadata=metadata))

    print(f"✅ {len(docs):,} documents préparés")
    print(f"   Exemple chunk :\n   {docs[0].page_content[:300]}...\n")

    # Vérifier ChromaDB existant
    if os.path.exists(CHROMA_DIR):
        answer = input(f"⚠️  ChromaDB enrichi existe déjà ({CHROMA_DIR}). Re-indexer ? (o/n) : ")
        if answer.lower() != "o":
            print("Annulé.")
            return

    # Vérifier Ollama
    import httpx
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        if not any("nomic-embed-text" in m for m in models):
            print("❌ nomic-embed-text non trouvé. Lance : ollama pull nomic-embed-text")
            sys.exit(1)
        print(f"✅ Ollama OK — {len(models)} modèles disponibles")
    except Exception as e:
        print(f"❌ Ollama non accessible : {e}")
        sys.exit(1)

    # Indexation
    from langchain_chroma import Chroma
    from langchain_ollama import OllamaEmbeddings

    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url="http://localhost:11434")
    os.makedirs(CHROMA_DIR, exist_ok=True)

    db     = None
    start  = time.time()
    n_total = (len(docs) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(docs), BATCH_SIZE):
        batch   = docs[i:i + BATCH_SIZE]
        n_batch = i // BATCH_SIZE + 1
        elapsed = time.time() - start
        eta     = (elapsed / (i + 1)) * (len(docs) - i) if i > 0 else 0
        print(f"  Batch {n_batch:3d}/{n_total} — {i+len(batch):,}/{len(docs):,}"
              f" — {elapsed:.0f}s — ETA ~{eta:.0f}s")
        try:
            if db is None:
                db = Chroma.from_documents(batch, embeddings,
                    persist_directory=CHROMA_DIR, collection_name=COLLECTION)
            else:
                db.add_documents(batch)
        except Exception as e:
            print(f"    ⚠️  Erreur batch {n_batch}: {e}")

    total = time.time() - start
    count = db._collection.count() if db else 0

    print(f"\n✅ Indexation terminée en {total:.0f}s")
    print(f"   {count:,} formations indexées dans {CHROMA_DIR}")
    print(f"\n🎉 Lance le serveur et teste :")
    print(f"   http://localhost:8000/api/rag/status_enriched")


if __name__ == "__main__":
    ingest_enriched()
