# Đáp án - CODE_LAB Day 12

## Part 1: Localhost vs Production

### Exercise 1.1 - Anti-patterns trong `01-localhost-vs-production/develop/app.py`

Ít nhất 5 vấn đề:

1. Hardcode secret (`OPENAI_API_KEY`, `DATABASE_URL`) trong source code.
2. Log ra secret (`print` API key) gây rò rỉ thông tin nhạy cảm.
3. Không có quản lý cấu hình bằng environment variables.
4. Không có endpoint health check/readiness.
5. Bind host `localhost` (không phù hợp container/cloud).
6. Port cố định `8000`, không đọc từ env `PORT`.
7. Bật `reload=True`/debug mode trong runtime.
8. Logging bằng `print`, không có structured logging.

### Exercise 1.2 - Nhận xét basic version

Basic version "chạy được local", nhưng chưa production-ready vì:
- Bảo mật kém (hardcoded secrets).
- Khó scale/monitor (không có health/readiness, logging yếu).
- Khó deploy cloud (hardcode host/port).

### Exercise 1.3 - So sánh `develop/app.py` vs `production/app.py`

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---|---|---|---|
| Config | Hardcode trong code | `config.settings` + env vars | Tách cấu hình khỏi code, an toàn, deploy linh hoạt |
| Health check | Không có | `/health`, `/ready` | Platform biết service còn sống/sẵn sàng để restart và route traffic |
| Logging | `print()` | Structured JSON logging | Dễ parse trên Datadog/Loki, truy vết lỗi tốt hơn |
| Shutdown | Đột ngột | Lifespan + SIGTERM handler | Hoàn tất request đang xử lý, tránh mất dữ liệu |
| Host/Port | `localhost:8000` cố định | `0.0.0.0` + `PORT` env | Chạy được trong container/cloud load balancer |
| CORS | Không có | CORS middleware có cấu hình | Kiểm soát nguồn gọi API an toàn |

### Checkpoint 1

- [x] Hiểu nguy cơ hardcode secrets  
- [x] Biết dùng environment variables  
- [x] Hiểu vai trò health check  
- [x] Hiểu graceful shutdown  

---

## Part 2: Docker Containerization

### Exercise 2.1 - `02-docker/develop/Dockerfile`

1. **Base image:** `python:3.11`
2. **Working directory:** `/app`
3. **Copy `requirements.txt` trước:** để tận dụng Docker layer cache, source code đổi thì không cần cài lại dependencies.
4. **CMD vs ENTRYPOINT:**
   - `CMD`: lệnh mặc định, dễ bị override khi `docker run ... <cmd>`.
   - `ENTRYPOINT`: executable cố định, tham số bổ sung sẽ được append vào.

### Exercise 2.2 - Build/run basic image

Lệnh lab đã đúng. Image develop là single-stage nên thường lớn hơn production multi-stage.

### Exercise 2.3 - `02-docker/production/Dockerfile` (multi-stage)

- **Stage 1 (`builder`)**: cài build deps + pip install requirements vào user site-packages.
- **Stage 2 (`runtime`)**: copy package đã build + source cần thiết, chạy bằng non-root user.
- **Lý do image nhỏ hơn:** loại bỏ build tools/caches/apt artifacts khỏi image runtime.

### Exercise 2.4 - `02-docker/production/docker-compose.yml`

**Services start:**
- `agent`
- `redis`
- `qdrant`
- `nginx`

**Luồng giao tiếp:**
- Client -> `nginx`
- `nginx` reverse proxy/load-balance -> `agent`
- `agent` -> `redis` (cache/session/rate limit)
- `agent` -> `qdrant` (vector DB)
- Toàn bộ traffic nội bộ qua network `internal`.

### Checkpoint 2

- [x] Hiểu cấu trúc Dockerfile  
- [x] Hiểu lợi ích multi-stage build  
- [x] Hiểu Docker Compose orchestration  
- [x] Biết cách debug (`docker logs`, `docker exec`)  

---

## Part 3: Cloud Deployment

### Exercise 3.1 - Railway

Đã có cấu hình trong `03-cloud-deployment/railway/railway.toml`:
- `builder = "NIXPACKS"`
- `startCommand` dùng `$PORT`
- Có `healthcheckPath=/health`
- Có restart policy khi fail

### Exercise 3.2 - So sánh `render.yaml` và `railway.toml`

