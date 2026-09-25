import time
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()

from langfuse import observe, get_client

app = FastAPI(title="AI Agent Observability with Langfuse")


# ==============================================================================
# 1. MÔ PHỎNG TOOL CALL VỚI DECORATOR @observe
# ==============================================================================
@observe(name="tool_execution")
def execute_weather_tool(location: str):
    """
    Decorator @observe sẽ tự động tạo một Span con (Observation)
    nằm bên trong Trace chính của request.
    """
    time.sleep(0.1)  # Giả lập thời gian gọi API thời tiết
    result = {"location": location, "temperature": "28C", "condition": "Sunny"}

    get_client().update_current_span(
        metadata={"tool_name": "get_weather", "input_location": location},
        output=result
    )
    return result


# ==============================================================================
# 2. MÔ PHỎNG LLM CALL VỚI DECORATOR @observe(as_type="generation")
# ==============================================================================
@observe(as_type="generation", name="llm_generation")
def call_llm(prompt: str, model_name: str = "claude-3-5-sonnet"):
    """
    Đánh dấu as_type="generation" giúp Langfuse nhận diện đây là lượt gọi LLM,
    từ đó tự động tính toán số lượng Token và Chi phí (Cost).
    """
    time.sleep(0.3)  # Giả lập thời gian LLM sinh câu trả lời
    response_text = "Thời tiết tại Hà Nội hôm nay rất đẹp, 28°C và có nắng."

    get_client().update_current_generation(
        model=model_name,
        input=prompt,
        output=response_text,
        usage_details={
            "input": 150,
            "output": 45,
            "total": 195
        },
        metadata={
            "temperature": 0.7,
            "provider": "anthropic"
        }
    )
    return response_text


# ==============================================================================
# 3. API ENDPOINT CHÍNH (ROOT TRACE)
# ==============================================================================
@observe(name="chat_agent_endpoint")
async def handle_chat_logic(user_query: str, user_id: str):
    """
    Hàm xử lý chính của Agent. @observe ở đây đóng vai trò tạo Root Trace.
    """
    # Bước 1: Gọi Tool (Tự động lồng vào Trace chính thành Child Span)
    tool_data = execute_weather_tool(location="Hanoi")

    # Bước 2: Gọi LLM (Tự động lồng vào Trace chính thành Generation Span)
    final_prompt = f"User query: {user_query}. Context: {tool_data}"
    response = call_llm(prompt=final_prompt)

    return response


@app.post("/chat")
async def chat_agent(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    user_query = data.get("query", "Thời tiết Hà Nội thế nào?")
    user_id = data.get("user_id", "u_7842")

    response = await handle_chat_logic(user_query=user_query, user_id=user_id)

    return {"status": "success", "response": response}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
