"""
Mock LLM — dùng chung cho tất cả ví dụ.
Không cần API key thật. Trả lời giả lập để focus vào deployment concept.
"""
import time
import random


MOCK_RESPONSES = {
    "default": [
        "Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.",
        "Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.",
        "Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.",
    ],
    "docker": ["Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"],
    "deploy": ["Deployment là quá trình đưa code từ máy bạn lên server để người khác dùng được."],
    "health": ["Agent đang hoạt động bình thường. All systems operational."],
    # Lab 11: Banking responses
    "transfer": ["Tôi có thể giúp bạn chuyển tiền. Vui lòng cung cấp số tài khoản người nhận và số tiền."],
    "balance": ["Số dư tài khoản của bạn hiện tại là... Bạn có muốn xem chi tiết không?"],
    "loan": ["Chúng tôi cung cấp nhiều loại vay. Bạn có thể cho biết mục đích vay và số tiền mong muốn?"],
    "account": ["Tôi có thể giúp bạn với các vấn đề về tài khoản. Bạn cần hỗ trợ gì?"],
}


def ask(question: str, delay: float = 0.1) -> str:
    """
    Mock LLM call với delay giả lập latency thật.
    """
    time.sleep(delay + random.uniform(0, 0.05))  # simulate API latency

    question_lower = question.lower()
    for keyword, responses in MOCK_RESPONSES.items():
        if keyword in question_lower:
            return random.choice(responses)

    return random.choice(MOCK_RESPONSES["default"])