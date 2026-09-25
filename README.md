# LLMOps Monitoring & Observability

Tài liệu và code demo các kỹ thuật Monitoring, Observability cho hệ thống AI Agent / LLM trong production.

## Cấu trúc dự án

```
.
├── trace.md                 # Lý thuyết về Trace, Span, Waterfall trong LLM Agent
├── structured-logs.py       # Structured Logging với structlog + contextvars
├── pii-scrubbing.py         # PII Scrubbing (Regex + Microsoft Presidio)
├── opentelemetry/           # OpenTelemetry Tracing + Jaeger visualization
│   ├── oltp.py
│   ├── requirements.txt
│   └── README.md
└── langfuse/                # Langfuse LLM Observability platform
    ├── langfuse-integration.py
    ├── requirements.txt
    ├── .env
    └── README.md
```

## Nội dung chính

### 1. Trace & Span (`trace.md`)

Giải thích khái niệm Trace, Span, Waterfall View trong ngữ cảnh AI Agent — cách một request đi qua các bước Guardrail → RAG → LLM → Tool Call → Answer và cách dùng trace để debug bottleneck, hallucination, cost.

### 2. Structured Logging (`structured-logs.py`)

Demo Python `structlog` với JSON output chuẩn:
- Cấu hình processors (log level, timestamp ISO 8601, exception formatting)
- `contextvars` để tự động gắn `correlation_id`, `user_id` xuyên suốt async call chain
- Mô phỏng multi-request đồng thời

```bash
pip install structlog
python3 structured-logs.py
```

### 3. PII Scrubbing (`pii-scrubbing.py`)

Hybrid pipeline lọc dữ liệu cá nhân (PII) trước khi log/trace:
- **Regex** — xử lý nhanh các mẫu cố định (SĐT, Email, CCCD, thẻ tín dụng)
- **Microsoft Presidio (NLP/NER)** — nhận diện ngữ cảnh sâu (tên người, địa chỉ)

```bash
pip install presidio-analyzer presidio-anonymizer
python3 -m spacy download en_core_web_lg
python3 pii-scrubbing.py
```

### 4. OpenTelemetry + Jaeger (`opentelemetry/`)

Distributed tracing với OpenTelemetry SDK, FastAPI auto-instrumentation, và Jaeger UI để visualize trace waterfall. Xem chi tiết tại [opentelemetry/README.md](opentelemetry/README.md).

### 5. Langfuse Integration (`langfuse/`)

LLM Observability với Langfuse — decorator-based tracing (`@observe`), tự động track token usage, cost, và hiển thị trace trên Langfuse Cloud UI. Xem chi tiết tại [langfuse/README.md](langfuse/README.md).
