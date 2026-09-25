# OpenTelemetry Tracing Demo — AI Agent Service

## 1. Cài đặt

```bash
pip3 install -r requirements.txt
```

## 2. Chạy server

```bash
python3 oltp.py
```

## 3. Test

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Thời tiết Hà Nội thế nào?"}'
```

---

## 4. Tích hợp Jaeger (Trace Visualization)

Code trong `oltp.py` đã được cấu hình sẵn để đẩy trace sang Jaeger qua OTLP gRPC:

```python
resource = Resource.create({
    "service.name": "ai-agent-service",
    "service.version": "1.0.0",
    "deployment.environment": "development"
})

jaeger_otlp_exporter = OTLPSpanExporter(
    endpoint="localhost:4317",
    insecure=True
)
provider.add_span_processor(BatchSpanProcessor(jaeger_otlp_exporter))
```

### Bước 1: Khởi chạy Jaeger bằng Docker

```bash
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest
```

| Port | Mục đích |
|------|----------|
| `16686` | Jaeger UI — mở trình duyệt tại http://localhost:16686 |
| `4317` | OTLP gRPC receiver — nơi app đẩy trace vào |
| `4318` | OTLP HTTP receiver (backup) |

### Bước 2: Chạy server & gửi request

```bash
python3 oltp.py
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Thời tiết Hà Nội thế nào?"}'
```

### Bước 3: Xem trace trên Jaeger UI

Mở http://localhost:16686 → chọn Service **`ai-agent-service`** → **Find Traces** → click vào trace để xem Waterfall View với đầy đủ spans và attributes.

---

## 5. Giải thích output OpenTelemetry

Khi gửi request `POST /chat`, OpenTelemetry tạo ra **một Trace** (cùng `trace_id`) gồm **6 Spans** phân cấp theo mô hình parent-child:

### Span Tree

```
[Root] POST /chat (SpanKind.SERVER)        ← parent_id: null (gốc, auto-instrumented)
  ├── http receive   (INTERNAL)            ← FastAPI nhận request body
  ├── tool.execute   (INTERNAL)            ← Gọi weather tool     (~102ms)
  ├── llm.generate   (INTERNAL)            ← Gọi LLM              (~305ms)
  ├── http send      (INTERNAL)            ← Gửi response header
  └── http send      (INTERNAL)            ← Gửi response body
```

### Timeline Waterfall

```
0ms        100ms      200ms      300ms      400ms
|----------|----------|----------|----------|-->
[=============== POST /chat (~411ms) ===============]
[recv]
 [== tool.execute (102ms) ==]
                             [=== llm.generate (305ms) ===]
                                                      [send][send]
```

### Chi tiết từng Span

#### a. Root Span — `POST /chat` (SERVER)

Được **FastAPIInstrumentor tự động tạo** cho mỗi HTTP request đi vào. Không cần viết code.

| Field | Giá trị | Ý nghĩa |
|-------|---------|----------|
| `parent_id` | `null` | Đây là root span, không có cha |
| `http.method` | `POST` | HTTP method |
| `http.route` | `/chat` | Route matched |
| `http.status_code` | `200` | Request thành công |
| `user.query` | `"Thời tiết Hà Nội..."` | Custom attribute gắn bằng `set_attribute()` |
| Duration | **~411ms** | Tổng thời gian xử lý request |

#### b. `tool.execute` — Gọi Weather Tool

Child span tạo thủ công bằng `tracer.start_as_current_span("tool.execute")`.

| Attribute | Giá trị |
|-----------|---------|
| `tool.name` | `get_weather` |
| `tool.args.location` | `Hanoi` |
| `tool.result` | `{'temperature': '28C', 'condition': 'Sunny'}` |
| Duration | **~102ms** |

#### c. `llm.generate` — Gọi LLM

Child span cho bước gọi model, sử dụng **GenAI Semantic Conventions**.

| Attribute | Giá trị |
|-----------|---------|
| `gen_ai.system` | `anthropic` |
| `gen_ai.request.model` | `claude-3-5-sonnet` |
| `gen_ai.request.temperature` | `0.7` |
| `gen_ai.usage.input_tokens` | `150` |
| `gen_ai.usage.output_tokens` | `45` |
| `gen_ai.usage.total_tokens` | `195` |
| `status_code` | **OK** |
| Duration | **~305ms** |

#### d. `http receive` / `http send` (Auto)

Các span được FastAPI Instrumentor tự động tạo:
- **`http receive`** — ghi nhận thời điểm nhận body từ client
- **`http send` x2** — tách thành 2 span: gửi response header (status 200) và gửi response body

### Phân tích Bottleneck

| Span | Thời gian | % tổng |
|------|-----------|--------|
| `tool.execute` | 102ms | ~25% |
| `llm.generate` | 305ms | **~74%** |
| Overhead (routing, serialization) | ~4ms | ~1% |

> **Kết luận**: `llm.generate` chiếm **74% tổng thời gian** — đây là bottleneck chính.
> Trong production với LLM thật, con số này sẽ còn lớn hơn rất nhiều.
> Trace waterfall giúp nhìn ra điều này ngay lập tức mà không cần đoán.
