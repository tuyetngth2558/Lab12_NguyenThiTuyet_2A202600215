"""
Production AI Agent — Kết hợp tất cả Day 12 concepts + Lab 11 Guardrails

Checklist:
  ✅ Config từ environment (12-factor)
  ✅ Structured JSON logging
  ✅ API Key authentication
  ✅ Rate limiting
  ✅ Cost guard
  ✅ Input validation (Pydantic)
  ✅ Health check + Readiness probe
  ✅ Graceful shutdown
  ✅ Security headers
  ✅ CORS
  ✅ Error handling
  ✅ Lab 11: Input Guardrails (injection detection, topic filter)
  ✅ Lab 11: Output Guardrails (content filter)
  ✅ Lab 11: HITL (confidence-based routing)
"""
import os
import time
import signal
import logging
import json
import re
from datetime import datetime, timezone
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Optional, Tuple

from fastapi import FastAPI, HTTPException, Security, Depends, Request, Response
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings

# Mock LLM (thay bằng OpenAI/Anthropic khi có API key)
from utils.mock_llm import ask as llm_ask

# ─────────────────────────────────────────────────────────
# Logging — JSON structured
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0

# ─────────────────────────────────────────────────────────
# Simple In-memory Rate Limiter
# ─────────────────────────────────────────────────────────
_rate_windows: dict[str, deque] = defaultdict(deque)

def check_rate_limit(key: str):
    now = time.time()
    window = _rate_windows[key]
    while window and window[0] < now - 60:
        window.popleft()
    if len(window) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
            headers={"Retry-After": "60"},
        )
    window.append(now)

# ─────────────────────────────────────────────────────────
# Simple Cost Guard
# ─────────────────────────────────────────────────────────
_daily_cost = 0.0
_cost_reset_day = time.strftime("%Y-%m-%d")

def check_and_record_cost(input_tokens: int, output_tokens: int):
    global _daily_cost, _cost_reset_day
    today = time.strftime("%Y-%m-%d")
    if today != _cost_reset_day:
        _daily_cost = 0.0
        _cost_reset_day = today
    if _daily_cost >= settings.daily_budget_usd:
        raise HTTPException(503, "Daily budget exhausted. Try tomorrow.")
    cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
    _daily_cost += cost


# ═══════════════════════════════════════════════════════════════
# LAB 11: GUARDRAILS - Input Guardrails
# ═══════════════════════════════════════════════════════════════
def check_injection(user_input: str) -> Tuple[bool, Optional[str]]:
    """
    Check for prompt injection attempts.
    Returns: (is_injection, reason)
    """
    if not settings.enable_injection_detection:
        return False, None
    
    injection_patterns = [
        r"ignore\s+(previous|all|instructions)",
        r"disregard\s+(previous|all|instructions)",
        r"forget\s+(everything|all|previous)",
        r"new\s+instructions",
        r"override\s+(system|previous)",
        r"you\s+are\s+now",
        r"system\s+prompt",
        r"bypass\s+(security|filter)",
        r"ignore\s+previous",
        r"disregard\s+previous",
    ]
    
    lower_input = user_input.lower()
    for pattern in injection_patterns:
        if re.search(pattern, lower_input):
            return True, "injection_detected"
    
    return False, None


def check_topic(user_input: str) -> Tuple[bool, Optional[str]]:
    """
    Check if input is in allowed topics.
    Returns: (is_allowed, reason)
    """
    if not settings.enable_topic_filter:
        return True, None
    
    lower_input = user_input.lower()
    
    # Check blocked topics first
    for topic in settings.blocked_topics:
        if topic in lower_input:
            return False, f"blocked_topic:{topic}"
    
    # Check allowed topics
    for topic in settings.allowed_topics:
        if topic in lower_input:
            return True, None
    
    return False, "off_topic"


# ═══════════════════════════════════════════════════════════════
# LAB 11: GUARDRAILS - Output Guardrails
# ═══════════════════════════════════════════════════════════════
def check_output_content(response: str) -> Tuple[bool, Optional[str]]:
    """
    Check output for sensitive content.
    Returns: (is_safe, reason)
    """
    if not settings.enable_output_guardrails:
        return True, None
    
    # Simple content filter - check for sensitive patterns
    sensitive_patterns = [
        r"\b\d{10,16}\b",  # Credit card numbers
        r"\b\d{9,12}\b",   # SSN-like patterns
    ]
    
    for pattern in sensitive_patterns:
        if re.search(pattern, response):
            return False, "sensitive_data_detected"
    
    return True, None


# ═══════════════════════════════════════════════════════════════
# LAB 11: HITL - Confidence-based routing
# ═══════════════════════════════════════════════════════════════
def calculate_confidence(response: str, user_input: str) -> float:
    """
    Calculate confidence score for response.
    Returns: confidence score between 0 and 1
    """
    if not settings.enable_hitl:
        return 1.0  # No HITL, full confidence
    
    score = 0.5
    
    # Length-based scoring
    if len(response) > 50:
        score += 0.1
    if len(response) > 200:
        score += 0.1
    
    # Content quality indicators
    response_lower = response.lower()
    if any(word in response_lower for word in ["however", "therefore", "additionally", "moreover"]):
        score += 0.1
    
    # Check if response addresses the input
    input_keywords = set(user_input.lower().split())
    response_words = set(response_lower.split())
    overlap = len(input_keywords & response_words) / max(len(input_keywords), 1)
    if overlap > 0.3:
        score += 0.2
    
    return min(score, 1.0)


