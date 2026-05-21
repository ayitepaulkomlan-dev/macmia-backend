"""
catalogue.py — Données MACMIA : formations, métiers ROME, personas, stats OPIIEC
Extraites directement du macmia-chatbot-v5.html
"""

# ── Stats OPIIEC 2025 ────────────────────────────────────────────────────────
OPIIEC_STATS = {
    "adoption": "64%",
    "prevision": "88%",
    "emplois_actuels": "258 000",
    "creations": "+45 000",
    "poids_ia": "17%",
    "a_former": "287 000",
}

# ── Personas (14) ────────────────────────────────────────────────────────────
PERSONAS = [
    {"id": "sarah",     "name": "Sarah, 28 ans",       "desc": "Reconvertie anxieuse",          "groupe": "A", "kw": ["reconversion","cdi","bts","assistante","canva","excel","design","numérique"],          "fin": "CPF",        "niv": "Bac+2",    "reg": "Clermont-Ferrand"},
    {"id": "karim",     "name": "Karim, 38 ans",        "desc": "Professionnel ambitieux",        "groupe": "A", "kw": ["chef de projet","esn","dsi","cadre","management","certification"],                     "fin": "OPCO",       "niv": "Bac+5",    "reg": "Paris"},
    {"id": "michel",    "name": "Michel, 52 ans",        "desc": "Demandeur emploi",              "groupe": "A", "kw": ["demandeur emploi","maintenance","technicien","licencié","are","france travail"],       "fin": "ARE+CPF",    "niv": "CAP",      "reg": "Haute-Saône"},
    {"id": "isabelle",  "name": "Isabelle, 45 ans",      "desc": "RH stratégique",                "groupe": "A", "kw": ["drh","rh","responsable formation","pme","opco","qualiopi"],                            "fin": "OPCO",       "niv": "Bac+4",    "reg": "Lyon"},
    {"id": "leo",       "name": "Léo, 20 ans",           "desc": "Étudiant explorateur",          "groupe": "A", "kw": ["bachelier","alternance","licence pro","bts","post-bac"],                              "fin": "Alternance", "niv": "Bac",      "reg": "Bordeaux"},
    {"id": "amina",     "name": "Amina, 34 ans",         "desc": "Reprise activité",              "groupe": "A", "kw": ["interruption","mère","comptabilité","bts","télétravail","caf"],                        "fin": "CPF+CAF",    "niv": "Bac+2",    "reg": "Banlieue Paris"},
    {"id": "thomas",    "name": "Thomas, 16 ans",         "desc": "Lycéen orientation",            "groupe": "A", "kw": ["lycéen","bac pro","orientation","apprentissage"],                                     "fin": "Apprentissage","niv": "Lycée", "reg": "Grand Est"},
    {"id": "hugo",      "name": "Hugo, 17 ans",           "desc": "Lycéen IA — MACMIA",           "groupe": "B", "kw": ["nsi","python","terminale","mathématiques","ia","jeux vidéo","programmation"],         "fin": "Parents",    "niv": "Terminale","reg": "Grand Est"},
    {"id": "ingrid",    "name": "Ingrid, 24 ans",         "desc": "Ingénieure → IA",               "groupe": "B", "kw": ["ingénieure","imt atlantique","data science","mastère","kaggle","github","alternance"],"fin": "Alternance", "niv": "Bac+3",    "reg": "Bretagne"},
    {"id": "sebastien", "name": "Sébastien, 35 ans",      "desc": "Ingénieur → IA industrielle",  "groupe": "B", "kw": ["ingénieur process","agroalimentaire","automatisation","python","opco 2i","industrie"], "fin": "OPCO 2i",    "niv": "Bac+5",    "reg": "Pays-de-la-Loire"},
    {"id": "fatima",    "name": "Fatima, 41 ans",          "desc": "DRH PME industrielle",         "groupe": "B", "kw": ["drh","pme","métallurgie","opco ep","imt nord europe","hauts-de-france"],              "fin": "OPCO EP",    "niv": "Bac+4",    "reg": "Hauts-de-France"},
    {"id": "romain",    "name": "Romain, 29 ans",          "desc": "Dev freelance → IA",           "groupe": "B", "kw": ["freelance","développeur","python","javascript","full-stack","llm","cpf tns"],         "fin": "CPF TNS",    "niv": "Bac+3",    "reg": "Île-de-France"},
    {"id": "claire",    "name": "Dr Claire, 44 ans",       "desc": "Médecin & IA Santé",           "groupe": "B", "kw": ["médecin","urgentiste","chu","diagnostic ia","dpc","santé"],                          "fin": "DPC",        "niv": "Bac+8",    "reg": "Occitanie"},
    {"id": "abdel",     "name": "Abdel, 38 ans",           "desc": "Demandeur emploi industrie",   "groupe": "B", "kw": ["maintenance industrielle","bts","demandeur emploi","fermeture usine","esigelec"],    "fin": "ARE+CPF",    "niv": "BTS",      "reg": "Normandie"},
]

