"""
Scrape France Compétences pour récupérer les codes ROME et intitulés d'une fiche RNCP
"""
import re
import httpx
from fastapi import APIRouter
from functools import lru_cache

router = APIRouter()

@lru_cache(maxsize=200)
def get_rome_metiers(rncp_code: str) -> list:
    """Retourne [{code, intitule}] depuis France Compétences"""
    num = re.sub(r'[^0-9]', '', rncp_code)
    if not num:
        return []
    try:
        url = f"https://www.francecompetences.fr/recherche/rncp/{num}/"
        r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8, follow_redirects=True)
        # Pattern : <span ...>M1805 - </span>\n  Études et développement informatique
        pattern = r'([A-Z]\d{4})\s*-\s*</span>\s*\n?\s*([^\n<]{5,80})'
        matches = re.findall(pattern, r.text)
        seen = {}
        for code, intitule in matches:
            intitule = intitule.strip().rstrip('.')
            if code not in seen and intitule:
                seen[code] = intitule.replace("''", "'")
        return [{"code": k, "intitule": v} for k, v in seen.items()]
    except Exception:
        return []

def get_rome_codes(rncp_code: str) -> list:
    """Retourne uniquement les codes ROME (compatibilité)"""
    return [m["code"] for m in get_rome_metiers(rncp_code)]

@router.get("/rncp/{rncp_code}/metiers")
async def rncp_metiers(rncp_code: str):
    metiers = get_rome_metiers(rncp_code)
    return {"rncp": rncp_code, "metiers": metiers}
