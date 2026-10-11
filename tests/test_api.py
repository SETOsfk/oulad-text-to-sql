import api, agent
from fastapi.testclient import TestClient

def fake(system, prompt):
    return "CLARIFY: hangi sunum?" if "belirsiz" in prompt else ("DROP TABLE courses" if "yaz" in prompt else "SELECT COUNT(*) FROM courses")

def test_ask():
    con = agent.connect_ro()
    api._s.update(system="x", cols=agent.table_columns(con), llm=fake)
    c = TestClient(api.app)
    assert c.get("/health").json()["ok"]
    assert c.post("/ask", json={"question": "kaç ders var"}).json()["rows"] == [[22]]
    assert c.post("/ask", json={"question": "belirsiz soru"}).json()["clarify"]
    assert c.post("/ask", json={"question": "yaz sil"}).json()["error"]   # salt-okunur kapı
    assert c.post("/ask", json={"question": "a"}).status_code == 422
