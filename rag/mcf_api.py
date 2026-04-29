"""
rag/mcf_api.py — Client pour l'API publique Caisse des Dépôts (Opendatasoft)
Source : opendata.caissedesdepots.fr
  - moncompteformation_formations_engagees → prix_moyen, duree_moyenne, modalite_presence par RNCP
  - moncompteformation_catalogueformation  → intitule_formation, objectif_formation (fallback)

Cache SQLite 7 jours dans formations_enrichies.db (table api_enrichment_cache)
Aucune authentification requise.
"""

import re
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

DB_PATH = str(Path(__file__).parent.parent / "data" / "formations_enrichies.db")

# ── Endpoints Opendatasoft ──────────────────────────────────────────────────
_BASE = "https://opendata.caissedesdepots.fr/api/explore/v2.1/catalog/datasets"
_DS_ENGAGEES  = f"{_BASE}/moncompteformation_formations_engagees/records"
_DS_CATALOGUE = f"{_BASE}/moncompteformation_catalogueformation/records"

_CACHE_TTL_DAYS = 7
_TIMEOUT = 8.0   # secondes


# ── Cache SQLite ─────────────────────────────────────────────────────────────
def _get_cache_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_enrichment_cache (
            code_rncp   TEXT PRIMARY KEY,
            prix_api    INTEGER,
            duree_h_api INTEGER,
            modalite    TEXT,
            fetched_at  TEXT
        )
    """)
    conn.commit()
    return conn


_cache_conn = None

def _conn():
    global _cache_conn
    if _cache_conn is None:
        _cache_conn = _get_cache_conn()
    return _cache_conn


def _cache_get(rncp: str) -> dict | None:
    """Retourne les données cachées si elles sont récentes (< TTL jours)."""
    try:
        row = _conn().execute(
            "SELECT prix_api, duree_h_api, modalite, fetched_at "
            "FROM api_enrichment_cache WHERE code_rncp = ?", (rncp,)
        ).fetchone()
        if row:
            age = datetime.utcnow() - datetime.fromisoformat(row["fetched_at"])
            if age < timedelta(days=_CACHE_TTL_DAYS):
                return {
                    "prix_api":    row["prix_api"],
                    "duree_h_api": row["duree_h_api"],
                    "modalite":    row["modalite"],
                }
    except Exception as e:
        logger.debug(f"Cache miss/erreur pour RNCP {rncp}: {e}")
    return None


def _cache_set(rncp: str, prix: int, duree: int, modalite: str):
    try:
        _conn().execute(
            "INSERT OR REPLACE INTO api_enrichment_cache VALUES (?,?,?,?,?)",
            (rncp, prix, duree, modalite, datetime.utcnow().isoformat())
        )
        _conn().commit()
    except Exception as e:
        logger.debug(f"Cache write erreur RNCP {rncp}: {e}")


# ── Requête API Opendatasoft ─────────────────────────────────────────────────
async def _fetch_engagees(rncp: str) -> dict | None:
    """
    Interroge formations_engagees pour obtenir prix, durée et modalité réels.
    Prend la modalité la plus fréquente parmi les formations clôturées avec réalisation totale.
    """
    params = {
        "select": "modalite_presence, avg(prix_moyen) as prix, avg(duree_moyenne) as duree, count(*) as nb",
        "where":  f'code_rncp="{rncp}" AND statut_dossier="Clos - Réalisation Totale"',
        "group_by": "modalite_presence",
        "order_by": "nb desc",
        "limit": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_DS_ENGAGEES, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                r = results[0]
                return {
                    "prix":     int(r.get("prix") or 0),
                    "duree":    int(r.get("duree") or 0),
                    "modalite": _normalise_modalite(r.get("modalite_presence") or ""),
                }
    except Exception as e:
        logger.debug(f"API engagees RNCP {rncp}: {e}")
    return None


async def _fetch_catalogue_by_titre(titre: str, rncp: str) -> dict | None:
    """
    Cherche le prix/durée d'une formation spécifique par titre dans le catalogue CDC.
    Bien plus précis qu'une moyenne par RNCP (ex: RNCP 39775 a des prix de 5850€ à 15600€).
    """
    # Extraire les mots-clés significatifs (hors parenthèses/sigles)
    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', titre).strip()
    words = [w for w in clean.split() if len(w) > 2][:5]
    if not words:
        return None
    search_query = " ".join(words)

    params = {
        "select": "frais_ttc_tot_mean, nombre_heures_total_mean, nb_session_a_distance, nb_action",
        "where":  f'code_rncp="{rncp}" AND search(intitule_formation, "{search_query}")',
        "order_by": "frais_ttc_tot_mean desc",
        "limit":  1,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_DS_CATALOGUE, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                r = results[0]
                prix  = int(r.get("frais_ttc_tot_mean") or 0)
                duree = int(r.get("nombre_heures_total_mean") or 0)
                nb    = r.get("nb_action") or 0
                dist  = r.get("nb_session_a_distance") or 0
                if nb > 0:
                    if dist == 0:    modal = "Présentiel"
                    elif dist >= nb: modal = "Distanciel"
                    else:            modal = "Hybride"
                else:
                    modal = "NC"
                if prix > 0 or duree > 0:
                    logger.debug(f"API titre match '{search_query}' RNCP {rncp}: {prix}€ / {duree}h")
                    return {"prix": prix, "duree": duree, "modalite": modal}
    except Exception as e:
        logger.debug(f"API catalogue titre '{search_query}' RNCP {rncp}: {e}")
    return None


async def _fetch_catalogue(rncp: str) -> dict | None:
    """
    Fallback : interroge le catalogue pour prix/durée par RNCP (moyenne).
    """
    params = {
        "select": (
            "frais_ttc_tot_mean, nombre_heures_total_mean, "
            "nb_session_a_distance, nb_action"
        ),
        "where":    f'code_rncp="{rncp}"',
        "order_by": "frais_ttc_tot_mean desc",
        "limit":    1,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_DS_CATALOGUE, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                r = results[0]
                prix  = int(r.get("frais_ttc_tot_mean") or 0)
                duree = int(r.get("nombre_heures_total_mean") or 0)
                nb    = r.get("nb_action") or 0
                dist  = r.get("nb_session_a_distance") or 0
                if nb > 0:
                    if dist == 0:       modal = "Présentiel"
                    elif dist >= nb:    modal = "Distanciel"
                    else:               modal = "Hybride"
                else:
                    modal = "NC"
                if prix > 0 or duree > 0:
                    return {"prix": prix, "duree": duree, "modalite": modal}
    except Exception as e:
        logger.debug(f"API catalogue RNCP {rncp}: {e}")
    return None


def _normalise_modalite(raw: str) -> str:
    r = raw.strip().lower()
    if "distance" in r:   return "Distanciel"
    if "présenti" in r:   return "Présentiel"
    if "mixte" in r:      return "Hybride"
    return raw.strip() or "NC"


# ── Point d'entrée : enrichissement par titre + RNCP (le plus précis) ────────
async def _enrich_formation_smart(rncp: str, titre: str = "") -> dict:
    """
    Stratégie en 4 niveaux (du plus précis au moins précis) :
      1. Match titre dans catalogue CDC (prix de la formation spécifique)
      2. Cache RNCP (résultat précédent)
      3. API formations_engagees (moyenne historique par RNCP)
      4. API catalogue par RNCP (fallback)
    """
    valid_rncp = rncp and rncp not in ("", "-1", "nan")

    # 1. Match titre exact dans catalogue (le plus précis — évite les moyennes trompeuses)
    titre_clean = titre.strip() if titre else ""
    if titre_clean and valid_rncp:
        result = await _fetch_catalogue_by_titre(titre_clean, rncp)
        if result:
            return {
                "prix_api":    result["prix"],
                "duree_h_api": result["duree"],
                "modalite":    result["modalite"],
            }

    if not valid_rncp:
        return {}

    # 2. Cache RNCP (résultat précédemment récupéré)
    cached = _cache_get(rncp)
    if cached is not None:
        return cached

    # 3. API formations_engagees (historique réalisé par RNCP)
    result = await _fetch_engagees(rncp)

    # 4. API catalogue par RNCP (fallback si aucun dossier engagé)
    if not result:
        result = await _fetch_catalogue(rncp)

    if result:
        _cache_set(rncp, result["prix"], result["duree"], result["modalite"])
        return {
            "prix_api":    result["prix"],
            "duree_h_api": result["duree"],
            "modalite":    result["modalite"],
        }

    _cache_set(rncp, 0, 0, "NC")
    return {}


async def enrich_rncp_from_api(rncp: str) -> dict:
    """Compatibilité — délègue à _enrich_formation_smart sans titre."""
    return await _enrich_formation_smart(rncp)


async def enrich_cards_from_api(cards: list[dict]) -> list[dict]:
    """
    Enrichit en batch une liste de cartes formation avec les données API CDC.
    Utilise le titre de la formation pour un match précis (pas une moyenne RNCP).
    Ne modifie que les champs prix/duree/format si les valeurs actuelles sont NC.
    """
    tasks = []
    indices = []

    for i, card in enumerate(cards):
        fd = card.get("formation_data", {})
        rncp  = str(fd.get("rncp") or "").strip()
        titre = str(fd.get("titre") or "").strip()
        # N'appeler l'API que si prix OU durée est NC
        if rncp and rncp not in ("", "-1", "nan"):
            if fd.get("prix") in (None, "NC", "") or fd.get("duree") in (None, "NC", ""):
                tasks.append(_enrich_formation_smart(rncp, titre))
                indices.append(i)

    if not tasks:
        return cards

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for idx, api_data in zip(indices, results):
        if isinstance(api_data, Exception) or not api_data:
            continue
        fd = cards[idx]["formation_data"]

        # Prix
        if fd.get("prix") in (None, "NC", "") and api_data.get("prix_api", 0) > 0:
            prix = api_data["prix_api"]
            fd["prix"] = f"{prix:,} €".replace(",", "\u202f")

        # Durée
        if fd.get("duree") in (None, "NC", "") and api_data.get("duree_h_api", 0) > 0:
            fd["duree"] = f"{api_data['duree_h_api']} h"

        # Modalité + format (seulement si NC)
        if fd.get("format") in (None, "NC", "") and api_data.get("modalite") not in (None, "NC", ""):
            fd["format"] = api_data["modalite"]

    return cards
