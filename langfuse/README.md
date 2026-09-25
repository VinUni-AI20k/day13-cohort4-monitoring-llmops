# Langfuse Integration — LLM Observability

## 1. Cài đặt

```bash
pip install -r requirements.txt
```

## 2. Cấu hình

Tạo file `.env` với credentials từ [Langfuse Dashboard](https://cloud.langfuse.com):

```env
LANGFUSE_PUBLIC_KEY="pk-lf-..."
LANGFUSE_SECRET_KEY="sk-lf-..."
LANGFUSE_BASE_URL="https://us.cloud.langfuse.com"
```

## 3. Chạy server

```bash
python3 langfuse-integration.py
```

## 4. Test

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Thời tiết Hà Nội thế nào?", "user_id": "u_7842"}'
```

## 5. Xem trace trên Langfuse

Mở https://us.cloud.langfuse.com → **Traces** → click vào trace để xem chi tiết.

---

## 6. Giải thích code

### Trace Tree

Mỗi request `POST /chat` tạo ra một Trace trên Langfuse với cấu trúc:

```
[Trace] chat_agent_endpoint
  ├── [Span] tool_execution          ← @observe(name="tool_execution")
  └── [Generation] llm_generation    ← @observe(as_type="generation")
```

### Cách hoạt động

#### a. `@observe` decorator

Thay vì viết code tracing thủ công, Langfuse dùng decorator `@observe` để tự động:
- Tạo Span/Generation cho mỗi hàm
- Đo thời gian thực thi
- Capture input/output
- Lồng các span theo call hierarchy (parent-child)

```python
from langfuse import observe

@observe(name="tool_execution")
def execute_weather_tool(location: str):
    ...
```

#### b. `as_type="generation"` — đánh dấu LLM call

Khi gắn `as_type="generation"`, Langfuse nhận diện đây là lượt gọi LLM và hiển thị riêng biệt trên UI với thông tin model, token, cost:

```python
@observe(as_type="generation", name="llm_generation")
def call_llm(prompt: str):
    ...
```

#### c. `update_current_span()` / `update_current_generation()`

Bên trong hàm được `@observe`, dùng `get_client()` để bổ sung metadata:

| Loại span | Method | Dữ liệu bổ sung |
|-----------|--------|------------------|
| Span thường | `get_client().update_current_span(...)` | `metadata`, `output`, `level` |
| Generation (LLM) | `get_client().update_current_generation(...)` | `model`, `usage_details`, `cost_details`, `model_parameters` |

### So sánh với OpenTelemetry

| | OpenTelemetry | Langfuse |
|---|---|---|
| Cách tạo span | `tracer.start_as_current_span()` (thủ công) | `@observe` decorator (tự động) |
| LLM-specific | Tự gắn attributes theo GenAI conventions | Built-in `as_type="generation"` với token/cost tracking |
| UI | Jaeger / Tempo / Grafana | Langfuse Cloud UI (chuyên cho LLM) |
| Effort | Nhiều boilerplate hơn | Ít code hơn, tập trung vào LLMOps |
