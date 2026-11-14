import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.config import get_settings
from app.services.storage import SQLiteStorage
from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest

import sqlite3

settings = get_settings()
storage = SQLiteStorage(settings.resolved_sqlite_db_path)
chat_svc = ChatService(settings=settings)

# Get a user who has assessments
conn = sqlite3.connect(settings.resolved_sqlite_db_path)
conn.row_factory = sqlite3.Row
cursor = conn.execute("SELECT user_id, assessment_id FROM assessments WHERE user_id IS NOT NULL LIMIT 5")
rows = cursor.fetchall()
user_id = rows[0]["user_id"]
assessment_id = rows[0]["assessment_id"]

user_assessments = storage.list_all(user_id=user_id)
target_assessment = storage.get(assessment_id, user_id=user_id)

print(f"Testing Chatbot with user_id: {user_id}, assessments count: {len(user_assessments)}")

test_queries = [
    ("Soil Health Score (EN)", "What is my soil health score and how can I improve it?", None),
    ("Soil Health Score (TE)", "నా నేల ఆరోగ్యం స్కోరు ఎంత? దానిని ఎలా మెరుగుపరచాలి?", None),
    ("Assessment Counts", "How many assessments have I completed so far?", None),
    ("Model Registry Health", "Which AI models are currently verified and running?", None),
    ("Market Turmeric Nizamabad", "What is the price of Turmeric in Nizamabad?", None),
    ("Market Turmeric Telugu", "నిజామాబాద్‌లో పసుపు ధర ఎంత?", None),
    ("Irrigation Water Req", "How much water does rice need on 2.5 acres?", None),
    ("Screen Awareness", "What is on my screen right now?", {
        "screen_title": "Soil Health Diagnostics",
        "active_view": "soil",
        "displayed_data": {
            "screen_title": "Soil Health Diagnostics",
            "nitrogen": "350",
            "phosphorus": "18",
            "potassium": "200",
            "ph": "6.8",
            "soil_health_score": 100.0,
            "soil_health_category": "Excellent",
        }
    }),
]

passed = 0
for name, query, screen_ctx in test_queries:
    print(f"\n--- Running Test: {name} ---")
    print(f"Query: {query}")
    lang = "te" if "(TE)" in name or "Telugu" in name else "en"
    req = ChatRequest(message=query, screen_context=screen_ctx, language=lang)
    resp = chat_svc.respond(
        request=req,
        user_id=user_id,
        assessment=target_assessment,
        past_assessments=user_assessments
    )
    answer = resp.reply or resp.answer or ""
    print(f"Response:\n{answer[:250]}...\n")
    assert len(answer) > 20, f"Response too short for {name}"
    passed += 1

print(f"\n==========================================")
print(f"ALL {passed}/{len(test_queries)} CHATBOT TESTS PASSED SUCCESSFULLY!")
print(f"==========================================")

