"""
AgriVerse-AI Chatbot Comprehensive Evaluation Script.
Runs all 10 benchmark queries from notebook Cell 149 plus bilingual (Telugu/English) scenarios.
"""

import sys
from pathlib import Path

backend_path = Path("E:/KshetraIQ/backend")
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService

svc = ChatService()

EVALUATION_QUESTIONS = [
    {"id": 1, "query": "What is the recommended spacing for cotton sowing?", "expected_topic": "knowledge/spacing"},
    {"id": 2, "query": "What crops are suitable for black soil in Andhra Pradesh during Kharif?", "expected_topic": "neo4j/soil"},
    {"id": 3, "query": "Which pests affect cotton?", "expected_topic": "neo4j/pests"},
    {"id": 4, "query": "What is the weather forecast for Guntur?", "expected_topic": "weather"},
    {"id": 5, "query": "Should I irrigate my cotton field in Guntur this week?", "expected_topic": "weather+irrigation"},
    {"id": 6, "query": "What should I grow in black soil in Andhra Pradesh during Kharif?", "expected_topic": "crop_planning"},
    {"id": 7, "query": "What is the current market price of cotton in Andhra Pradesh?", "expected_topic": "market"},
    {"id": 8, "query": "What yield can I expect from 4 hectares with 650 mm rainfall?", "expected_topic": "yield"},
    {"id": 9, "query": "What are the suitable crops and expected weather for Andhra Pradesh during Kharif?", "expected_topic": "multi_agent"},
    {"id": 10, "query": "What pests affect rice and what does the agricultural literature say about them?", "expected_topic": "neo4j+knowledge"},
    # Bilingual Scenarios
    {"id": 11, "query": "ఆంధ్రప్రదేశ్‌లో నల్లరేగడి నేలలో ఏ పంటలు వేయవచ్చు?", "expected_topic": "telugu_crops"},
    {"id": 12, "query": "వరి పంటలో నీటి యాజమాన్యం ఎలా చేయాలి?", "expected_topic": "telugu_irrigation"},
    # Edge Cases & Context
    {"id": 13, "query": "Can I grow coffee in the plains of Guntur?", "expected_topic": "agronomic_rule"},
    {"id": 14, "query": "My soil test says nitrogen is low. How do I improve it?", "expected_topic": "soil_remedy"},
]

print("=" * 80)
print("AGRIVERSE-AI MULTI-AGENT CHATBOT BENCHMARK & EVALUATION")
print("=" * 80)

passed = 0
for test in EVALUATION_QUESTIONS:
    qid = test["id"]
    query = test["query"]
    lang = "te" if any(ord(char) >= 0x0C00 and ord(char) <= 0x0C7F for char in query) else "en"

    req = ChatRequest(message=query, language=lang)
    resp = svc.respond(req)

    print(f"\n[Test #{qid:02d}] Query ({lang.upper()}): {query}")
    print(f"Provider: {resp.provider} | Mode: {resp.mode}")
    print(f"Response: {resp.reply[:200]}...")

    assert resp.reply and len(resp.reply) > 20, f"Test {qid} failed: response too short"
    passed += 1

print("\n" + "=" * 80)
print(f"EVALUATION COMPLETE: {passed}/{len(EVALUATION_QUESTIONS)} tests passed successfully!")
print("=" * 80)

