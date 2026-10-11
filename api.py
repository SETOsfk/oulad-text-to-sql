"""OULAD text-to-SQL servisi (en iyi yapılandırma: sözlük + değer ipuçları + lint + 2 deneme + netleştirme).
Çalıştır: uvicorn api:app --port 8000   ·   Gerekli: GEMINI_API_KEY, OULAD_DB (varsayılan data/oulad.db)"""
import threading
from fastapi import FastAPI
from pydantic import BaseModel, Field
import agent

app = FastAPI(title="OULAD text-to-SQL", description="Doğal dil sorusu -> salt-okunur SQLite sorgusu -> sonuç")
_lock = threading.Lock()  # ponytail: tek kullanıcılı demo; llm hız sınırlayıcısı thread-safe değil. Çok kullanıcı için kuyruk gerekir.
_s = {}


def _state():
    if not _s:
        con = agent.connect_ro()
        _s.update(system=agent.schema_text(con, True, True, True), cols=agent.table_columns(con), llm=agent.make_llm(rpm=10))
    return _s


class Ask(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@app.get("/health")
def health():
    return {"ok": True, "model": agent.MODEL}


@app.post("/ask")
def ask(body: Ask):
    with _lock:
        s = _state()
        try:
            out = agent.answer(agent.connect_ro(), body.question, s["llm"], s["system"], retries=2, lint_cols=s["cols"])
        except agent.QuotaExhausted as e:
            return {"sql": None, "rows": None, "clarify": None, "error": f"Gemini kotası: {e}"}
    return {k: out[k] for k in ("sql", "rows", "clarify", "error", "attempts")}
