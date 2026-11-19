import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/chatapp"
)
API_KEYS = {k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
PRICE_INPUT_PER_M = float(os.getenv("PRICE_INPUT_PER_M", "0.15"))
PRICE_OUTPUT_PER_M = float(os.getenv("PRICE_OUTPUT_PER_M", "0.60"))

RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "20"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600"))

MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "3000"))
MAX_CONTEXT_MESSAGES = int(os.getenv("MAX_CONTEXT_MESSAGES", "20"))

SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful, concise assistant.")
FRIENDLY_ERROR = (
    "Sorry, I'm having trouble reaching the AI service right now. "
    "Please try again in a moment."
)