# ── Métiers ROME / OPIIEC (12) ───────────────────────────────────────────────
JOBS_REF = {
    "M1889": {
        "titre": "Ingénieur IA", "famille": "Architecture & Conception", "domaine": "IA",
        "rome": "M1889", "salaire": "60–90k€", "salaire_range": [60, 90],
        "tendance": "🔺 Très forte demande", "tendance_detail": "+45 000 emplois d'ici 3 ans (OPIIEC 2025)",
        "opiiec_level": "Niveau 3/4",
        "skills_requis": [
            {"name": "Algorithmie & ML", "required": 85}, {"name": "Architecture IA", "required": 80},
            {"name": "Python / Frameworks IA", "required": 85}, {"name": "Gestion projets IA", "required": 70},
            {"name": "Évaluation modèles", "required": 75}, {"name": "Veille IA", "required": 70},
        ],
        "rncp_recommandes": ["RNCP38587", "RNCP35609", "RNCP41813"],
        "competences_emergentes": "IA générative, LLM fine-tuning, MLOps",
        "metiers_lies": ["Data Engineer", "Data Scientist", "Architecte IA"],
        "desc": "Conçoit, développe et déploie des solutions d'IA (ML, NLP, vision par ordinateur).",
    },
    "M1405": {
        "titre": "Data Scientist", "famille": "Architecture & Conception", "domaine": "Data",
        "rome": "M1405", "salaire": "50–80k€", "salaire_range": [50, 80],
        "tendance": "🔺 Profil le + recherché", "tendance_detail": "Salaire médian 55–80k€. Fort besoin industrie & santé.",
        "opiiec_level": "Niveau 4/4",
        "skills_requis": [
            {"name": "Python / R / Scala", "required": 85}, {"name": "Machine Learning", "required": 90},
            {"name": "Statistiques", "required": 85}, {"name": "Traitement Big Data", "required": 75},
            {"name": "Visualisation", "required": 70}, {"name": "SQL / NoSQL", "required": 80},
        ],
        "rncp_recommandes": ["RNCP37431", "RNCP34545", "RNCP39586"],
        "competences_emergentes": "Manager la connaissance, démarche agile innovante",
        "metiers_lies": ["Data Engineer", "Business Analyst", "ML Engineer"],
        "desc": "Introduit des techniques de Data Science et d'IA pour résoudre des problématiques métier.",
    },
    "M1419": {
        "titre": "Data Analyst", "famille": "Analytics & BI", "domaine": "Data",
        "rome": "M1419", "salaire": "38–60k€", "salaire_range": [38, 60],
        "tendance": "🔶 Demande stable forte", "tendance_detail": "Profils hybrides métier+data très recherchés.",
        "opiiec_level": "Niveau 2/4",
        "skills_requis": [
            {"name": "SQL & Bases de données", "required": 80}, {"name": "Statistiques descriptives", "required": 75},
            {"name": "Power BI / Tableau", "required": 75}, {"name": "Python / R", "required": 65},
            {"name": "Analyse prédictive", "required": 70}, {"name": "Restitution métier", "required": 70},
        ],
        "rncp_recommandes": ["RNCP34545", "RNCP38616"],
        "competences_emergentes": "Analyse prédictive, communication insights",
        "metiers_lies": ["Data Scientist", "BI Developer", "Product Analyst"],
        "desc": "Transforme les données en informations statistiques et techniques.",
    },
    "M1811": {
        "titre": "Data Engineer", "famille": "Architecture & Conception", "domaine": "Data",
        "rome": "M1811", "salaire": "48–75k€", "salaire_range": [48, 75],
        "tendance": "🔺 Fort recrutement", "tendance_detail": "Métier cœur de la transformation IA.",
        "opiiec_level": "Niveau 3/4",
        "skills_requis": [
            {"name": "SQL / NoSQL", "required": 85}, {"name": "Pipelines ETL", "required": 85},
            {"name": "Cloud (AWS/GCP/Azure)", "required": 80}, {"name": "Spark / Hadoop", "required": 75},
            {"name": "Python", "required": 80}, {"name": "Qualité des données", "required": 75},
        ],
        "rncp_recommandes": ["RNCP38919", "RNCP37172", "RNCP41813"],
        "competences_emergentes": "Intégration outils IA/Data Science",
        "metiers_lies": ["Data Architect", "MLOps Engineer", "Cloud Engineer"],
        "desc": "Collecte et analyse des volumes importants de données, développe des solutions de traitement.",
    },
    "M1423": {
        "titre": "Chief Data Officer", "famille": "Management & Stratégie", "domaine": "Management Data",
        "rome": "M1423", "salaire": "80–130k€", "salaire_range": [80, 130],
        "tendance": "🔺 Profil stratégique rare", "tendance_detail": "80–130k€. Recrutement accéléré.",
        "opiiec_level": "Niveau 4/4",
        "skills_requis": [
            {"name": "Gouvernance des données", "required": 80}, {"name": "Stratégie Data", "required": 85},
            {"name": "Management équipes", "required": 75}, {"name": "RGPD & conformité", "required": 70},
            {"name": "Architecture SI", "required": 70}, {"name": "Communication dirigeants", "required": 80},
        ],
        "rncp_recommandes": ["RNCP35609", "RNCP41813"],
        "competences_emergentes": "Cybersécurité, conformité IA Act",
        "metiers_lies": ["DSI", "CDO", "DPO"],
        "desc": "Pilote la stratégie data de l'entreprise, coordonne les équipes data.",
    },
    "M1824": {
        "titre": "Développeur BI / Décisionnel", "famille": "Analytics & BI", "domaine": "Data",
        "rome": "M1824", "salaire": "42–65k€", "salaire_range": [42, 65],
        "tendance": "🔶 Demande constante", "tendance_detail": "Profils BI/Analytics très demandés.",
        "opiiec_level": "Niveau 2/4",
        "skills_requis": [
            {"name": "SQL & entrepôts données", "required": 80}, {"name": "Power BI / Tableau", "required": 80},
            {"name": "Modélisation dimensionnelle", "required": 75}, {"name": "ETL/ELT", "required": 70},
            {"name": "Python", "required": 65}, {"name": "Analyse métier", "required": 75},
        ],
        "rncp_recommandes": ["RNCP34545", "RNCP38616"],
        "competences_emergentes": "Intégration outils IA/Data Science",
        "metiers_lies": ["Data Analyst", "Data Engineer", "Consultant BI"],
        "desc": "Conçoit et développe des solutions décisionnelles, tableaux de bord et rapports.",
    },
    "M1879": {
        "titre": "Ingénieur Cloud", "famille": "Infrastructure & Cloud", "domaine": "Cloud & Infra",
        "rome": "M1879", "salaire": "50–80k€", "salaire_range": [50, 80],
        "tendance": "🔺 En forte croissance", "tendance_detail": "Cloud souverain, FinOps, GreenIT.",
        "opiiec_level": "Niveau 3/4",
        "skills_requis": [
            {"name": "AWS / GCP / Azure", "required": 85}, {"name": "Infrastructure as Code", "required": 80},
            {"name": "Docker / Kubernetes", "required": 80}, {"name": "Sécurité Cloud", "required": 80},
            {"name": "Scalabilité", "required": 75}, {"name": "DevOps / CI-CD", "required": 80},
        ],
        "rncp_recommandes": ["RNCP38919", "RNCP41813"],
        "competences_emergentes": "GreenIT, cloud souverain, FinOps",
        "metiers_lies": ["DevOps Engineer", "Site Reliability Engineer", "Cloud Architect"],
        "desc": "Conçoit et optimise les infrastructures cloud.",
    },
    "M1856": {
        "titre": "Expert Cybersécurité", "famille": "Sécurité", "domaine": "Sécurité",
        "rome": "M1856", "salaire": "55–90k€", "salaire_range": [55, 90],
        "tendance": "🔺 Pénurie critique", "tendance_detail": "NIS2, DORA, IA Act : besoin réglementaire croissant.",
        "opiiec_level": "Niveau 3/4",
        "skills_requis": [
            {"name": "Audit sécurité", "required": 85}, {"name": "Analyse vulnérabilités", "required": 85},
            {"name": "Cryptographie", "required": 80}, {"name": "SOC / SIEM", "required": 75},
            {"name": "RGPD / NIS2", "required": 75}, {"name": "Forensique", "required": 70},
        ],
        "rncp_recommandes": ["RNCP38587"],
        "competences_emergentes": "IA Act, sécurité LLM, zero-trust",
        "metiers_lies": ["RSSI", "Pentester", "Analyste SOC"],
        "desc": "Protège les systèmes d'information, réalise des audits, gère les incidents.",
    },
    "M1892": {
        "titre": "Ingénieur Systèmes Embarqués", "famille": "Industrie du Futur", "domaine": "Industrie du Futur",
        "rome": "M1892", "salaire": "48–75k€", "salaire_range": [48, 75],
        "tendance": "🔺 Métier clé Industrie du Futur", "tendance_detail": "Fort besoin aéronautique, automobile, défense.",
        "opiiec_level": "Niveau 3/4",
        "skills_requis": [
            {"name": "Programmation embarquée (C/C++)", "required": 85}, {"name": "RTOS", "required": 80},
            {"name": "IoT & protocoles", "required": 75}, {"name": "IA embarquée", "required": 70},
            {"name": "Tests & validation", "required": 80}, {"name": "Architecture matérielle", "required": 75},
        ],
        "rncp_recommandes": ["RNCP38587", "RNCP35609"],
        "competences_emergentes": "IA embarquée, edge computing",
        "metiers_lies": ["Ingénieur IoT", "Développeur firmware", "Architecte systèmes"],
        "desc": "Conçoit et développe des systèmes embarqués intelligents.",
    },
    "M1426": {
        "titre": "Chief Digital Officer", "famille": "Management & Stratégie", "domaine": "Transformation Digitale",
        "rome": "M1426", "salaire": "80–140k€", "salaire_range": [80, 140],
        "tendance": "🔺 Poste stratégique", "tendance_detail": "CDO devient rôle clé dans toutes les grandes entreprises.",
        "opiiec_level": "Niveau 4/4",
        "skills_requis": [
            {"name": "Stratégie digitale", "required": 75}, {"name": "Conduite du changement", "required": 80},
            {"name": "Culture data & IA", "required": 70}, {"name": "Gestion portefeuille projets", "required": 75},
            {"name": "Architecture SI", "required": 65}, {"name": "Communication exécutive", "required": 80},
        ],
        "rncp_recommandes": ["RNCP35609", "RNCP41813"],
        "competences_emergentes": "Gouvernance IA, IA Act, transformation IA",
        "metiers_lies": ["DSI", "CDO", "Directeur Innovation"],
        "desc": "Pilote la transformation digitale de l'entreprise.",
    },
    "K1906": {
        "titre": "Data Protection Officer", "famille": "Gouvernance & Conformité", "domaine": "Gouvernance",
        "rome": "K1906", "salaire": "50–80k€", "salaire_range": [50, 80],
        "tendance": "🔶 Poste réglementaire", "tendance_detail": "RGPD + IA Act : DPO devient incontournable.",
        "opiiec_level": "Niveau 3/4",
        "skills_requis": [
            {"name": "Droit RGPD", "required": 90}, {"name": "Audit conformité", "required": 80},
            {"name": "Gestion des risques données", "required": 80}, {"name": "Cartographie traitements", "required": 75},
            {"name": "Relations CNIL", "required": 70}, {"name": "Formation sensibilisation", "required": 75},
        ],
        "rncp_recommandes": ["RNCP35609"],
        "competences_emergentes": "IA Act, conformité systèmes IA",
        "metiers_lies": ["RSSI", "Juriste IT", "Consultant conformité"],
        "desc": "Garantit la conformité RGPD, pilote la politique de protection des données.",
    },
    "M1861": {
        "titre": "Développeur Logiciel / App", "famille": "Développement", "domaine": "Dev",
        "rome": "M1861", "salaire": "40–65k€", "salaire_range": [40, 65],
        "tendance": "🔶 Demande soutenue", "tendance_detail": "Profils full-stack IA très recherchés.",
        "opiiec_level": "Niveau 2/4",
        "skills_requis": [
            {"name": "Développement logiciel", "required": 80}, {"name": "Architecture applicative", "required": 75},
            {"name": "Tests & qualité", "required": 80}, {"name": "Agilité / Scrum", "required": 75},
            {"name": "API & intégration", "required": 75}, {"name": "DevOps", "required": 70},
        ],
        "rncp_recommandes": ["RNCP36581", "RNCP38616"],
        "competences_emergentes": "IA générative, copilot-assisted dev",
        "metiers_lies": ["Tech Lead", "DevOps Engineer", "Architecte logiciel"],
        "desc": "Conçoit et développe des applications logicielles.",
    },
}

