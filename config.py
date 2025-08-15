from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


def _b(s: str, default: bool = False) -> bool:
    return os.getenv(s, str(default)).strip().lower() in {"1","true","yes","y","on"}


# Access the environment variables
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
#BING_API_KEY = os.getenv("BING_API_KEY")

# You can also add any additional config or fallback values here:
DEFAULT_LANGUAGE = "en"

# Ollama / models
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL       = os.getenv("LLM_MODEL", "mistral:latest")
EMBED_MODEL     = os.getenv("EMBED_MODEL", "nomic-embed-text:latest")

# Vector store
VECTOR_DB_DIR = os.getenv("VECTOR_DB_DIR", "./database/chroma")
CHROMA_COLLECTION_PREFIX = os.getenv("CHROMA_COLLECTION_PREFIX", "news_")

SAFETY_ENABLED = os.getenv("SAFETY_ENABLED", "true").lower() == "true"
TOXICITY_THRESHOLD = float(os.getenv("TOXICITY_THRESHOLD", "0.75"))
BLOCK_ADULT   = os.getenv("BLOCK_ADULT", "true").lower() == "true"
BLOCK_HATE    = os.getenv("BLOCK_HATE", "true").lower() == "true"
BLOCK_VIOLENCE= os.getenv("BLOCK_VIOLENCE", "true").lower() == "true"
SAFESEARCH_GOOGLE = os.getenv("SAFESEARCH_GOOGLE", "true").lower() == "true"

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

APP_DB_URL = os.getenv("APP_DB_URL", "sqlite:///./database/app.db")
JWT_SECRET   = os.getenv("JWT_SECRET", "dev-secret")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me") 

DB_RESET_ON_STARTUP = _b("DB_RESET_ON_STARTUP", False)

DEFAULT_REGION = os.getenv("DEFAULT_REGION", "us")  
DEFAULT_LANG   = os.getenv("DEFAULT_LANG", "en") 