def needs_human_review(confidence: float) -> bool:
    """
    Determine if response needs human review based on confidence thresholds.
    """
    if not settings.enable_hitl:
        return False
    
    # High confidence (very sure) or low confidence (very unsure) needs review
    return confidence > settings.confidence_threshold_high or confidence < settings.confidence_threshold_low


# ─────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    # Skip auth if no API key configured (for testing)
    if not settings.agent_api_key or settings.agent_api_key == "dev-key-change-me":
        return "test-user"
    if not api_key or api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    return api_key

# ─────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }))
    time.sleep(0.1)  # simulate init
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

# ─────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # Remove server header for security (use try/except for compatibility)
        try:
            del response.headers["server"]
        except KeyError:
            pass
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception as e:
        _error_count += 1
        raise

# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="Your question for the agent")

class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    timestamp: str
    # Lab 11: Guardrails & HITL fields
    confidence: Optional[float] = None
    needs_human_review: bool = False
    guardrails_triggered: Optional[str] = None


# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
            "config": "GET /config (Lab 11 guardrails config)",
        },
    }


@app.get("/config", tags=["Lab 11"])
def get_config():
    """Get Lab 11 guardrails configuration (non-sensitive)."""
    return {
        "allowed_topics": settings.allowed_topics,
        "blocked_topics": settings.blocked_topics,
        "enable_hitl": settings.enable_hitl,
        "confidence_threshold_high": settings.confidence_threshold_high,
        "confidence_threshold_low": settings.confidence_threshold_low,
        "enable_input_guardrails": settings.enable_input_guardrails,
        "enable_output_guardrails": settings.enable_output_guardrails,
        "enable_injection_detection": settings.enable_injection_detection,
        "enable_topic_filter": settings.enable_topic_filter,
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    """
    Send a question to the AI agent with Lab 11 Guardrails & HITL.

    **Authentication:** Include header `X-API-Key: <your-key>`
    
    **Lab 11 Features:**
    - Input Guardrails: Injection detection, topic filter
    - Output Guardrails: Content filter
    - HITL: Confidence-based routing for human review
    """
    # Rate limit per API key
    check_rate_limit(_key[:8])  # use first 8 chars as key bucket

    # Budget check
    input_tokens = len(body.question.split()) * 2
    check_and_record_cost(input_tokens, 0)

    logger.info(json.dumps({
        "event": "agent_call",
        "q_len": len(body.question),
        "client": str(request.client.host) if request.client else "unknown",
    }))

    # ═══════════════════════════════════════════════════════════
    # LAB 11: INPUT GUARDRAILS
    # ═══════════════════════════════════════════════════════════
    guardrails_triggered = None
    
    if settings.enable_input_guardrails:
        # Step 1: Injection Detection
        is_injection, injection_reason = check_injection(body.question)
        if is_injection:
            logger.warning(json.dumps({
                "event": "guardrail_blocked",
                "type": "injection",
                "reason": injection_reason,
            }))
            return AskResponse(
                question=body.question,
                answer="I cannot process this request due to security concerns.",
                model=settings.llm_model,
                timestamp=datetime.now(timezone.utc).isoformat(),
                confidence=1.0,
                needs_human_review=False,
                guardrails_triggered=injection_reason,
            )
        
        # Step 2: Topic Filter
        is_allowed, topic_reason = check_topic(body.question)
        if not is_allowed:
            logger.warning(json.dumps({
                "event": "guardrail_blocked",
                "type": "topic",
                "reason": topic_reason,
            }))
            return AskResponse(
                question=body.question,
                answer="I'm sorry, but I can only assist with banking-related inquiries.",
                model=settings.llm_model,
                timestamp=datetime.now(timezone.utc).isoformat(),
                confidence=1.0,
                needs_human_review=False,
                guardrails_triggered=topic_reason,
            )

    # Step 3: Get agent response
    answer = llm_ask(body.question)

    # ═══════════════════════════════════════════════════════════
    # LAB 11: OUTPUT GUARDRAILS
    # ═══════════════════════════════════════════════════════════
    if settings.enable_output_guardrails:
        is_safe, content_reason = check_output_content(answer)
        if not is_safe:
            logger.warning(json.dumps({
                "event": "guardrail_blocked",
                "type": "output_content",
                "reason": content_reason,
            }))
            answer = "I cannot provide this information due to security concerns."

    output_tokens = len(answer.split()) * 2
    check_and_record_cost(0, output_tokens)

    # ═══════════════════════════════════════════════════════════
    # LAB 11: HITL - Confidence-based routing
    # ═══════════════════════════════════════════════════════════
    confidence = calculate_confidence(answer, body.question)
    review_needed = needs_human_review(confidence)
    
    logger.info(json.dumps({
        "event": "hitl_check",
        "confidence": confidence,
        "needs_review": review_needed,
    }))

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence=confidence,
        needs_human_review=review_needed,
        guardrails_triggered=guardrails_triggered,
    )


@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe. Platform restarts container if this fails."""
    status = "ok"
    checks = {"llm": "mock" if not settings.openai_api_key else "openai"}
    return {
        "status": status,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe. Load balancer stops routing here if not ready."""
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True}


@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    """Basic metrics (protected)."""
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "daily_cost_usd": round(_daily_cost, 4),
        "daily_budget_usd": settings.daily_budget_usd,
        "budget_used_pct": round(_daily_cost / settings.daily_budget_usd * 100, 1),
    }


# ─────────────────────────────────────────────────────────
# Graceful Shutdown
# ─────────────────────────────────────────────────────────
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"API Key: {settings.agent_api_key[:4]}****")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
