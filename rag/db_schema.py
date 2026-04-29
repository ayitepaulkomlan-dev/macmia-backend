"""
rag/db_schema.py — Création et gestion de la base SQLite enrichie
Lance une seule fois : python rag/db_schema.py

Tables :
  - formations        : données de base (CPF + RNCP fusionnées)
  - blocs_competences : blocs de compétences par RNCP
  - metiers_debouches : métiers accessibles après la formation
  - enrichissement    : prix, durée, modalité, lien catalogue (scraping)
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = str(Path(__file__).parent.parent / "data" / "formations_enrichies.db")

SCHEMA = """
-- ── Table principale formations ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS formations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    code_rncp           TEXT,           -- ex: "38587"
    intitule_formation  TEXT,           -- titre de la formation
    intitule_certification TEXT,        -- titre de la certification
    organisme           TEXT,           -- nom de l'organisme
    region              TEXT,           -- région
    departement         TEXT,           -- département
    niveau              TEXT,           -- Bac+3, Bac+5, NIVEAU 6, NIVEAU 7
    cpf_eligible        TEXT,           -- oui/non
    type_referentiel    TEXT,           -- RNCP ou RS
    date_chargement     TEXT,           -- date de mise à jour
    source              TEXT DEFAULT 'cpf_datagouv',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Enrichissement (prix, durée, modalité, lien) ─────────────────────────────
CREATE TABLE IF NOT EXISTS enrichissement (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    code_rncp           TEXT UNIQUE,    -- clé de jointure
    lien_catalogue      TEXT,           -- URL de la formation chez l'organisme
    lien_france_comp    TEXT,           -- URL fiche France Compétences
    prix_min            INTEGER,        -- prix minimum en euros
    prix_max            INTEGER,        -- prix maximum en euros
    prix_affiche        TEXT,           -- ex: "3 900 €" ou "Sur devis"
    duree_heures        INTEGER,        -- durée totale en heures
    duree_mois          INTEGER,        -- durée en mois
    duree_affichee      TEXT,           -- ex: "12 mois" ou "400h"
    modalite            TEXT,           -- Présentiel / Distanciel / Hybride
    rythme              TEXT,           -- Temps plein / Alternance / Soir+WE
    public_vise         TEXT,           -- Salarié, Demandeur emploi, etc.
    prerequis           TEXT,           -- prérequis d'entrée
    objectif_general    TEXT,           -- objectif pédagogique résumé
    source_enrichissement TEXT,         -- 'manuel', 'scraping', 'llm', 'api'
    fiabilite           INTEGER DEFAULT 3, -- 1=faible, 2=moyen, 3=élevé, 4=vérifié
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Blocs de compétences RNCP ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS blocs_competences (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    code_rncp           TEXT,
    code_bloc           TEXT,           -- ex: "BC01"
    intitule_bloc       TEXT,           -- titre du bloc
    competences         TEXT,           -- compétences détaillées (JSON ou texte)
    modalite_eval       TEXT            -- modalité d'évaluation du bloc
);

-- ── Métiers et débouchés ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS metiers_debouches (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    code_rncp           TEXT,
    intitule_metier     TEXT,           -- ex: "Data Scientist"
    code_rome           TEXT,           -- ex: "M1405"
    secteur_activite    TEXT,           -- ex: "Numérique", "Industrie"
    niveau_acces        TEXT,           -- niveau requis pour ce métier
    salaire_min         INTEGER,        -- salaire annuel min en k€
    salaire_max         INTEGER         -- salaire annuel max en k€
);

-- ── Vue matérialisée pour le RAG ──────────────────────────────────────────────
CREATE VIEW IF NOT EXISTS v_formations_rag AS
SELECT
    f.code_rncp,
    f.intitule_formation,
    f.intitule_certification,
    f.organisme,
    f.region,
    f.departement,
    f.niveau,
    f.cpf_eligible,
    e.lien_catalogue,
    e.lien_france_comp,
    e.prix_affiche,
    e.prix_min,
    e.prix_max,
    e.duree_affichee,
    e.duree_heures,
    e.modalite,
    e.rythme,
    e.public_vise,
    e.prerequis,
    e.objectif_general,
    e.fiabilite,
    GROUP_CONCAT(DISTINCT b.intitule_bloc, ' | ') AS blocs_competences,
    GROUP_CONCAT(DISTINCT m.intitule_metier || ' (' || COALESCE(m.code_rome,'') || ')', ' | ') AS metiers_debouches
FROM formations f
LEFT JOIN enrichissement e  ON f.code_rncp = e.code_rncp
LEFT JOIN blocs_competences b ON f.code_rncp = b.code_rncp
LEFT JOIN metiers_debouches m ON f.code_rncp = m.code_rncp
GROUP BY f.id;

-- ── Index pour les performances ───────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_formations_rncp   ON formations(code_rncp);
CREATE INDEX IF NOT EXISTS idx_enrichissement_rncp ON enrichissement(code_rncp);
CREATE INDEX IF NOT EXISTS idx_blocs_rncp        ON blocs_competences(code_rncp);
CREATE INDEX IF NOT EXISTS idx_metiers_rncp      ON metiers_debouches(code_rncp);
"""

def create_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"✅ Base SQLite créée : {DB_PATH}")

def get_conn():
    """Retourne une connexion SQLite avec row_factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_stats():
    conn = get_conn()
    stats = {}
    for table in ["formations", "enrichissement", "blocs_competences", "metiers_debouches"]:
        stats[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return stats

if __name__ == "__main__":
    create_db()
    print("Stats :", get_stats())
