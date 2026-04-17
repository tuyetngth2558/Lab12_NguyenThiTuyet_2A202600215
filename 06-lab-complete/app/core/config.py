"""
Lab 11 Production — Configuration
12-Factor App compliant config management
"""
import os
from typing import List


def get_env(key: str, default: str = "") -> str:
    """Get environment variable with optional default."""
    return os.environ.get(key, default)


def get_env_int(key: str, default: int = 0) -> int:
    """Get environment variable as integer."""
    try:
        return int(get_env(key, str(default)))
    except ValueError:
        return default


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    val = get_env(key, str(default)).lower()
    return val in ("true", "1", "yes", "on")


# ============== API Configuration ==============
GOOGLE_API_KEY = get_env("GOOGLE_API_KEY", "")
GOOGLE_GENAI_USE_VERTEXAI = get_env("GOOGLE_GENAI_USE_VERTEXAI", "0")

# ============== Server Configuration ==============
HOST = get_env("HOST", "0.0.0.0")
PORT = get_env_int("PORT", 8080)
DEBUG = get_env_bool("DEBUG", False)

# ============== Guardrails Configuration ==============
# Allowed banking topics (used by topic_filter)
ALLOWED_TOPICS: List[str] = [
    "banking", "account", "transaction", "transfer",
    "loan", "interest", "savings", "credit",
    "deposit", "withdrawal", "balance", "payment",
    "tai khoan", "giao dich", "tiet kiem", "lai suat",
    "chuyen tien", "the tin dung", "so du", "vay",
    "ngan hang", "atm",
]

# Blocked topics (immediate reject)
BLOCKED_TOPICS: List[str] = [
    "hack", "exploit", "weapon", "drug", "illegal",
    "violence", "gambling", "bomb", "kill", "steal",
]

# ============== HITL Configuration ==============
CONFIDENCE_THRESHOLD_HIGH = get_env_float("CONFIDENCE_THRESHOLD_HIGH", 0.8)
CONFIDENCE_THRESHOLD_LOW = get_env_float("CONFIDENCE_THRESHOLD_LOW", 0.3)
ENABLE_HITL = get_env_bool("ENABLE_HITL", True)

# ============== Security Configuration ==============
API_KEY_REQUIRED = get_env_bool("API_KEY_REQUIRED", True)
RATE_LIMIT_REQUESTS = get_env_int("RATE_LIMIT_REQUESTS", 100)
RATE_LIMIT_WINDOW = get_env_int("RATE_LIMIT_WINDOW", 60)  # seconds


def get_env_float(key: str, default: float = 0.0) -> float:
    """Get environment variable as float."""
    try:
        return float(get_env(key, str(default)))
    except ValueError:
        return default


def setup_api_key():
    """Load Google API key from environment or prompt."""
    global GOOGLE_API_KEY
    if not GOOGLE_API_KEY:
        GOOGLE_API_KEY = input("Enter Google API Key: ")
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = GOOGLE_GENAI_USE_VERTEXAI
    print("API key loaded.")


def validate_config():
    """Validate required configuration."""
    errors = []
    
    if not GOOGLE_API_KEY:
        errors.append("GOOGLE_API_KEY is required")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")


# Initialize on import
if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = get_env("GOOGLE_API_KEY", "")