"""
rag/enrichment.py — Enrichissement des formations RAG avec données réelles (prix, modalité, lieu, durée, métiers)
Sources : formations_enrichies.db
  - mcf_lookup (218k formations MCF) → prix, modalité, lieu, durée par titre exact ou RNCP
  - rncp_metiers (2.6k RNCP) → texte métiers + durée consolidée par certification
"""

import re
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = str(Path(__file__).parent.parent / "data" / "formations_enrichies.db")

# Mapping département → ville principale (source: chefs-lieux officiels)
_DEPT_TO_CITY: dict[str, str] = {
    # Île-de-France
    "Paris": "Paris",
    "Hauts-de-Seine": "Neuilly-sur-Seine",
    "Seine-Saint-Denis": "Saint-Denis",
    "Val-de-Marne": "Créteil",
    "Seine-et-Marne": "Melun",
    "Yvelines": "Versailles",
    "Essonne": "Évry-Courcouronnes",
    "Val-d'Oise": "Cergy",
    # Grandes métropoles
    "Rhône": "Lyon",
    "Bouches-du-Rhône": "Marseille",
    "Nord": "Lille",
    "Gironde": "Bordeaux",
    "Haute-Garonne": "Toulouse",
    "Loire-Atlantique": "Nantes",
    "Hérault": "Montpellier",
    "Bas-Rhin": "Strasbourg",
    "Alpes-Maritimes": "Nice",
    "Ille-et-Vilaine": "Rennes",
    "Isère": "Grenoble",
    "Haut-Rhin": "Mulhouse",
    "Moselle": "Metz",
    "Meurthe-et-Moselle": "Nancy",
    "Puy-de-Dôme": "Clermont-Ferrand",
    "Seine-Maritime": "Rouen",
    "Pas-de-Calais": "Arras",
    "Var": "Toulon",
    "Maine-et-Loire": "Angers",
    "Finistère": "Brest",
    "Loiret": "Orléans",
    "Loire": "Saint-Étienne",
    "Gard": "Nîmes",
    "Côte-d'Or": "Dijon",
    "Pyrénées-Atlantiques": "Pau",
    # Autres départements
    "Ain": "Bourg-en-Bresse",
    "Aisne": "Laon",
    "Allier": "Moulins",
    "Alpes-de-Haute-Provence": "Digne-les-Bains",
    "Hautes-Alpes": "Gap",
    "Ardèche": "Privas",
    "Ardennes": "Charleville-Mézières",
    "Ariège": "Foix",
    "Aube": "Troyes",
    "Aude": "Carcassonne",
    "Aveyron": "Rodez",
    "Calvados": "Caen",
    "Cantal": "Aurillac",
    "Charente": "Angoulême",
    "Charente-Maritime": "La Rochelle",
    "Cher": "Bourges",
    "Corrèze": "Tulle",
    "Corse-du-Sud": "Ajaccio",
    "Haute-Corse": "Bastia",
    "Creuse": "Guéret",
    "Dordogne": "Périgueux",
    "Doubs": "Besançon",
    "Drôme": "Valence",
    "Eure": "Évreux",
    "Eure-et-Loir": "Chartres",
    "Haute-Garonne": "Toulouse",
    "Gers": "Auch",
    "Haute-Loire": "Le Puy-en-Velay",
    "Haute-Marne": "Chaumont",
    "Hautes-Pyrénées": "Tarbes",
    "Haute-Saône": "Vesoul",
    "Haute-Savoie": "Annecy",
    "Haute-Vienne": "Limoges",
    "Hautes-Vienne": "Limoges",
    "Indre": "Châteauroux",
    "Indre-et-Loire": "Tours",
    "Jura": "Lons-le-Saunier",
    "Landes": "Mont-de-Marsan",
    "Loir-et-Cher": "Blois",
    "Lot": "Cahors",
    "Lot-et-Garonne": "Agen",
    "Lozère": "Mende",
    "Manche": "Saint-Lô",
    "Marne": "Châlons-en-Champagne",
    "Mayenne": "Laval",
    "Meuse": "Bar-le-Duc",
    "Morbihan": "Vannes",
    "Nièvre": "Nevers",
    "Oise": "Beauvais",
    "Orne": "Alençon",
    "Puy-de-Dôme": "Clermont-Ferrand",
    "Pyrénées-Orientales": "Perpignan",
    "Bas-Rhin": "Strasbourg",
    "Saône-et-Loire": "Mâcon",
    "Sarthe": "Le Mans",
    "Savoie": "Chambéry",
    "Seine-Maritime": "Rouen",
    "Somme": "Amiens",
    "Tarn": "Albi",
    "Tarn-et-Garonne": "Montauban",
    "Vaucluse": "Avignon",
    "Vendée": "La Roche-sur-Yon",
    "Vienne": "Poitiers",
    "Vosges": "Épinal",
    "Yonne": "Auxerre",
    "Territoire de Belfort": "Belfort",
    # DOM
    "Guadeloupe": "Basse-Terre",
    "Martinique": "Fort-de-France",
    "Guyane": "Cayenne",
    "La Réunion": "Saint-Denis",
    "Mayotte": "Mamoudzou",
}

