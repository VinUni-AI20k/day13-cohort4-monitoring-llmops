import asyncio
import logging
import uuid
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

# ==============================================================================
# SLIDE 1: Python structlog — Setup Chuẩn
# ==============================================================================
structlog.configure(
    processors=[
        # 1. Tự động hợp nhất các biến ngữ cảnh từ contextvars (correlation_id, user_id,...)
        structlog.contextvars.merge_contextvars,
        # 2. Thêm cấp độ log (level: info, error, warn,...)
        structlog.processors.add_log_level,
        # 3. Tự động chèn timestamp định dạng ISO 8601 theo chuẩn UTC
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # 4. Định dạng thông tin lỗi/exception nếu có
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # 5. Xuất toàn bộ dữ liệu log ra chuỗi JSON chuẩn
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    cache_logger_on_first_use=True,
)

# Khởi tạo logger toàn cục
logger = structlog.get_logger()


# ==============================================================================
# MÔ PHỎNG DỊCH VỤ / TÁC VỤ PHỤ (Sub-functions / Services)
# ==============================================================================
async def process_rag_query(query: str):
    """
    Hàm xử lý con. Nhờ contextvars, logger ở đây KHÔNG CẦN truyền lại 
    correlation_id hay user_id nhưng vẫn tự động xuất ra đầy đủ trong JSON.
    """
    logger.info("retrieving_documents", vector_db="pinecone", top_k=3)
    await asyncio.sleep(0.1)  # Giả lập truy vấn Vector DB
    
    logger.info("llm_call_started", model="claude-sonnet-4-5")
    await asyncio.sleep(0.2)  # Giả lập gọi LLM
    
    return "Đây là câu trả lời từ RAG Agent."


# ==============================================================================
# SLIDE 2: contextvars — Correlation ID & Context Tự Động
# ==============================================================================
class MockRequest:
    """Giả lập Request object từ API Gateway / FastAPI"""
    def __init__(self, user_id: str, feature: str, query: str):
        self.user_id = user_id
        self.feature = feature
        self.query = query


async def handle_request(request: MockRequest):
    # 1. Dọn dẹp ngữ cảnh cũ để tránh rò rỉ dữ liệu giữa các request
    clear_contextvars()

    # 2. Bắn/Gắn ngữ cảnh cố định cho request hiện tại
    bind_contextvars(
        correlation_id=str(uuid.uuid4())[:8],
        user_id=request.user_id,
        feature=request.feature,
    )

    # Từ đây trở đi, MỌI dòng log trong hàm này VÀ các hàm con (process_rag_query)
    # sẽ TỰ ĐỘNG chứa: correlation_id, user_id, feature.
    logger.info("request_received", query_len=len(request.query))

    start_time = asyncio.get_event_loop().time()
    
    # Gọi hàm xử lý logic AI Agent
    result = await process_rag_query(request.query)
    
    latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
    
    logger.info("response_sent", latency_ms=latency_ms, status="success")
    return result


# ==============================================================================
# CHẠY THỬ MÔ PHỎNG MULTI-REQUEST
# ==============================================================================
async def main():
    logger.info("agent_started", service="rag-agent", version="1.2.0")

    # Giả lập 2 request đến đồng thời
    req1 = MockRequest(user_id="u_7842", feature="summary", query="Tóm tắt tài liệu này")
    req2 = MockRequest(user_id="u_9999", feature="chat", query="Xin chào Agent")

    # Chạy bất đồng bộ đồng thời 2 requests
    await asyncio.gather(
        handle_request(req1),
        handle_request(req2),
    )

if __name__ == "__main__":
    asyncio.run(main())