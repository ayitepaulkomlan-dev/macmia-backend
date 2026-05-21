from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MAIN_MODEL_PATH:  str = "/home/docker/models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
    EMBED_MODEL_PATH: str = "/home/docker/models/nomic-embed-text-v1.5.Q4_K_M.gguf"
    N_GPU_LAYERS:     int = 33
    N_CTX:            int = 8192
    N_BATCH:          int = 512
    MAIN_TEMPERATURE: float = 0.7
    MAIN_MAX_TOKENS:  int = 2500
    CHROMA_DIR:       str = "/home/docker/macmia/backend/chroma_db"
    COLLECTION_NAME:  str = "macmia_formations"
    HOST:             str = "0.0.0.0"
    PORT:             int = 8000
    # Compatibilité anciens routers
    OLLAMA_BASE_URL:  str = "http://localhost:11434"
    LLM_PROVIDER:     str = "anthropic"
    MAIN_MODEL:       str = "Meta-Llama-3.1-8B"
    EXTRACTION_MODEL: str = "nomic-embed-text"
    ANTHROPIC_API_KEY:str = ""

settings = Settings()
