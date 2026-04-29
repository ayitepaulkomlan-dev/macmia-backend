"""
routers/cv.py — Endpoint /api/cv/extract
Traitement upload CV (PDF, DOCX, TXT) + extraction LLM
Remplace processLandingFile(), parsePdfLanding(), parseDocxLanding() du JS
"""

import io
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from llm_chain import call_extraction_llm

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Extraction texte ──────────────────────────────────────────────────────────

def extract_text_from_pdf(content: bytes) -> str:
    """Extrait le texte d'un PDF. Essaie pdfplumber d'abord (meilleure qualité), puis pypdf."""
    # Essai 1 : pdfplumber (préserve la mise en page, meilleure extraction)
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            total = len(pdf.pages)
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text(x_tolerance=2, y_tolerance=3)
                if text and text.strip():
                    pages.append(f"--- Page {i}/{total} ---\n{text.strip()}")
        if pages:
            return "\n\n".join(pages)
    except ImportError:
        pass  # pdfplumber non installé, fallback pypdf
    except Exception as e:
        logger.warning(f"pdfplumber échoué ({e}), fallback pypdf")

    # Essai 2 : pypdf (fallback)
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except ImportError:
        raise HTTPException(status_code=500, detail="pdfplumber et pypdf non installés. Lance : pip install pdfplumber")
    except Exception as e:
        logger.error(f"Erreur extraction PDF: {e}")
        raise HTTPException(status_code=400, detail=f"Impossible de lire le PDF : {e}")


def extract_text_from_docx(content: bytes) -> str:
    """Extrait le texte d'un DOCX avec python-docx."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(content))
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return text.strip()
    except ImportError:
        raise HTTPException(status_code=500, detail="python-docx non installé. Lance : pip install python-docx")
    except Exception as e:
        logger.error(f"Erreur extraction DOCX: {e}")
        raise HTTPException(status_code=400, detail=f"Impossible de lire le DOCX : {e}")


def extract_text_from_txt(content: bytes) -> str:
    """Décode un fichier texte brut."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            return content.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="Impossible de décoder le fichier texte.")


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/cv/extract")
async def extract_cv(file: UploadFile = File(...)):
    """
    Upload + extraction CV complet.

    Étapes :
      1. Lire le fichier uploadé (PDF / DOCX / TXT)
      2. Extraire le texte brut
      3. Appeler le LLM léger (phi3 / mistral) pour structurer les données
      4. Retourner : {cv_text, cv_data: {nom, poste_actuel, niveau_etudes, annees_experience, competences_cles}}

    """
    # Vérification type fichier
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("pdf", "docx", "doc", "txt"):
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté : .{ext}. Formats acceptés : PDF, DOCX, TXT"
        )

    # Lecture du contenu
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lecture fichier : {e}")

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Le fichier est vide.")

    if len(content) > 10 * 1024 * 1024:  # 10 Mo max
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 10 Mo).")

    # Extraction texte selon le format
    logger.info(f"Extraction CV : {filename} ({len(content)} bytes)")
    if ext == "pdf":
        cv_text = extract_text_from_pdf(content)
    elif ext in ("docx", "doc"):
        cv_text = extract_text_from_docx(content)
    else:
        cv_text = extract_text_from_txt(content)

    if not cv_text or len(cv_text) < 50:
        raise HTTPException(
            status_code=400,
            detail="Le texte extrait est trop court. Le CV est peut-être une image scannée (OCR non supporté)."
        )

    # Extraction structurée via LLM léger
    cv_data = await call_extraction_llm(cv_text)
    logger.info(f"CV extrait — Nom: {cv_data.get('nom')}, Poste: {cv_data.get('poste_actuel')}")

    return {
        "success": True,
        "filename": filename,
        "cv_text": cv_text,
        "cv_text_length": len(cv_text),
        "cv_data": cv_data,
    }
