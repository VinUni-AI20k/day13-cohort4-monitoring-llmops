import time
import uvicorn
from fastapi import FastAPI, Request

# --- OPENTELEMETRY IMPORTS ---
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# ==============================================================================
# 1. CẤU HÌNH OPENTELEMETRY VÀ KẾT NỐI JAEGER
# ==============================================================================
# Định nghĩa thông tin dịch vụ hiển thị trên giao diện Jaeger UI
resource = Resource.create({
    "service.name": "ai-agent-service",
    "service.version": "1.0.0",
    "deployment.environment": "development"
})

provider = TracerProvider(resource=resource)

# 1.1 Exporter đẩy trace sang Jaeger thông qua cổng OTLP gRPC (localhost:4317)
jaeger_otlp_exporter = OTLPSpanExporter(
    endpoint="localhost:4317",
    insecure=True  # Kết nối gRPC không dùng TLS ở môi trường dev
)
provider.add_span_processor(BatchSpanProcessor(jaeger_otlp_exporter))

# 1.2 Exporter in ra console để kiểm tra song song (tùy chọn)
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

# Thiết lập TracerProvider toàn cục
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("ai.agent.tracer")

# ==============================================================================
# 2. KHỞI TẠO FASTAPI & AUTO-INSTRUMENTATION
# ==============================================================================
app = FastAPI(title="AI Agent Observability with Jaeger")
FastAPIInstrumentor.instrument_app(app)

# ==============================================================================
# 3. MÔ PHỎNG LOGIC AGENT (LLM CALL & TOOL CALL)
# ==============================================================================
def execute_weather_tool(location: str):
    with tracer.start_as_current_span("tool.execute") as span:
        span.set_attribute("tool.name", "get_weather")
        span.set_attribute("tool.args.location", location)
        time.sleep(0.1)  # Giả lập thời gian gọi API
        result = {"location": location, "temperature": "28C", "condition": "Sunny"}
        span.set_attribute("tool.result", str(result))
        return result

def call_llm(prompt: str, model_name: str = "claude-3-5-sonnet"):
    with tracer.start_as_current_span("llm.generate") as span:
        # Chuẩn hóa theo GenAI Semantic Conventions
        span.set_attribute("gen_ai.system", "anthropic")
        span.set_attribute("gen_ai.request.model", model_name)
        span.set_attribute("gen_ai.request.temperature", 0.7)
        span.set_attribute("gen_ai.prompt", prompt)
        
        time.sleep(0.3)  # Giả lập thời gian LLM sinh câu trả lời
        
        response_text = "Thời tiết tại Hà Nội hôm nay rất đẹp, 28°C và có nắng."
        
        span.set_attribute("gen_ai.completion", response_text)
        span.set_attribute("gen_ai.usage.input_tokens", 150)
        span.set_attribute("gen_ai.usage.output_tokens", 45)
        span.set_attribute("gen_ai.usage.total_tokens", 195)
        span.set_status(Status(StatusCode.OK))
        return response_text

@app.post("/chat")
async def chat_agent(request: Request):
    data = await request.json()
    user_query = data.get("query", "Thời tiết Hà Nội thế nào?")
    
    current_span = trace.get_current_span()
    current_span.set_attribute("user.query", user_query)
    
    tool_data = execute_weather_tool(location="Hanoi")
    final_prompt = f"User query: {user_query}. Context: {tool_data}"
    response = call_llm(prompt=final_prompt)
    
    return {"status": "success", "response": response}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)