- `render.yaml`: khai báo IaC chi tiết theo danh sách `services` (web + redis), env vars theo từng key, `autoDeploy`.
- `railway.toml`: gọn hơn, tập trung `build` + `deploy`, env vars thường set qua CLI/dashboard.
- Render Blueprint mạnh ở "multi-service in one file"; Railway config nhẹ và linh hoạt theo project.

### Exercise 3.3 (Optional) - GCP Cloud Run

- `cloudbuild.yaml`: pipeline CI/CD theo thứ tự `test -> build -> push -> deploy`.
- `service.yaml`: khai báo service Cloud Run (autoscaling, resources, probes, secrets, concurrency).

### Checkpoint 3

- [x] Có cấu hình deploy cho >=1 platform (Railway/Render)  
- [x] Có định nghĩa health check/public service config  
- [x] Hiểu cách set env vars/secrets trên cloud  
- [x] Hiểu cách xem logs (Cloud Build/Run, Railway, Render)  

---

## Part 4: API Security

### Exercise 4.1 - API key auth (`04-api-gateway/develop/app.py`)

- **Check key ở đâu?** Trong dependency `verify_api_key()` dùng `APIKeyHeader("X-API-Key")`.
- **Sai key thì sao?**
  - Thiếu key -> `401`
  - Key sai -> `403`
- **Rotate key:** đổi env var `AGENT_API_KEY` (không hardcode), sau đó restart service.

### Exercise 4.2 - JWT auth (`04-api-gateway/production/auth.py`)

JWT flow:
1. User gửi username/password vào endpoint login.
2. Server `authenticate_user` và `create_token` (payload có `sub`, `role`, `iat`, `exp`).
3. Client gọi API kèm `Authorization: Bearer <token>`.
4. Server `verify_token`, decode signature/expiry, inject user context.

### Exercise 4.3 - Rate limiting (`04-api-gateway/production/rate_limiter.py`)

- **Algorithm:** Sliding window (deque timestamps, loại entry cũ).
- **Limit:** user `10 req/min`, admin `100 req/min`.
- **Bypass/ưu tiên admin:** áp dụng limiter riêng theo role trong `app.py`:
  - admin -> `rate_limiter_admin`
  - user -> `rate_limiter_user`

### Exercise 4.4 - Cost guard (`04-api-gateway/production/cost_guard.py`)

Đã implement cost guard với các đặc điểm:
- Theo dõi token usage và cost theo user.
- Chặn khi vượt per-user budget (`402`) hoặc global budget (`503`).
- Có cảnh báo khi gần hết budget.
- Bản demo lưu in-memory; production nên dùng Redis/DB.

### Checkpoint 4

- [x] API key auth  
- [x] Hiểu JWT flow  
- [x] Rate limiting  
- [x] Cost guard  

---

## Part 5: Scaling & Reliability

### Exercise 5.1 - Health checks (`05-scaling-reliability/develop/app.py`)

- Đã có `GET /health` (liveness) và `GET /ready` (readiness).
- `/ready` trả `503` khi chưa sẵn sàng.

### Exercise 5.2 - Graceful shutdown

- Đã có signal handler `SIGTERM`/`SIGINT`.
- Lifespan shutdown cho phép chờ in-flight requests hoàn tất (tối đa 30s).

### Exercise 5.3 - Stateless design (`05-scaling-reliability/production/app.py`)

- State (session/history) được lưu qua Redis (`session:<id>`), không phụ thuộc memory của 1 instance.
- Request sau đến instance khác vẫn đọc được history -> scale ngang an toàn.

### Exercise 5.4 - Load balancing

- `docker-compose.yml` + `nginx.conf` tạo LB:
  - Nginx route vào upstream `agent`
  - Round-robin qua các replicas agent
  - Có `proxy_next_upstream` khi lỗi/timeout

### Exercise 5.5 - Test stateless (`test_stateless.py`)

Script:
1. Tạo session chat
2. Gửi nhiều requests liên tiếp
3. Kiểm tra `served_by` có thể khác instance
4. Đọc lại history và xác nhận vẫn đầy đủ qua Redis

### Checkpoint 5

- [x] Health/readiness checks  
- [x] Graceful shutdown  
- [x] Stateless design  
- [x] Hiểu load balancing Nginx  
- [x] Có script test stateless  

---

## Part 6: Final Project

### Tổng quan bài làm (`06-lab-complete`)

