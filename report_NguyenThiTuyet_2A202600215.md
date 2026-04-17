# BÁO CÁO NỘP BÀI DAY 12 - NguyenThiTuyet_2A202600215

## Thông Tin Sinh Viên

- **Họ và tên:** Nguyễn Thị Tuyết  
- **Mã sinh viên:** 2A202600215  
- **Ngày lập báo cáo:** 17/04/2026

---

## 1) Đánh Giá Theo Yêu Cầu Nộp Bài

### 1.1 Mission Answers (40 điểm)

**Yêu cầu:** Có file `MISSION_ANSWERS.md` trả lời đầy đủ các bài tập.

**Trạng thái hiện tại:**
- [x] Đã có file `MISSION_ANSWERS.md` đầy đủ
- [x] Trả lời đầy đủ Part 1 → Part 6
- [x] Có checkpoint từng phần

### 1.2 Full Source Code - Lab 06 Complete (60 điểm)

**Kiểm tra cấu trúc trong `06-lab-complete/`:**
- [x] `app/main.py` - FastAPI app với Lab 11 guardrails tích hợp
- [x] `app/config.py` - 12-Factor config với Lab 11 settings
- [x] `Dockerfile` - Multi-stage build
- [x] `docker-compose.yml` - Full stack với Redis
- [x] `requirements.txt` - Dependencies
- [x] `.env.example` - Environment template với Lab 11 vars
- [x] `.dockerignore` - Docker ignore
- [x] `railway.toml` - Railway config
- [x] `render.yaml` - Render config với Lab 11 env vars
- [x] `README.md` - Setup instructions
- [x] `utils/mock_llm.py` - Mock LLM với banking responses

**Lab 11 Integration (Project được chọn để áp dụng):**
- [x] Input Guardrails: Injection detection, topic filter
- [x] Output Guardrails: Content filter
- [x] HITL: Confidence-based routing
- [x] API Security: API Key auth, rate limiting, cost guard
- [x] Production Ready: Health check, graceful shutdown, JSON logging

**Kiểm tra quality gate:**
- [x] Đã chạy `06-lab-complete/check_production_ready.py`
- [x] Kết quả: **20/20 checks passed (100%)**
- [x] Multi-stage Dockerfile (< 500MB)
- [x] Có auth, rate limit, cost guard
- [x] Có health/readiness
- [x] Có graceful shutdown (SIGTERM)
- [x] Không hardcoded secrets nguy hiểm

### 1.3 Service Domain Link

**Yêu cầu:** Có file `DEPLOYMENT.md` + public URL đang chạy.

**Trạng thái hiện tại:**
- [x] Đã tạo file `DEPLOYMENT.md` với hướng dẫn deploy
- [x] Có cấu hình deploy: `railway.toml` và `render.yaml`
- [x] Đã deploy thành công lên Railway
- [x] **URL:** `https://lab12nguyenthituyet2a202600215-production.up.railway.app`


---

## 3) Lab 11 Integration - Project Được Chọn

### Project: Day 11 - Guardrails & HITL

Đã áp dụng Lab 12 concepts vào project Lab 11:

| Phần Lab 12 | Lab 11 Features Tích Hợp |
|-------------|-------------------------|
| 01-Localhost vs Production | 12-Factor config, env vars cho guardrails |
| 02-Docker | Dockerfile + docker-compose cho Lab 11 agent |
| 03-Cloud Deployment | Railway/Render config với Lab 11 settings |
| 04-API Gateway | Auth, rate limiting, cost guard |
| 05-Scaling & Reliability | Health check, stateless |
| 06-Lab Complete | Full production-ready với Lab 11 |

### Lab 11 Features Trong `06-lab-complete/app/main.py`:

```python
# Input Guardrails
- check_injection(): Phát hiện prompt injection
- check_topic(): Lọc topic (banking only)

# Output Guardrails  
- check_output_content(): Lọc nội dung nhạy cảm

# HITL
- calculate_confidence(): Tính confidence score
- needs_human_review(): Quyết định cần human review
```

### Config trong `06-lab-complete/app/config.py`:

```python
# Lab 11: Guardrails Configuration
allowed_topics: List[str] = [...]
blocked_topics: List[str] = [...]

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

---

## 5) Part 5 - Scaling & Reliability

### 5.1 Health Checks

- Đã triển khai đầy đủ 2 endpoint:
  - `GET /health` (liveness probe): kiểm tra service còn sống.
  - `GET /ready` (readiness probe): kiểm tra service đã sẵn sàng nhận traffic.
- Hành vi mong đợi:
  - Trả `200` khi hệ thống hoạt động bình thường.
  - Trả `503` ở `/ready` khi chưa sẵn sàng (ví dụ dependency chưa kết nối).

### 5.2 Graceful Shutdown

- Ứng dụng đã xử lý tín hiệu `SIGTERM` khi container/orchestrator yêu cầu dừng.
- Có cơ chế chờ các request đang xử lý (in-flight requests) hoàn tất trước khi thoát.
- Lợi ích:
  - Tránh fail request đột ngột.
  - Giảm nguy cơ mất dữ liệu hoặc trạng thái xử lý dở.

### 5.3 Stateless Design

- Trạng thái hội thoại/session không lưu cứng trong memory của một instance.
- Dữ liệu trạng thái được đưa ra lớp lưu trữ dùng chung (Redis) để nhiều instance cùng truy cập.
- Ý nghĩa khi scale ngang:
  - Request tiếp theo của cùng người dùng có thể đi vào instance bất kỳ.
  - Conversation/history vẫn liên tục và nhất quán.

### 5.4 Load Balancing

- Đã thiết kế mô hình cân bằng tải qua `nginx` trong `docker-compose`.
- Traffic từ client được phân phối vào cụm `agent` thay vì một instance duy nhất.
- Khi một instance lỗi, Nginx có thể chuyển tiếp sang instance còn sống theo cấu hình failover/retry.

### 5.5 Test Stateless

- Có script test tự động: `05-scaling-reliability/production/test_stateless.py`.
- Kịch bản test:
  1. Tạo session và gửi nhiều lượt hội thoại.
  2. Quan sát request được phục vụ bởi nhiều instance khác nhau (`served_by`).
  3. Kiểm tra lại history để xác nhận dữ liệu vẫn đầy đủ.
- Kết luận: thiết kế stateless đạt mục tiêu, phù hợp triển khai nhiều replica.

### Đánh Giá Checkpoint Part 5

- [x] Implement health và readiness checks  
- [x] Implement graceful shutdown  
- [x] Refactor theo hướng stateless  
- [x] Hiểu và áp dụng load balancing với Nginx  
- [x] Có kiểm thử cho stateless design  

---


