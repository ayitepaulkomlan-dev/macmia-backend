import json, re, logging
from llama_cpp import Llama
from config import settings

logger = logging.getLogger(__name__)
_llm   = None
_embed = None

def get_llm():
    global _llm
    if _llm is None:
        logger.info("Chargement Llama 3.1 8B sur GPU...")
        _llm = Llama(
            model_path=settings.MAIN_MODEL_PATH,
            n_gpu_layers=settings.N_GPU_LAYERS,
            n_ctx=settings.N_CTX,
            n_batch=settings.N_BATCH,
            verbose=False,
        )
        logger.info("✅ LLM chargé")
    return _llm

def get_embed():
    global _embed
    if _embed is None:
        _embed = Llama(
            model_path=settings.EMBED_MODEL_PATH,
            n_gpu_layers=settings.N_GPU_LAYERS,
            embedding=True,
            n_ctx=2048,
            verbose=False,
        )
    return _embed

def format_messages(system, messages):
    prompt  = ""  # begin_of_text ajouté automatiquement par llama-cpp
    prompt += f"<|start_header_id|>system<|end_header_id|>\n{system}<|eot_id|>"
    for m in messages:
        prompt += f"<|start_header_id|>{m.get('role','user')}<|end_header_id|>\n{m.get('content','')}<|eot_id|>"
    prompt += "<|start_header_id|>assistant<|end_header_id|>\n"
    return prompt

def generate(system, messages, max_tokens=None):
    out = get_llm()(
        format_messages(system, messages),
        max_tokens=max_tokens or settings.MAIN_MAX_TOKENS,
        temperature=settings.MAIN_TEMPERATURE,
        stop=["<|eot_id|>", "<|end_of_text|>"],
    )
    return out["choices"][0]["text"].strip()

def parse_json_response(raw):
    text = re.sub(r"```json\s*", "", raw).replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    msg = re.search(r'"message"\s*:\s*"([\s\S]*?)"(?:\s*,|\s*\})', text)
    if msg:
        return {"message": msg.group(1), "formations": [], "quick_replies": ["Recommencer"], "persona_id": None}
    return {"message": raw[:500] or "Erreur.", "formations": [], "quick_replies": ["Recommencer"], "persona_id": None}

def embed_text(text):
    result = get_embed().create_embedding(f"search_document: {text}")
    return result["data"][0]["embedding"]

def history_to_langchain(messages):
    return [{"role": m.get("role","user"), "content": m.get("content","")} for m in messages]

def build_system_prompt():
    from catalogue import build_catalogue_summary, build_personas_summary, FORMATIONS
    catalogue = build_catalogue_summary()
    personas  = build_personas_summary()
    # Tronquer si trop long (max 3000 chars pour le catalogue)
    if len(catalogue) > 3000:
        catalogue = catalogue[:3000] + "\n... (catalogue tronqué)"
    if len(personas) > 1000:
        personas = personas[:1000] + "\n... (personas tronqués)"
    return f"""Tu es l'assistant MACMIA, expert en orientation formation IA, Data et Industrie du Futur pour les 8 Grandes Écoles IMT (France 2030).
RÈGLE : Tu ne recommandes QUE des formations du catalogue ci-dessous (ids 1 à {len(FORMATIONS)}).
## PERSONAS
{personas}
## CATALOGUE IMT
{catalogue}
Réponds UNIQUEMENT en JSON :
{{"persona_id":"id|null","persona_confidence":0.0,"message":"texte","formations":[{{"id":N,"raison_match":"..."}}],"quick_replies":["..."],"profile_tags":[],"profile_name":"","profile_role":""}}"""

# ── Alias compatibilité ancienne API ─────────────────────────────────────────
async def call_main_llm(messages_or_history, messages: list = None, max_tokens: int = None) -> str:
    # Supporte call_main_llm(history) et call_main_llm(system, messages)
    if messages is None:
        # Appelé avec un seul argument : history complète
        history = messages_or_history if isinstance(messages_or_history, list) else []
        system  = build_system_prompt()
        msgs    = [{"role": m.get("role","user"), "content": m.get("content","")}
                   if isinstance(m, dict) else {"role": m.role, "content": m.content}
                   for m in history]
        raw = generate(system, msgs, max_tokens)
        return parse_json_response(raw)
    else:
        # Appelé avec (system, messages)
        return generate(messages_or_history, messages, max_tokens)

async def call_extraction_llm(system: str, messages: list, max_tokens: int = None) -> str:
    return generate(system, messages, max_tokens or 500)

# Pour compatibilité LangChain
class FakeLLM:
    async def ainvoke(self, messages):
        system = ""
        msgs   = []
        for m in messages:
            if hasattr(m, "type") and m.type == "system":
                system = m.content
            else:
                role    = getattr(m, "type", "user").replace("human","user")
                content = getattr(m, "content", "")
                msgs.append({"role": role, "content": content})
        class R:
            content = generate(system, msgs)
        return R()

llm_main       = FakeLLM()
llm_extraction = FakeLLM()

# ── Alias supplémentaires ─────────────────────────────────────────────────────
async def call_bridging_llm(system: str, messages: list, max_tokens: int = None) -> str:
    return generate(system, messages, max_tokens or 300)

async def call_recommendation_message_llm(system: str, messages: list, max_tokens: int = None) -> dict:
    text = generate(system, messages, max_tokens)
    if isinstance(text, dict):
        return text
    return {"message": text if isinstance(text, str) else str(text), "quick_replies": [], "persona_id": None}

def _extract_qa_profile(messages: list):
    return [], []

def _prefilter_formations(answers_lower, answers_list) -> list:
    try:
        import json
        path = "/home/docker/macmia/backend/data/formations_imt.json"
        with open(path) as f:
            all_f = json.load(f)
        # Scoring par mots-cles
        query = (" ".join(answers_lower) if isinstance(answers_lower, list) else str(answers_lower)).lower()
        def score(f):
            s = 0
            titre = f.get("titre","").lower()
            desc  = f.get("desc","").lower()
            kw    = " ".join(f.get("kw",[])).lower()
            for word in query.split():
                if len(word) < 3: continue
                if word in titre: s += 3
                if word in kw:    s += 2
                if word in desc:  s += 1
            return s
        scored = sorted(all_f, key=score, reverse=True)
        # Retourner top 4 avec score > 0, sinon les 4 premiers
        top = [f for f in scored if score(f) > 0][:4]
        return top if top else scored[:4]
    except Exception as e:
        return []

def _build_profile_summary(profile: dict) -> str:
    return str(profile)

# llm_extract = alias de llm_main
llm_extract = llm_main