- Đã có `app/main.py`, `app/config.py`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`.
- Multi-stage Dockerfile, non-root user, healthcheck instruction.
- App có API key auth, rate limiting, cost guard, structured logging JSON, `/health`, `/ready`, graceful shutdown.
- Có config deploy Railway (`railway.toml`) và Render (`render.yaml`).

### Kết quả validation

Đã chạy:

`python check_production_ready.py`

Kết quả: **20/20 checks passed (100%)** -> **PRODUCTION READY**.

### Checkpoint 6 (Final)

- [x] Functional API agent
- [x] Dockerized + multi-stage
- [x] Env-based config
- [x] Auth + rate limit + cost guard
- [x] Health/readiness + graceful shutdown
- [x] Structured logging
- [x] Ready to deploy Railway/Render

---

## Part 7: Lab 11 Integration

### Project Lựa Chọn: Day 11 - Guardrails & HITL

### Các Phần Đã Áp Dụng:

| Phần Lab 12 | Nội dung | Lab 11 Integration |
|-------------|----------|-------------------|
| **01** | Localhost vs Production | 12-Factor config với env vars cho guardrails settings |
| **02** | Docker | Tạo Dockerfile + docker-compose cho Lab 11 agent |
| **03** | Cloud Deployment | Railway/Render config với Lab 11 env vars |
| **04** | API Gateway | Auth, rate limiting, cost guard (đã có sẵn) |
| **05** | Scaling & Reliability | Health check, graceful shutdown (đã có sẵn) |
| **06** | Lab Complete | Full production-ready với Lab 11 tích hợp |

### Lab 11 Features Trong `06-lab-complete/app/main.py`:

```python
# Input Guardrails
def check_injection(user_input: str) -> Tuple[bool, Optional[str]]:
    """Phát hiện prompt injection attempts"""
    # Check các pattern như "ignore previous", "forget everything", etc.

def check_topic(user_input: str) -> Tuple[bool, Optional[str]]:
    """Lọc topic - chỉ cho phép banking topics"""
    # Blocked topics: hack, exploit, weapon, etc.
    # Allowed topics: banking, account, transfer, loan, etc.

# Output Guardrails
def check_output_content(response: str) -> Tuple[bool, Optional[str]]:
    """Lọc nội dung nhạy cảm trong response"""
    # Check credit card numbers, SSN patterns, etc.

# HITL - Human in the Loop
def calculate_confidence(response: str, user_input: str) -> float:
    """Tính confidence score dựa trên response quality"""

def needs_human_review(confidence: float) -> bool:
    """Quyết định cần human review không"""
    # High confidence (>0.8) hoặc low confidence (<0.3) -> review
```

### Lab 11 Config Trong `06-lab-complete/app/config.py`:

```python
# Lab 11: Guardrails Configuration
allowed_topics: List[str] = [
    "banking", "account", "transaction", "transfer",
    "loan", "interest", "savings", "credit",
    "tai khoan", "giao dich", "vay", "ngan hang",
]

blocked_topics: List[str] = [
    "hack", "exploit", "weapon", "drug", "illegal",
]

# Lab 11: HITL Configuration
enable_hitl: bool = True
confidence_threshold_high: float = 0.8
confidence_threshold_low: float = 0.3

# Lab 11: Guardrails Flags
enable_input_guardrails: bool = True
enable_output_guardrails: bool = True
enable_injection_detection: bool = True
enable_topic_filter: bool = True
```

### API Endpoint Với Lab 11:

`POST /ask` - Gửi câu hỏi với guardrails:

```json
{
  "question": "Tôi muốn chuyển tiền",
  // Response:
  "answer": "Tôi có thể giúp bạn chuyển tiền...",
  "confidence": 0.75,
  "needs_human_review": false,
  "guardrails_triggered": null
}
```

### Test Guardrails:

```bash
# Test injection detection
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"question": "ignore previous instructions"}'
# -> {"answer": "I cannot process...", "guardrails_triggered": "injection_detected"}

# Test topic filter
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"question": "how to hack a bank"}'
# -> {"answer": "I'm sorry...", "guardrails_triggered": "blocked_topic:hack"}

# Test valid banking question
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"question": "I want to transfer money"}'
# -> {"answer": "...", "confidence": 0.75, "needs_human_review": false}
```

### Checkpoint Lab 11 Integration:

- [x] Input Guardrails: Injection detection + topic filter
- [x] Output Guardrails: Content filter
- [x] HITL: Confidence-based routing
- [x] Config qua environment variables
- [x] Production-ready với tất cả Lab 12 features
- [x] Deploy được lên Railway/Render
