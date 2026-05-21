# MACMIA × IMT Exed — Moteur de Recommandation Formation IA & Data

> Plateforme d'orientation personnalisée par IA pour les formations IA, Data et Industrie du Futur des 8 Grandes Écoles IMT — France 2030 (5,9M€)

## 🏗️ Architecture
## 🚀 Stack Technique

| Composant | Technologie |
|-----------|-------------|
| LLM | Llama 3.1 8B Instruct Q4_K_M (llama-cpp-python) |
| GPU | Tesla T4 — 15 Go VRAM |
| Embeddings | nomic-embed-text-v1.5 Q4_K_M (GPU) |
| Vector DB | ChromaDB — 30 949 formations CPF |
| Backend | FastAPI + Uvicorn |
| Tunnel | ngrok (développement) |
| Frontend | Vanilla JS + Chart.js + PDF.js |

## 📊 Sources de données

- **Catalogue IMT ExEd** : 32 formations curatées (IMT-BS, Télécom Paris, IMT Atlantique, IMT Nord Europe, IMT Mines Albi, Télécom SudParis)
- **Catalogue CPF** : 30 949 formations IA/Data depuis data.gouv.fr (MAJ quotidienne)
- **France Compétences** : Codes ROME et intitulés métiers par RNCP
- **OPIIEC 2025** : Données marché emploi IA/Data

## ⚙️ Installation & Démarrage

### Prérequis
- Python 3.10+
- GPU CUDA (recommandé Tesla T4+)
- Modèles GGUF dans `/home/docker/models/` :
  - `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf`
  - `nomic-embed-text-v1.5.Q4_K_M.gguf`

### Backend

```bash
cd backend
pip install -r requirements.txt

# Indexer le catalogue CPF (30-60 min première fois)
python3 rag/ingest.py

# Lancer le serveur
python3 main.py
```

### Frontend

Ouvrir `frontend/index.html` dans un navigateur ou servir via FastAPI :
### Tunnel ngrok (développement)

```python
from pyngrok import ngrok
url = ngrok.connect(8000)
print("URL:", url)
```

## 🧠 Flux de recommandation
## 🎯 Fonctionnalités clés

- **Qualification avant recommandation** : le moteur pose 3 questions minimum avant de recommander
- **Recommandation uniquement sur demande** : jamais de formations imposées
- **Métiers réels** : codes ROME et intitulés scrappés depuis France Compétences
- **Données CPF officielles** : durée, prix, ville, modalité depuis data.gouv.fr
- **Analyse CV** : extraction automatique des compétences + interview personnalisée
- **Radar de compétences** : comparaison profil utilisateur vs exigences métier

## 👥 Équipe

Projet France 2030 — IMT Executive Education