_conn = None


def _get_conn():
    global _conn
    if _conn is None:
        try:
            _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
        except Exception as e:
            logger.error(f"Erreur ouverture formations_enrichies.db : {e}")
    return _conn


def enrich_formation(titre_formation: str, rncp: str = "") -> dict:
    """
    Cherche prix, modalité, lieu, durée et métiers pour une formation RAG.
    Recherche par titre exact puis par RNCP.
    Retourne {} si aucune donnée disponible.
    """
    conn = _get_conn()
    if conn is None:
        return {}

    titre_norm = (titre_formation or "").strip().lower()
    rncp_clean = (str(rncp) or "").strip()
    valid_rncp = rncp_clean not in ("", "-1", "nan")

    result = {}

    try:
        # 1. Recherche exacte par titre normalisé (prix, modalité, lieu, durée)
        if titre_norm:
            cur = conn.execute(
                "SELECT prix, modalite, departement, region, duree_h FROM mcf_lookup "
                "WHERE titre_norm = ? LIMIT 1",
                (titre_norm,)
            )
            row = cur.fetchone()
            if row:
                result = _row_to_dict(row)

        # 2. Fallback RNCP pour prix/modalité/durée si titre non trouvé
        if not result and valid_rncp:
            cur = conn.execute(
                "SELECT AVG(prix) as prix, modalite, departement, region, MAX(duree_h) as duree_h "
                "FROM mcf_lookup WHERE code_rncp = ? GROUP BY modalite ORDER BY COUNT(*) DESC LIMIT 1",
                (rncp_clean,)
            )
            row = cur.fetchone()
            if row:
                result = _row_to_dict(row)

        # 3. Enrichissement durée + métiers depuis rncp_metiers
        if valid_rncp:
            cur = conn.execute(
                "SELECT metiers_text, duree_h_mean FROM rncp_metiers WHERE code_rncp = ?",
                (rncp_clean,)
            )
            rm = cur.fetchone()
            if rm:
                # Durée consolidée : priorité à rncp_metiers si meilleure que mcf_lookup
                duree_rncp = int(rm["duree_h_mean"] or 0)
                duree_actuelle = result.get("_duree_h_raw", 0)
                if duree_rncp > duree_actuelle:
                    result["duree_h_reel"] = f"{duree_rncp} h"
                    result["_duree_h_raw"] = duree_rncp

                # Métiers extraits du texte resultats_attendus
                metiers_text = rm["metiers_text"] or ""
                result["metiers"] = _extract_metiers(metiers_text)

    except Exception as e:
        logger.warning(f"Erreur enrichissement formation '{titre_norm[:40]}': {e}")

    # Nettoyer clé interne
    result.pop("_duree_h_raw", None)
    return result


