"""Production config — 12-Factor: tất cả từ environment variables."""
import os
import logging
from dataclasses import dataclass, field
from typing import List


@dataclass
class Settings:
    # Server
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # App
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Lab 11 Guardrails Agent"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))

    # LLM
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    google_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))

    # Security
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", "dev-key-change-me"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "dev-jwt-secret"))
    allowed_origins: list = field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*").split(",")
    )

    # Rate limiting
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
    )

    # Budget
    daily_budget_usd: float = field(
        default_factory=lambda: float(os.getenv("DAILY_BUDGET_USD", "5.0"))
    )

    # Storage
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))

    # ============== Lab 11: Guardrails Configuration ==============
    # Allowed topics (banking)
    allowed_topics: List[str] = field(
        default_factory=lambda: [
            "banking", "account", "transaction", "transfer",
            "loan", "interest", "savings", "credit",
            "deposit", "withdrawal", "balance", "payment",
            "tai khoan", "giao dich", "tiet kiem", "lai suat",
            "chuyen tien", "the tin dung", "so du", "vay",
            "ngan hang", "atm",
        ]
    )

    # Blocked topics
    blocked_topics: List[str] = field(
        default_factory=lambda: [
            "hack", "exploit", "weapon", "drug", "illegal",
            "violence", "gambling", "bomb", "kill", "steal",
        ]
    )

    # ============== Lab 11: HITL Configuration ==============
    enable_hitl: bool = field(
        default_factory=lambda: os.getenv("ENABLE_HITL", "true").lower() == "true"
    )
    confidence_threshold_high: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_THRESHOLD_HIGH", "0.8"))
    )
    confidence_threshold_low: float = field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_THRESHOLD_LOW", "0.3"))
    )

    # ============== Lab 11: Guardrails Flags ==============
    enable_input_guardrails: bool = field(
        default_factory=lambda: os.getenv("ENABLE_INPUT_GUARDRAILS", "true").lower() == "true"
    )
    enable_output_guardrails: bool = field(
        default_factory=lambda: os.getenv("ENABLE_OUTPUT_GUARDRAILS", "true").lower() == "true"
    )
    enable_injection_detection: bool = field(
        default_factory=lambda: os.getenv("ENABLE_INJECTION_DETECTION", "true").lower() == "true"
    )
    enable_topic_filter: bool = field(
        default_factory=lambda: os.getenv("ENABLE_TOPIC_FILTER", "true").lower() == "true"
    )

    def validate(self):
        logger = logging.getLogger(__name__)
        if self.environment == "production":
            if self.agent_api_key == "dev-key-change-me":
                raise ValueError("AGENT_API_KEY must be set in production!")
            if self.jwt_secret == "dev-jwt-secret":
                raise ValueError("JWT_SECRET must be set in production!")
        if not self.openai_api_key and not self.google_api_key:
            logger.warning("OPENAI_API_KEY or GOOGLE_API_KEY not set — using mock LLM")
        return self


settings = Settings().validate()
