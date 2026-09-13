"""End-to-end flow verification against a running backend.

Usage: python -m scripts.e2e_check
"""
import io
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

BASE = "http://localhost:8000"
OK = []
FAIL = []


def step(name, cond, extra=""):
    (OK if cond else FAIL).append(name)
    print(("  ✔ " if cond else "  ✘ ") + name + (f"  {extra}" if extra else ""))


print("== Gyan Sathi E2E check ==")

# ---- signup via OTP (dev fallback 000000)
r = requests.post(f"{BASE}/api/auth/send-otp", json={"email": f"e2e{Path(__file__).stat().st_ino}@test.in"})
step("send-otp", r.status_code == 200)
email_payload = {"email": r.json().get("email", "e2e@test.in")} if False else None

r = requests.post(f"{BASE}/api/auth/verify-otp", json={"email": "e2e-flow@test.in", "otp": "000000"})
step("verify-otp → jwt", r.status_code == 200 and "access_token" in r.json())
tok = r.json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

# ---- onboarding
r = requests.post(f"{BASE}/api/auth/onboarding", headers=H,
                  json={"full_name": "E2E વિદ્યાર્થી", "standard": 10,
                        "medium": "gujarati", "preferred_language": "gu"})
step("onboarding", r.status_code == 200 and r.json()["user"]["onboarded"])

# ---- subjects from DB
r = requests.get(f"{BASE}/api/subjects?standard=10", headers=H)
step("subjects (DB-driven)", r.status_code == 200 and len(r.json()["subjects"]) >= 6)
subjects = r.json()["subjects"]
science = next((s for s in subjects if s["name_en"] == "Science"), subjects[0])

r = requests.get(f"{BASE}/api/subjects/{science['id']}/chapters", headers=H)
step("chapters", r.status_code == 200 and len(r.json()["chapters"]) > 0)
light = next((c for c in r.json()["chapters"] if "પ્રકાશ" in c["name_gu"]), r.json()["chapters"][0])

# ---- RAG chat (Gujarati)
r = requests.post(f"{BASE}/api/chat", headers=H, json={
    "message": "પ્રકાશનું પરાવર્તન સમજાવો.", "mode": "ask",
    "subject_id": science["id"], "chapter_id": light["id"],
})
step("chat answer", r.status_code == 200, f"({len(r.json().get('answer',''))} chars)")
data = r.json()
print("     AI:", data.get("answer", "")[:120].replace("\n", " "))
print("     sources:", len(data.get("sources", [])), "| used_rag:", data.get("used_rag"))
conv_id = data["conversation_id"]

# ---- chat history
r = requests.get(f"{BASE}/api/chats", headers=H)
step("chat list", r.status_code == 200 and any(c["id"] == conv_id for c in r.json()["chats"]))
r = requests.get(f"{BASE}/api/chats/{conv_id}", headers=H)
step("chat messages", r.status_code == 200 and len(r.json()["messages"]) == 2)
msg_id = r.json()["messages"][-1]["id"]

# ---- feedback
r = requests.post(f"{BASE}/api/feedback", headers=H,
                  json={"message_id": msg_id, "rating": "up"})
step("feedback", r.status_code == 200)

# ---- upload limits (allowance reflects plan: 10 free / 500 premium)
r = requests.get(f"{BASE}/api/uploads", headers=H)
allowance0 = r.json()["allowance"]
expected_limit = 500 if allowance0["is_premium"] else 10
step("uploads list + allowance (plan-aware)",
     r.status_code == 200 and allowance0["limit"] == expected_limit,
     f"(used {allowance0['used']}/{allowance0['limit']}, premium={allowance0['is_premium']})")

# upload a real txt file
file_bytes = "GSEB sample question paper: પ્રકાશના પરાવર્તન વિશે ટૂંકનોંધ આપો. (10 marks)".encode("utf-8")
r = requests.post(f"{BASE}/api/uploads", headers=H,
                  files={"file": ("notes.txt", io.BytesIO(file_bytes), "text/plain")})
step("upload counts server-side",
     r.status_code == 200 and r.json()["allowance"]["used"] == allowance0["used"] + 1,
     f"(now {r.json()['allowance']['used']}/{r.json()['allowance']['limit']})")

# ---- quiz generation (real AI)
r = requests.post(f"{BASE}/api/quiz/generate", headers=H, json={
    "standard": 10, "subject_id": science["id"], "chapter_id": light["id"], "count": 3})
step("quiz generate", r.status_code == 200 and len(r.json()["questions"]) == 3)
qs = r.json()["questions"]
print("     Q1:", qs[0]["question"][:90])
r = requests.post(f"{BASE}/api/quiz/attempt/submit", headers=H, json={
    "answers": [{"question_id": qs[i].get("id"),
                 "question_index": i,
                 "selected": qs[i]["answer"],
                 "subject_id": science["id"], "chapter_id": light["id"]} for i in range(3)]})
step("quiz submit 3/3", r.status_code == 200 and r.json()["correct"] == 3,
     f"(score {r.json().get('score_percent', 0)}%)" if r.status_code == 200 else f"({r.status_code})")

# ---- progress
r = requests.get(f"{BASE}/api/progress", headers=H)
step("progress", r.status_code == 200 and r.json()["questions_asked"] >= 1)

# ---- premium purchase (sandbox) — server verifies
r = requests.post(f"{BASE}/api/subscription/create", headers=H,
                  json={"plan_code": "premium"})
step("subscription create (sandbox order)", r.status_code == 200)
pay = r.json()
r = requests.post(f"{BASE}/api/subscription/verify", headers=H, json={
    "payment_id": pay["payment_id"], "gateway_order_id": pay["order_id"],
    "gateway_payment_id": "sandbox_test_123", "gateway_signature": "sandbox"})
step("premium activated", r.status_code == 200 and r.json()["subscription"]["plan"]["code"] == "premium")

r = requests.get(f"{BASE}/api/subscription/status", headers=H)
step("premium status", r.json()["is_premium"] is True)
r = requests.get(f"{BASE}/api/uploads", headers=H)
step("premium upload limit raised", r.json()["allowance"]["limit"] == 500)

# ---- admin blocked for student
r = requests.get(f"{BASE}/api/admin/dashboard", headers=H)
step("student blocked from admin (403)", r.status_code == 403)

# ---- admin login + dashboard
r = requests.post(f"{BASE}/api/auth/login",
                  json={"email": "admin@gyansathi.in", "password": "Admin@123"})
step("admin login", r.status_code == 200)
admin_h = {"Authorization": f"Bearer {r.json()['access_token']}"}
r = requests.get(f"{BASE}/api/admin/dashboard", headers=admin_h)
step("admin dashboard", r.status_code == 200 and r.json()["total_students"] >= 1)

print(f"\n== {len(OK)} passed, {len(FAIL)} failed ==")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