def _extract_metiers(text: str) -> list[str]:
    """
    Extrait la liste de métiers depuis resultats_attendus_formation.
    Reconnaît deux structures :
      A) Liste à puces après "métiers suivants :" / "exercer les métiers"
      B) Énumération de postes dans une phrase : "occupent des postes de X, Y, Z"
    Filtre les faux positifs (blocs de compétences, évaluations).
    """
    if not text:
        return []

    # Patterns qui indiquent une vraie section métiers (pas "problématique métier")
    SECTION_TRIGGERS = re.compile(
        r'(métiers suivants|exercer les métiers|opérationnel pour exercer|'
        r'occupent des postes|débouchés.*professionnel|emplois.*visés|'
        r'poste.*occuper|métiers.*accessibles|prépare aux métiers)',
        re.I
    )
    # Faux positifs à ignorer (contexte métier non-professionnel)
    FALSE_POSITIVE = re.compile(r'problématique métier|référentiel métier|secteur métier', re.I)

    # Structure A : liste à puces
    metiers = []
    lines = text.split("\n")
    in_section = False
    for line in lines:
        line_s = line.strip()
        if SECTION_TRIGGERS.search(line_s) and not FALSE_POSITIVE.search(line_s):
            in_section = True
            # Tenter aussi d'extraire les titres inline (après ":")
            after_colon = re.split(r':\s*', line_s, maxsplit=1)
            if len(after_colon) > 1 and len(after_colon[1]) > 4:
                for part in re.split(r'[,;]', after_colon[1]):
                    t = _clean_metier(part)
                    if t:
                        metiers.append(t)
            continue
        if in_section:
            bm = re.match(r'^[-•·*]\s*(.+)$', line_s)
            if bm:
                t = _clean_metier(bm.group(1))
                if t:
                    metiers.append(t)
            elif line_s and len(metiers) > 0:
                # Fin de section si ligne non-vide sans tiret
                break
        if len(metiers) >= 6:
            break

    # Structure B : "postes de X, Y, Z" dans une phrase (si aucun résultat via A)
    if not metiers:
        m = re.search(
            r'(?:postes? de|métiers? de|emplois? de|exercer)\s*:?\s*([A-ZÀ-Ü][^.!?\n]{10,200})',
            text, re.I
        )
        if m:
            for part in re.split(r'[,;/]', m.group(1)):
                t = _clean_metier(part)
                if t:
                    metiers.append(t)
                if len(metiers) >= 6:
                    break

    return metiers[:6]


def _clean_metier(raw: str) -> str:
    """Nettoie un intitulé de métier brut."""
    t = raw.strip()
    # Supprimer parenthèses
    t = re.sub(r'\s*\([^)]*\)', '', t).strip()
    # Supprimer numéro de bloc (ex: "Bloc 1 : ...")
    if re.match(r'^Bloc\s*\d', t, re.I):
        return ""
    # Supprimer les suffixes parasites après "/"
    t = t.split("/")[0].strip()
    # Nettoyer ponctuation finale
    t = t.rstrip(".,;:").strip()
    # Filtrer les titres trop courts, trop longs ou sans majuscule
    if len(t) < 4 or len(t) > 80:
        return ""
    return t


def _row_to_dict(row) -> dict:
    prix = int(row["prix"] or 0)
    modalite = (row["modalite"] or "NC").strip()
    departement = (row["departement"] or "").strip().replace("nan", "").strip()
    region = (row["region"] or "").strip().replace("nan", "").strip()
    duree_h = int(row["duree_h"] or 0)

    # Format prix lisible en français
    if prix > 0:
        prix_str = f"{prix:,} €".replace(",", "\u202f")
    else:
        prix_str = "NC"

    # Lieu : ville principale du département si présentiel/hybride
    lieu = ""
    if modalite in ("Présentiel", "Hybride"):
        if departement:
            lieu = _DEPT_TO_CITY.get(departement, departement)  # ville ou fallback département
        elif region:
            lieu = region

    return {
        "prix_reel": prix_str,
        "modalite_reelle": modalite,
        "lieu": lieu,
        "duree_h_reel": f"{duree_h} h" if duree_h > 0 else "NC",
        "_duree_h_raw": duree_h,
    }