# ── Formations (32) ──────────────────────────────────────────────────────────
FORMATIONS = [
    # ── F1–F15 : IMT-BS Executive Education ──────────────────────────────────
    {"id": 1,  "titre": "Intelligence Artificielle et Data Marketing", "ecole": "IMT-BS Executive Education", "theme": "Numérique", "duree": "15 jours (3 × 5 jours sur 4 mois)", "format": "Présentiel", "niveau": "Bac+3 + 3 ans exp. marketing/IT", "prix": "NC", "fin": ["OPCO","CPF","Plan formation"], "reg": "Île-de-France", "kw": ["IA","Data","Marketing","CRM","Programmatic"], "url": "https://www.imtexed.fr/fr/formation/numerique/1738664932-56-intelligence-artificielle-et-data-marketing", "rncp": "RNCP35910", "rncp_niveau": "Niv. 6", "rncp_eligible_cpf": True, "metiers_cibles": ["M1419","M1861","M1426"], "desc": "Certifiante RNCP 35910. IA générative, data marketing, CRM, programmatic."},
    {"id": 2,  "titre": "Executive Master Intelligence Artificielle pour les Managers Innovants", "ecole": "Institut Mines-Télécom Business School", "theme": "Numérique", "duree": "6 mois (6 modules thématiques)", "format": "Distanciel (100% en ligne)", "niveau": "Bac+5 ou Bac+4 + 5 ans exp.", "prix": "NC", "fin": ["OPCO","Plan formation"], "reg": "Nationale", "kw": ["IA","Management","Innovation","LLM"], "url": "https://imtexed.fr/fr/formation/numerique/1746445444-187-executive-master-intelligence-artificielle-pour-les-managers", "rncp": "Niveau 7", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": False, "metiers_cibles": ["M1423","M1426","M1889"], "desc": "Diplômant RNCP Niveau 7. 100% en ligne pour managers en poste."},
    {"id": 3,  "titre": "Mastère Spécialisé® Conseil et Management en Systèmes d'Information", "ecole": "IMT-BS Executive Education", "theme": "Numérique", "duree": "12 mois en alternance", "format": "Présentiel", "niveau": "Bac+5 ou Bac+4 + 3 ans exp.", "prix": "15 000 €", "fin": ["CPF","OPCO","Alternance","Plan formation"], "reg": "Île-de-France", "kw": ["SI","Management","Numérique","Transformation"], "url": "https://www.imtexed.fr/fr/formation/numerique/1746612361-191-mastere-specialiser-conseil-et-management-en-systeme", "rncp": "RNCP35910", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1423","M1426","K1906"], "desc": "Diplômant RNCP 35910. Enjeux managériaux, technologiques et stratégiques des SI."},
    {"id": 4,  "titre": "Mastère Spécialisé® Ingénieur d'Affaires International", "ecole": "IMT-BS Executive Education", "theme": "Management et Marketing", "duree": "12 mois en alternance", "format": "Présentiel", "niveau": "Bac+5 ou Bac+4 + 3 ans exp.", "prix": "NC", "fin": ["OPCO","Alternance","CPF"], "reg": "Île-de-France", "kw": ["Ingénieur Affaires","Management","International","Négociation"], "url": "https://www.imtexed.fr/fr/formation/management-et-marketing/1746611618-190-mastere-specialise-ingenieur-affaires-international", "rncp": "RNCP35910", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1426","M1423"], "desc": "Diplômant RNCP 35910. Stratégie commerciale internationale, direction d'affaires complexes."},
    {"id": 5,  "titre": "Mastère Spécialisé® Réseaux et Systèmes de Communication", "ecole": "IMT-BS Executive Education", "theme": "Réseaux & Télécoms", "duree": "12 mois en alternance", "format": "Présentiel", "niveau": "Bac+5 ou Bac+4 + 3 ans exp.", "prix": "NC", "fin": ["CPF","OPCO","Alternance"], "reg": "Île-de-France", "kw": ["Réseaux","Télécoms","5G","Cloud","IoT"], "url": "https://www.imtexed.fr/fr/formation/reseaux-et-telecoms/1746612789-192-mastere-specialise-reseaux-et-systemes-de-communication", "rncp": "RNCP35910", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1879","M1892","M1889"], "desc": "Diplômant RNCP 35910. Architectures réseaux, 5G, IoT, Cloud, cybersécurité réseaux."},
    {"id": 6,  "titre": "Mastère Spécialisé® Cybersécurité et Cyberdéfense des Organisations", "ecole": "IMT-BS Executive Education", "theme": "Cybersécurité", "duree": "12 mois en alternance", "format": "Présentiel", "niveau": "Bac+5 ou Bac+4 + 3 ans exp.", "prix": "NC", "fin": ["CPF","OPCO","Alternance"], "reg": "Île-de-France", "kw": ["Cybersécurité","RSSI","SOC","NIS2","RGPD"], "url": "https://www.imtexed.fr/fr/formation/cybersecurite/1746613267-193-mastere-specialise-cybersecurite-et-cyberdefense-des-organisations", "rncp": "RNCP35910", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1856","K1906","M1889"], "desc": "Diplômant RNCP 35910. RSSI, audit, gestion incidents, conformité NIS2/RGPD."},
    {"id": 7,  "titre": "Manager de Projet IA", "ecole": "IMT-BS Executive Education", "theme": "Numérique", "duree": "5 jours (présentiel)", "format": "Présentiel", "niveau": "Bac+3 + 3 ans exp.", "prix": "NC", "fin": ["OPCO","Plan formation","CPF"], "reg": "Île-de-France", "kw": ["IA","Chef de projet","Gestion projet","Agilité"], "url": "https://www.imtexed.fr/fr/formation/numerique/1738665432-64-manager-de-projet-ia", "rncp": None, "rncp_niveau": None, "rncp_eligible_cpf": False, "metiers_cibles": ["M1889","M1423","M1426"], "desc": "Formation courte certifiante. Piloter et déployer des projets IA en entreprise."},
    {"id": 8,  "titre": "Robotique Industrielle et Cobotique", "ecole": "IMT-BS Executive Education", "theme": "Industrie du Futur", "duree": "5 jours", "format": "Présentiel", "niveau": "Technicien/Ingénieur + 2 ans exp.", "prix": "NC", "fin": ["OPCO","Plan formation"], "reg": "Île-de-France", "kw": ["Robotique","Cobotique","Industrie 4.0","Automatisation"], "url": "https://www.imtexed.fr/fr/formation/industrie-du-futur/1738666066-71-robotique-industrielle-et-cobotique", "rncp": None, "rncp_niveau": None, "rncp_eligible_cpf": False, "metiers_cibles": ["M1892","M1889"], "desc": "Programmation et intégration de robots industriels et collaboratifs."},
    {"id": 9,  "titre": "Bâtiments et Villes Intelligentes", "ecole": "IMT-BS Executive Education", "theme": "Industrie du Futur", "duree": "3 jours", "format": "Présentiel", "niveau": "Bac+3 + 3 ans exp.", "prix": "NC", "fin": ["OPCO","Plan formation"], "reg": "Île-de-France", "kw": ["Smart Building","Smart City","IoT","Énergie"], "url": "https://www.imtexed.fr/fr/formation/industrie-du-futur/1738666233-73-batiments-et-villes-intelligentes", "rncp": None, "rncp_niveau": None, "rncp_eligible_cpf": False, "metiers_cibles": ["M1892","M1879","M1426"], "desc": "Bâtiments connectés, Smart City, gestion énergétique, IoT urbain."},
    {"id": 10, "titre": "Formation de Manager de l'Innovation et du Leadership (FMIL)", "ecole": "IMT-BS Executive Education", "theme": "Management et Marketing", "duree": "10 jours (5 modules)", "format": "Présentiel", "niveau": "Manager + 5 ans exp.", "prix": "NC", "fin": ["OPCO","Plan formation"], "reg": "Île-de-France", "kw": ["Innovation","Leadership","Management","Transformation"], "url": "https://www.imtexed.fr/fr/formation/management-et-marketing/1738664742-54-formation-manager-innovation-leadership-fmil", "rncp": None, "rncp_niveau": None, "rncp_eligible_cpf": False, "metiers_cibles": ["M1426","M1423"], "desc": "Leadership innovant, conduite du changement, management de l'innovation."},
    {"id": 11, "titre": "Mastère Spécialisé® Ingénierie et Économie Circulaire", "ecole": "IMT-BS Executive Education", "theme": "Développement Durable", "duree": "12 mois en alternance", "format": "Présentiel", "niveau": "Bac+5 ou Bac+4 + 3 ans exp.", "prix": "NC", "fin": ["CPF","OPCO","Alternance"], "reg": "Île-de-France", "kw": ["Économie circulaire","RSE","Développement durable","Green"], "url": "https://www.imtexed.fr/fr/formation/developpement-durable/1746613598-194-mastere-specialise-ingenierie-economie-circulaire", "rncp": "RNCP35910", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1426","M1423"], "desc": "Diplômant RNCP 35910. Économie circulaire, RSE, transition énergétique."},
    {"id": 12, "titre": "Ingénieur Génie des Infrastructures Ferroviaires", "ecole": "IMT-BS Executive Education", "theme": "Industrie du Futur", "duree": "12 mois en alternance", "format": "Présentiel", "niveau": "Bac+5 ou Bac+4 + 3 ans exp.", "prix": "NC", "fin": ["OPCO","Alternance","Plan formation"], "reg": "Île-de-France", "kw": ["Ferroviaire","Infrastructure","Génie civil","SNCF"], "url": "https://www.imtexed.fr/fr/formation/industrie-du-futur/1746613836-195-ingenieur-genie-des-infrastructures-ferroviaires", "rncp": "RNCP35910", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": False, "metiers_cibles": ["M1892","M1879"], "desc": "Conception et gestion des infrastructures ferroviaires intelligentes."},
    {"id": 13, "titre": "5G Non-Terrestrial Networks (NTN)", "ecole": "IMT-BS Executive Education", "theme": "Réseaux & Télécoms", "duree": "3 jours", "format": "Présentiel", "niveau": "Ingénieur télécoms + 2 ans exp.", "prix": "NC", "fin": ["OPCO","Plan formation"], "reg": "Île-de-France", "kw": ["5G","NTN","Satellite","Réseaux","IoT"], "url": "https://www.imtexed.fr/fr/formation/reseaux-et-telecoms/1738665744-68-5g-non-terrestrial-networks-ntn", "rncp": None, "rncp_niveau": None, "rncp_eligible_cpf": False, "metiers_cibles": ["M1879","M1892"], "desc": "Réseaux 5G non-terrestres (satellites, drones, HAPS) pour la connectivité globale."},
    {"id": 14, "titre": "5G Open RAN", "ecole": "IMT-BS Executive Education", "theme": "Réseaux & Télécoms", "duree": "3 jours", "format": "Présentiel", "niveau": "Ingénieur télécoms + 2 ans exp.", "prix": "NC", "fin": ["OPCO","Plan formation"], "reg": "Île-de-France", "kw": ["5G","Open RAN","Réseaux","Virtualisation"], "url": "https://www.imtexed.fr/fr/formation/reseaux-et-telecoms/1738665900-69-5g-open-ran", "rncp": None, "rncp_niveau": None, "rncp_eligible_cpf": False, "metiers_cibles": ["M1879","M1892"], "desc": "Architecture Open RAN, virtualisation des réseaux mobiles 5G."},
    {"id": 15, "titre": "Architecte 5G", "ecole": "IMT-BS Executive Education", "theme": "Réseaux & Télécoms", "duree": "5 jours", "format": "Présentiel", "niveau": "Bac+5 Télécoms + 3 ans exp.", "prix": "NC", "fin": ["OPCO","Plan formation"], "reg": "Île-de-France", "kw": ["5G","Architecture réseau","Core Network","Slice"], "url": "https://www.imtexed.fr/fr/formation/reseaux-et-telecoms/1738666055-70-architecte-5g", "rncp": None, "rncp_niveau": None, "rncp_eligible_cpf": False, "metiers_cibles": ["M1879","M1892","M1889"], "desc": "Conception d'architectures 5G end-to-end, network slicing, cœur de réseau."},
    # ── F16–F22 : Autres écoles IMT ──────────────────────────────────────────
    {"id": 16, "titre": "MS® IA Expert Data & MLops", "ecole": "Télécom Paris", "theme": "Numérique", "duree": "13–15 mois (dont 4–6 mois stage)", "format": "Présentiel", "niveau": "Bac+5 informatique/mathématiques", "prix": "NC", "fin": ["OPCO","CPF","Alternance"], "reg": "Île-de-France", "kw": ["IA","MLOps","Data","Machine Learning","Big Data"], "url": "https://www.telecom-paris.fr/fr/masteres-specialises/formation-big-data", "rncp": "RNCP40235", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1889","M1405","M1811"], "desc": "MS Télécom Paris. Big Data, MLOps, IA générative, déploiement modèles. RNCP40235."},
    {"id": 17, "titre": "MS® Cybersécurité des Infrastructures et des Données", "ecole": "Télécom SudParis", "theme": "Cybersécurité", "duree": "12–16 mois (temps partiel)", "format": "Hybride", "niveau": "Bac+4/5 informatique/réseaux", "prix": "NC", "fin": ["CPF","OPCO","Alternance"], "reg": "Île-de-France", "kw": ["Cybersécurité","NIS2","ANSSI","SecNumEdu","Audit"], "url": "https://www.telecom-sudparis.eu/formation/mastere-specialise-cybersecurite/", "rncp": "RNCP36855", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1856","K1906"], "desc": "MS Télécom SudParis. Label SecNumEdu ANSSI. RNCP36855."},
    {"id": 18, "titre": "MS® Cybersécurité & Cyberdéfense", "ecole": "Télécom Paris", "theme": "Cybersécurité", "duree": "9 mois cours + 4–6 mois stage", "format": "Présentiel", "niveau": "Bac+5 ingénieur informatique", "prix": "NC", "fin": ["CPF","OPCO"], "reg": "Île-de-France", "kw": ["Cybersécurité","Cyberdéfense","Réseaux","Cryptographie","IP"], "url": "https://www.telecom-paris.fr/fr/masteres-specialises/formation-cybersecurite-cyberdefense", "rncp": "RNCP35609", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1856","K1906","M1879"], "desc": "MS Télécom Paris. Sécurité réseaux IP, cryptographie, cyberdéfense."},
    {"id": 19, "titre": "MS® Cybersécurité (co-accrédité IMT Atlantique / CentraleSupélec)", "ecole": "IMT Atlantique", "theme": "Cybersécurité", "duree": "13 mois dont 5 mois mission entreprise", "format": "Présentiel", "niveau": "Bac+5 scientifique (info/réseaux)", "prix": "NC", "fin": ["CPF","OPCO","Alternance"], "reg": "Bretagne", "kw": ["Cybersécurité","ANSSI","SecNumEdu","Rennes","CentraleSupélec"], "url": "https://www.imt-atlantique.fr/fr/formation/masteres-specialises/cybersecurite", "rncp": "RNCP39837", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1856","K1906","M1879"], "desc": "Double diplôme IMT Atlantique + CentraleSupélec. Label SecNumEdu ANSSI. RNCP39837."},
    {"id": 20, "titre": "MS® Intelligence Artificielle", "ecole": "IMT Atlantique", "theme": "Numérique", "duree": "13 mois dont 6 mois stage", "format": "Présentiel", "niveau": "Bac+5 ingénieur ou Master scientifique", "prix": "NC", "fin": ["OPCO","CPF","Alternance"], "reg": "Bretagne / Pays de la Loire", "kw": ["IA","Machine Learning","Deep Learning","Data Science"], "url": "https://www.imt-atlantique.fr/fr/formation/masteres-specialises", "rncp": "RNCP38587", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1889","M1405","M1811"], "desc": "MS IMT Atlantique. IA avancée, ML, Deep Learning, applications industrielles. RNCP38587."},
    {"id": 21, "titre": "MS® Management Technologique & Innovation", "ecole": "IMT Mines Albi", "theme": "Management et Marketing", "duree": "12 mois en alternance", "format": "Hybride", "niveau": "Bac+5 ingénieur ou équivalent", "prix": "NC", "fin": ["OPCO","Alternance","CPF"], "reg": "Occitanie", "kw": ["Innovation","Management","Technologie","Transformation industrielle"], "url": "https://www.imt-mines-albi.fr/fr/integrer-une-formation/mastere-specialise-imt-mines-albi", "rncp": "RNCP35609", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1426","M1423","M1889"], "desc": "MS IMT Mines Albi. Innovation technologique, management de projets industriels complexes."},
    {"id": 22, "titre": "Formation Data Engineer RNCP41813 (CPF)", "ecole": "IMT Atlantique", "theme": "Numérique", "duree": "12 mois en alternance ou formation continue", "format": "Hybride", "niveau": "Bac+3 minimum + expérience dev/data", "prix": "NC", "fin": ["CPF","OPCO","Alternance"], "reg": "Bretagne / Pays de la Loire", "kw": ["Data Engineer","ETL","Pipeline","Big Data","Cloud"], "url": "https://www.imt-atlantique.fr/fr/formation/masteres-specialises", "rncp": "RNCP41813", "rncp_niveau": "Niv. 6", "rncp_eligible_cpf": True, "metiers_cibles": ["M1811","M1889","M1879"], "desc": "Formation Data Engineer certifiante RNCP41813. ETL, pipelines, Cloud, Big Data."},
    # ── F23–F32 : Partenaires ─────────────────────────────────────────────────
    {"id": 23, "titre": "Certificat Professionnel IA pour le Management", "ecole": "CNAM", "theme": "Numérique", "duree": "6 mois (temps partiel)", "format": "Hybride", "niveau": "Bac+2 + 3 ans exp. management", "prix": "3 900 €", "fin": ["CPF","OPCO","Plan formation"], "reg": "Nationale", "kw": ["IA","Management","Certificat","CNAM","CPF"], "url": "https://formation.cnam.fr/rechercher-par-discipline/intelligence-artificielle-et-systemes-informatiques-1078978.kjsp", "rncp": "RNCP38121", "rncp_niveau": "Niv. 6", "rncp_eligible_cpf": True, "metiers_cibles": ["M1426","M1423","M1419"], "desc": "CNAM. Certificat pro IA pour managers non-techniques. RNCP38121 Niv.6."},
    {"id": 24, "titre": "MS® IA, Décision, Management", "ecole": "CentraleSupélec", "theme": "Numérique", "duree": "18 mois (temps partiel)", "format": "Hybride", "niveau": "Bac+5 ingénieur ou équivalent", "prix": "15 500 €", "fin": ["OPCO","CPF","Plan formation"], "reg": "Île-de-France", "kw": ["IA","Décision","Management","MS","CentraleSupélec"], "url": "https://exed.centralesupelec.fr/formation/mastere-specialiseintelligence-artificielle-de-confiance/", "rncp": "RNCP36399", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1889","M1423","M1426"], "desc": "MS CentraleSupélec. IA de confiance, décision industrielle, management. RNCP36399."},
    {"id": 25, "titre": "Certificat IA & Stratégie pour Dirigeants", "ecole": "HEC Paris Executive Education", "theme": "Management et Marketing", "duree": "5 jours (intensif)", "format": "Présentiel", "niveau": "Dirigeant / Cadre dirigeant", "prix": "5 800 €", "fin": ["Plan formation","OPCO"], "reg": "Île-de-France", "kw": ["IA","Stratégie","Dirigeants","HEC","Executive"], "url": "https://www.hec.edu/fr/executive-education/parcours/digital-et-innovation", "rncp": None, "rncp_niveau": None, "rncp_eligible_cpf": False, "metiers_cibles": ["M1426","M1423"], "desc": "HEC Paris. IA pour dirigeants : stratégie, gouvernance, cas d'usage sectoriels."},
    {"id": 26, "titre": "IA Générative & Prompt Engineering — Ingénieur IA", "ecole": "OpenClassrooms", "theme": "Numérique", "duree": "12 mois (alternance ou CPF)", "format": "Distanciel", "niveau": "Bac+3 informatique ou expérience dev", "prix": "1 490 €", "fin": ["CPF","Alternance","OPCO"], "reg": "Nationale", "kw": ["IA générative","Prompt Engineering","LLM","Python","RAG"], "url": "https://openclassrooms.com/fr/paths/2053-ai-engineer", "rncp": "RS6424", "rncp_niveau": "Niv. 6", "rncp_eligible_cpf": True, "metiers_cibles": ["M1889","M1861","M1405"], "desc": "OpenClassrooms. IA générative, LLM, RAG, MLOps. Certification RS6424."},
    {"id": 27, "titre": "Executive MBA Digital & Intelligence Artificielle", "ecole": "ESCP Business School", "theme": "Management et Marketing", "duree": "18 mois (temps partiel)", "format": "Hybride", "niveau": "Bac+4 + 5 ans exp.", "prix": "24 900 €", "fin": ["OPCO","Plan formation","CPF"], "reg": "Île-de-France / Berlin", "kw": ["MBA","Digital","IA","Executive","Management"], "url": "https://escp.eu/fr/programmes/executive-education/executive-mba", "rncp": "RNCP35455", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1426","M1423","M1889"], "desc": "ESCP. Executive MBA Digital & IA pour dirigeants. RNCP35455."},
    {"id": 28, "titre": "Titre Professionnel Développeur en Intelligence Artificielle", "ecole": "AFPA", "theme": "Numérique", "duree": "8–12 mois", "format": "Présentiel", "niveau": "Bac+2 minimum + bases Python", "prix": "6 500 €", "fin": ["CPF","ARE","Plan formation","OPCO"], "reg": "Nationale (multi-centres)", "kw": ["Développeur IA","Python","Machine Learning","AFPA","Reconversion"], "url": "https://www.afpa.fr/formation-qualifiante/developpeur-en-intelligence-artificielle", "rncp": "RNCP38596", "rncp_niveau": "Niv. 6", "rncp_eligible_cpf": True, "metiers_cibles": ["M1889","M1861","M1405"], "desc": "AFPA. Titre Pro Développeur IA RNCP38596. Applications IA, Python, ML, déploiement."},
    {"id": 29, "titre": "Data Analyst Certifiant — Mines ParisTech PSL", "ecole": "DataScientest (Mines ParisTech PSL)", "theme": "Numérique", "duree": "11 semaines bootcamp ou 8,5 mois temps partiel", "format": "Distanciel", "niveau": "Bac+2 minimum + notions stats/marketing", "prix": "4 490 €", "fin": ["CPF","OPCO","AIF France Travail"], "reg": "Nationale", "kw": ["Data Analyst","Python","SQL","Power BI","Reconversion"], "url": "https://datascientest.com/formation-data-analyst", "rncp": "RNCP38177", "rncp_niveau": "Niv. 6", "rncp_eligible_cpf": True, "metiers_cibles": ["M1419","M1824","M1405"], "desc": "DataScientest × Mines Paris PSL. Data Analyst certifiant. Python, SQL, Power BI, ML."},
    {"id": 30, "titre": "Big Data, Analytics & IA — Certificat ESSEC", "ecole": "ESSEC Business School", "theme": "Numérique", "duree": "3–5 jours (présentiel)", "format": "Présentiel", "niveau": "Cadre + 5 ans exp.", "prix": "19 500 €", "fin": ["Plan formation","OPCO"], "reg": "Île-de-France", "kw": ["Big Data","Analytics","IA","ESSEC","Business Intelligence"], "url": "https://essec.edu/fr/programme/big-data-analytics-ia/", "rncp": "RNCP41186", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": False, "metiers_cibles": ["M1423","M1419","M1824"], "desc": "ESSEC Executive Education. Big Data, IA pour décideurs. RNCP41186."},
    {"id": 31, "titre": "MLOps & IA en Production", "ecole": "DataScientest (Liora)", "theme": "Numérique", "duree": "4 mois (temps partiel, 10h/semaine)", "format": "Distanciel", "niveau": "Bac+3 + bases ML/Python", "prix": "5 200 €", "fin": ["CPF","OPCO"], "reg": "Nationale", "kw": ["MLOps","DevOps","IA Production","Kubernetes","Docker"], "url": "https://liora.io/formation/data-ia/mlops", "rncp": "RNCP38587", "rncp_niveau": "Niv. 7", "rncp_eligible_cpf": True, "metiers_cibles": ["M1889","M1811","M1879"], "desc": "DataScientest/Liora. MLOps : déploiement, monitoring, industrialisation des modèles IA."},
    {"id": 32, "titre": "IA & Ressources Humaines — Transformation RH par l'IA", "ecole": "CNAM/IGS-RH", "theme": "Management et Marketing", "duree": "3 mois (temps partiel)", "format": "Hybride", "niveau": "Bac+3 + 3 ans exp. RH", "prix": "2 800 €", "fin": ["CPF","OPCO","Plan formation"], "reg": "Nationale", "kw": ["RH","IA","Ressources humaines","CNAM","Transformation"], "url": "https://formation.cnam.fr/rechercher-par-discipline/ressources-humaines-1078970.kjsp", "rncp": "RNCP37249", "rncp_niveau": "Niv. 6", "rncp_eligible_cpf": True, "metiers_cibles": ["M1423","M1426","K1906"], "desc": "CNAM/IGS-RH. IA appliquée aux RH : recrutement, GPEC, formation, automatisation."},
]


def build_catalogue_summary(formations=None) -> str:
    """Construit le résumé JSON du catalogue pour le prompt système.
    Accepte un sous-ensemble optionnel de formations (pour le ciblage par profil).
    """
    import json
    target = formations if formations is not None else FORMATIONS
    cats = []
    for f in target:
        metiers_titres = []
        for rome in (f.get("metiers_cibles") or []):
            j = JOBS_REF.get(rome)
            if j:
                metiers_titres.append(j["titre"])
        cats.append({
            "id": f["id"], "titre": f["titre"], "ecole": f["ecole"],
            "theme": f["theme"], "duree": f["duree"], "format": f["format"],
            "niveau": f["niveau"], "prix": f.get("prix") if f.get("prix") != "NC" else None,
            "fin": f["fin"], "reg": f["reg"], "kw": f["kw"],
            "rncp": f.get("rncp"), "rncp_niveau": f.get("rncp_niveau"),
            "cpf": f.get("rncp_eligible_cpf", False),
            "metiers": metiers_titres,
            "url": f.get("url"),
            "desc": f["desc"],
        })
    return json.dumps(cats, ensure_ascii=False)


def build_personas_summary() -> str:
    """Construit le résumé JSON des personas pour le prompt système."""
    import json
    return json.dumps([
        {"id": p["id"], "name": p["name"], "desc": p["desc"],
         "niveau": p["niv"], "financement": p["fin"],
         "region": p["reg"], "kw": p["kw"]}
        for p in PERSONAS
    ], ensure_ascii=False)


# ── Blocs de compétences RNCP (source : France Compétences 2024-2025) ────────
RNCP_BLOCS = {
    "RNCP38587": {
        "intitule": "Expert en ingénierie de l'intelligence artificielle",
        "niveau": "7", "niveau_fr": "Bac+5", "cpf": True,
        "blocs": [
            {"code": "BC01", "intitule": "Mesurer l'apport de l'IA dans la stratégie SI",
             "question": "Avez-vous déjà analysé ou proposé une stratégie IA pour une organisation ?",
             "chips": ["Oui, en entreprise", "Oui, en formation/projet", "Non mais je veux apprendre", "Pas encore"]},
            {"code": "BC02", "intitule": "Élaborer et mettre en production des modèles/algorithmes",
             "question": "Avez-vous déjà entraîné et déployé un modèle ML en production ?",
             "chips": ["Oui, en prod réelle", "Oui, en projet/POC", "J'ai fait du ML mais pas déployé", "Non, débutant"]},
            {"code": "BC03", "intitule": "Concevoir et piloter une infrastructure data",
             "question": "Gérez-vous des infrastructures de données (Cloud, pipelines, BDD) ?",
             "chips": ["Oui, AWS/GCP/Azure", "Oui, on-premise", "Notions de base", "Non"]},
            {"code": "BC04", "intitule": "Piloter un projet IA",
             "question": "Avez-vous déjà piloté un projet IA (cadrage, équipe, livraison) ?",
             "chips": ["Oui, chef de projet", "Partiellement (contributeur)", "Non mais je vise ce rôle", "Non"]},
        ],
        "metiers_rome": ["M1889", "M1405", "M1811"],
    },
    "RNCP37431": {
        "intitule": "Expert en data science",
        "niveau": "7", "niveau_fr": "Bac+5", "cpf": True,
        "blocs": [
            {"code": "BC01", "intitule": "Analyser, concevoir des modélisations mathématiques",
             "question": "Votre niveau en statistiques et mathématiques appliquées ?",
             "chips": ["Solide (Bac+5 maths/stats)", "Intermédiaire (Bac+3/4)", "Notions de base", "À renforcer"]},
            {"code": "BC02", "intitule": "Concevoir/déployer des solutions de Data Science",
             "question": "Maîtrisez-vous Python et les librairies Data Science (pandas, scikit-learn, TF) ?",
             "chips": ["Oui, très à l'aise", "Python oui, librairies en cours", "Débutant Python", "Pas encore"]},
            {"code": "BC03", "intitule": "Traitement données non structurées (NLP, vision)",
             "question": "Avez-vous travaillé sur du NLP (texte) ou de la vision par ordinateur ?",
             "chips": ["Oui les deux", "NLP seulement", "Vision seulement", "Ni l'un ni l'autre"]},
            {"code": "BC04", "intitule": "Manager des projets IA/Data Science complexes",
             "question": "Souhaitez-vous évoluer vers un rôle de management/lead Data Science ?",
             "chips": ["Oui, c'est mon objectif", "Peut-être à terme", "Je préfère rester expert tech", "Non"]},
        ],
        "metiers_rome": ["M1405", "M1889", "M1423"],
    },
    "RNCP35609": {
        "intitule": "Chef de Projets en Intelligence Artificielle et Data Science",
        "niveau": "7", "niveau_fr": "Bac+5", "cpf": True,
        "blocs": [
            {"code": "BC01", "intitule": "Identifier des cas d'usage IA créateurs de valeur",
             "question": "Savez-vous identifier des opportunités IA dans un contexte métier ?",
             "chips": ["Oui, c'est mon quotidien", "En cours d'apprentissage", "Quelques notions", "Non"]},
            {"code": "BC02", "intitule": "Élaborer un plan stratégique IA",
             "question": "Avez-vous déjà élaboré une roadmap ou un business case IA ?",
             "chips": ["Oui, plusieurs fois", "Une fois en projet", "Non mais je veux apprendre", "Non"]},
            {"code": "BC03", "intitule": "Manager les projets IA",
             "question": "Votre expérience en gestion de projets complexes ?",
             "chips": ["+5 ans chef de projet", "1-5 ans", "Moins d'1 an", "Aucune expérience"]},
            {"code": "BC04", "intitule": "Traiter et visualiser des données massives",
             "question": "Utilisez-vous des outils BI/visualisation (Power BI, Tableau, Looker) ?",
             "chips": ["Oui régulièrement", "Occasionnellement", "Peu", "Non"]},
            {"code": "BC05", "intitule": "Industrialiser les processus IA",
             "question": "Connaissez-vous les pratiques MLOps (CI/CD, monitoring de modèles) ?",
             "chips": ["Oui, je pratique", "Notions théoriques", "J'en ai entendu parler", "Non"]},
        ],
        "metiers_rome": ["M1889", "M1423", "M1426"],
    },
    "RNCP38919": {
        "intitule": "Data engineer",
        "niveau": "7", "niveau_fr": "Bac+5", "cpf": True,
        "blocs": [
            {"code": "BC01", "intitule": "Concevoir une architecture de données scalable",
             "question": "Avez-vous conçu des architectures data (data lake, data warehouse, lakehouse) ?",
             "chips": ["Oui en production", "Oui en projet", "Notions", "Non"]},
            {"code": "BC02", "intitule": "Développer des pipelines de données industrielles",
             "question": "Maîtrisez-vous les outils ETL/ELT et orchestration (Airflow, dbt, Spark) ?",
             "chips": ["Oui, plusieurs outils", "1-2 outils maîtrisés", "En cours d'apprentissage", "Non"]},
            {"code": "BC03", "intitule": "Déployer une solution d'analyse intégrant l'IA",
             "question": "Avez-vous intégré des modèles IA dans des pipelines de données ?",
             "chips": ["Oui régulièrement", "Ponctuellement", "Non mais je veux", "Non"]},
            {"code": "BC04", "intitule": "Piloter un projet d'architecture technique",
             "question": "Avez-vous une expérience de pilotage technique (lead, tech lead) ?",
             "chips": ["Oui, tech lead", "Contributeur senior", "Junior", "Non"]},
        ],
        "metiers_rome": ["M1811", "M1879", "M1889"],
    },
    "RNCP38616": {
        "intitule": "Concepteur développeur en IA et analyse Big Data",
        "niveau": "6", "niveau_fr": "Bac+3/4", "cpf": True,
        "blocs": [
            {"code": "BC01", "intitule": "Préparer les données pour l'analyse IA",
             "question": "Savez-vous nettoyer, transformer et préparer des données (pandas, SQL) ?",
             "chips": ["Oui, à l'aise", "Notions", "En cours d'apprentissage", "Non"]},
            {"code": "BC02", "intitule": "Analyser et synthétiser les données",
             "question": "Réalisez-vous des analyses statistiques et des visualisations de données ?",
             "chips": ["Oui régulièrement", "Occasionnellement", "Rarement", "Non"]},
            {"code": "BC03", "intitule": "Appliquer des techniques ML",
             "question": "Avez-vous appliqué des algorithmes ML (classification, régression…) ?",
             "chips": ["Oui, plusieurs projets", "1-2 projets", "Cours/tutoriels seulement", "Non"]},
            {"code": "BC04", "intitule": "Mener des projets IA/Big Data (éthique, légal)",
             "question": "Connaissez-vous les enjeux RGPD et éthique de l'IA ?",
             "chips": ["Oui, je les applique", "Notions générales", "Peu", "Non"]},
        ],
        "metiers_rome": ["M1419", "M1405", "M1824"],
    },
    "RNCP41813": {
        "intitule": "Chef de projet data et intelligence artificielle",
        "niveau": "7", "niveau_fr": "Bac+5", "cpf": True,
        "blocs": [
            {"code": "BC01", "intitule": "Cadrer un projet IA à partir de l'analyse du besoin client",
             "question": "Avez-vous déjà recueilli et analysé des besoins clients pour un projet IA/Data ?",
             "chips": ["Oui, régulièrement", "Quelques fois", "En cours d'apprentissage", "Non"]},
            {"code": "BC02", "intitule": "Sélectionner et interpréter les données d'une solution IA",
             "question": "Savez-vous évaluer la qualité et la pertinence des données pour un projet IA ?",
             "chips": ["Oui, expertise data", "Notions", "Très peu", "Non"]},
            {"code": "BC03", "intitule": "Conception et supervision d'une solution IA",
             "question": "Avez-vous supervisé ou contribué à la conception d'une solution IA complète ?",
             "chips": ["Oui, en supervision", "En tant que contributeur", "En projet étudiant", "Non"]},
            {"code": "BC04", "intitule": "Piloter un projet IA (AI Act, éthique)",
             "question": "Connaissez-vous la réglementation AI Act et ses implications projet ?",
             "chips": ["Oui, je l'applique", "Notions générales", "J'en ai entendu parler", "Non"]},
        ],
        "metiers_rome": ["M1423", "M1426", "M1889"],
    },
    "RNCP36581": {
        "intitule": "Développeur en Intelligence Artificielle et Data Science",
        "niveau": "6", "niveau_fr": "Bac+3/4", "cpf": True,
        "blocs": [
            {"code": "BC01", "intitule": "Concevoir et développer une solution IA",
             "question": "Avez-vous développé une application intégrant de l'IA ?",
             "chips": ["Oui en production", "Oui en projet/POC", "Tutoriels seulement", "Non"]},
            {"code": "BC02", "intitule": "Préparer les données pour une solution IA",
             "question": "Maîtrisez-vous la collecte, le nettoyage et le prétraitement de données ?",
             "chips": ["Oui, expertise", "Notions solides", "Débutant", "Non"]},
            {"code": "BC03", "intitule": "Développer les composants d'une solution IA",
             "question": "Programmez-vous en Python avec des frameworks IA (PyTorch, TF, HuggingFace) ?",
             "chips": ["Oui, plusieurs frameworks", "Python seul", "En cours d'apprentissage", "Non"]},
            {"code": "BC04", "intitule": "Gérer les activités du développement IA",
             "question": "Utilisez-vous des méthodes agiles et outils de versioning (Git, Jira) ?",
             "chips": ["Oui au quotidien", "Occasionnellement", "Peu", "Non"]},
        ],
        "metiers_rome": ["M1889", "M1405", "M1861"],
    },
}

# Index rapide : ROME → RNCPs prioritaires (ordre décroissant d'alignement)
ROME_TO_RNCP_PRIORITY = {
    "M1889": ["RNCP38587", "RNCP37431", "RNCP35609", "RNCP36581"],
    "M1405": ["RNCP38587", "RNCP37431", "RNCP34545", "RNCP38616"],
    "M1811": ["RNCP38919", "RNCP37172", "RNCP38587"],
    "M1419": ["RNCP38616", "RNCP34545", "RNCP37431"],
    "M1423": ["RNCP35609", "RNCP41813", "RNCP37431"],
    "M1426": ["RNCP35609", "RNCP41813"],
    "M1879": ["RNCP38919", "RNCP37172"],
    "M1856": ["RNCP38587", "RNCP35609"],
    "M1892": ["RNCP38587", "RNCP35609"],
    "K1906": ["RNCP35609", "RNCP41813"],
    "M1861": ["RNCP36581", "RNCP38616"],
    "M1824": ["RNCP38616", "RNCP34545"],
}
