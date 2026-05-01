"""Central configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
INDEX_DIR  = DATA_DIR / "indices"
RESULTS_DIR = DATA_DIR / "results"
CHAT_DIR   = DATA_DIR / "chats"

OPENROUTER_API_KEY  = (os.getenv("OPENROUTER_API_KEY") or "").strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
EMBEDDING_MODEL     = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag_benchmark")

AVAILABLE_MODELS = [
    {"id": "openai/gpt-4o",                "name": "GPT-4o"},
    {"id": "openai/gpt-4o-mini",           "name": "GPT-4o Mini"},
    {"id": "anthropic/claude-sonnet-4",  "name": "Claude Sonnet 4"},
    {"id": "anthropic/claude-haiku-3.5",    "name": "Claude 3.5 Haiku"},
    {"id": "google/gemini-2.0-flash-001",   "name": "Gemini 2.0 Flash"},
    {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B"},
    {"id": "deepseek/deepseek-chat-v3-0324","name": "DeepSeek V3"},
    {"id": "mistralai/mistral-large-2411",  "name": "Mistral Large"},
]
