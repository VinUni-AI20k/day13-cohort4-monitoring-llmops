# pip install presidio-analyzer presidio-anonymizer
import re
from typing import Dict, Any
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine


class PIIScrubber:
    """
    Bộ lọc PII kết hợp Hybrid:
    - Regex: Xử lý siêu nhanh các mẫu định dạng cố định (SĐT, Email, CCCD, Thẻ ngân hàng).
    - Presidio (NLP/NER): Nhận diện ngữ cảnh sâu cho Tên người, Địa chỉ, Email,...
    """

    # 1. Các mẫu Regex cho dữ liệu có cấu trúc cố định
    REGEX_PATTERNS: Dict[str, str] = {
        "email": r"[\w\.-]+@[\w\.-]+\.\w+",
        "phone_vn": r"(\+84|0)\d{9,10}",
        "cccd": r"\b\d{12}\b",
        "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    }

    def __init__(self, enable_presidio: bool = True):
        self.enable_presidio = enable_presidio
        if self.enable_presidio:
            # Khởi tạo Engine của Microsoft Presidio
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()

    def scrub_with_regex(self, text: str) -> str:
        """Phương pháp 1: Dùng Regex để che các mẫu cố định nhanh chóng"""
        for pattern_name, pattern_regex in self.REGEX_PATTERNS.items():
            replacement = f"[REDACTED_{pattern_name.upper()}]"
            text = re.sub(pattern_regex, replacement, text)
        return text

    def scrub_with_presidio(self, text: str, language: str = "en") -> str:
        """Phương pháp 2: Dùng Microsoft Presidio phân tích ngữ cảnh (NER)"""
        if not self.enable_presidio:
            return text

        # Bước 1: Phân tích ngữ cảnh để tìm các thực thể PII (Tên, Địa chỉ, Email,...)
        results = self.analyzer.analyze(text=text, language=language)

        # Bước 2: Thay thế/Ẩn danh các thực thể đã phát hiện
        anonymized_result = self.anonymizer.anonymize(
            text=text, analyzer_results=results
        )
        return anonymized_result.text

    def sanitize(self, text: str) -> str:
        """Quy trình Sanitization kết hợp (Hybrid Pipeline)"""
        if not text:
            return text

        # Bước 1: Lọc nhanh bằng Regex trước để giảm tải
        clean_text = self.scrub_with_regex(text)

        # Bước 2: Quét sâu bằng Presidio để bắt các thực thể ngữ cảnh (như tên người)
        if self.enable_presidio:
            clean_text = self.scrub_with_presidio(clean_text)

        return clean_text


# ==============================================================================
# DEMO CHẠY THỬ HỆ THỐNG
# ==============================================================================
if __name__ == "__main__":
    scrubber = PIIScrubber(enable_presidio=True)

    # Đoạn văn bản thô giả lập chứa PII của người dùng
    raw_user_input = (
        "Xin chào, tôi tên là John Doe, email của tôi là johndoe@example.com. "
        "Số điện thoại Việt Nam là 0912345678 và số CCCD là 001092001234. "
        "Thẻ tín dụng thanh toán: 4532-1111-2222-3333."
    )

    print("=== DỮ LIỆU BAN ĐẦU (RAW INPUT) ===")
    print(raw_user_input)
    print("\n" + "=" * 50 + "\n")

    # 1. Thử lọc bằng Regex thuần
    regex_only_output = scrubber.scrub_with_regex(raw_user_input)
    print("--- 1. KẾT QUẢ CHỈ DÙNG REGEX ---")
    print(regex_only_output)
    # Lưu ý: Regex che được Email, SĐT, CCCD, Thẻ nhưng BỎ SÓT tên "John Doe"

    print("\n" + "=" * 50 + "\n")

    # 2. Thử lọc bằng Pipeline Hybrid (Regex + Presidio)
    hybrid_output = scrubber.sanitize(raw_user_input)
    print("--- 2. KẾT QUẢ HYBRID (REGEX + PRESIDIO) ---")
    print(hybrid_output)
    # Kết quả: Bắt trọn vẹn cả tên người "John Doe" ([<PERSON>]) lẫn các dữ liệu định dạng