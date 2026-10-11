import json, os, pathlib, sqlite3, sys
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
import agent, evaluate


@pytest.fixture
def con(tmp_path):
    p = tmp_path / "t.db"
    c = sqlite3.connect(p)
    c.executescript("CREATE TABLE t (a INTEGER, b TEXT); INSERT INTO t VALUES (1,'x'),(2,'y');")
    c.commit(); c.close()
    return agent.connect_ro(p)


@pytest.mark.parametrize("sql", [
    "DROP TABLE t", "INSERT INTO t VALUES (3,'z')", "DELETE FROM t", "PRAGMA table_info(t)",
    "ATTACH DATABASE ':memory:' AS m", "SELECT 1; DROP TABLE t", "WITH x AS (SELECT 1) DELETE FROM t",
])
def test_gate_blocks_writes(con, sql):
    rows, err = agent.run_sql(con, sql)
    assert rows is None and err
    assert con.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 2  # veri değişmedi


def test_gate_allows_select(con):
    assert agent.run_sql(con, "SELECT a FROM t ORDER BY a") == ([(1,), (2,)], None)


def test_extract_sql():
    assert agent.extract_sql("```sql\nSELECT 1;\n```") == "SELECT 1"
    assert agent.extract_sql("SELECT 2;") == "SELECT 2"


def test_retry_feeds_error_back(con):
    seen = []
    replies = iter(["SELECT nope FROM t", "SELECT a FROM t"])
    def llm(system, prompt):
        seen.append(prompt); return next(replies)
    out = agent.answer(con, "q", llm, "sys", retries=2)
    assert out["attempts"] == 2 and out["error"] is None and out["rows"] == [(1,), (2,)]
    assert "no such column" in seen[1]


def test_no_retry_returns_error(con):
    out = agent.answer(con, "q", lambda s, p: "SELECT nope FROM t", "sys", retries=0)
    assert out["attempts"] == 1 and "no such column" in out["error"]


def test_match_rules():
    assert evaluate.match([(2,), (1,)], [(1,), (2,)], ordered=False)
    assert not evaluate.match([(2,), (1,)], [(1,), (2,)], ordered=True)
    assert evaluate.match([(75.8,)], [(75.7995729,)], ordered=True)   # 1 ondalık tolerans
    assert evaluate.match([(3,)], [(3.0,)], ordered=True)
    assert not evaluate.match([(1, "a")], [(1,)], ordered=True)       # fazladan kolon yanlış sayılır


def test_lenient_allows_extra_columns_only():
    assert evaluate.match_lenient([("a", 5), ("b", 3)], [("a",), ("b",)], ordered=True)       # ek kolon tolere
    assert evaluate.match_lenient([(5, "a"), (3, "b")], [("a",), ("b",)], ordered=True)       # sıra fark etmez
    assert not evaluate.match_lenient([("a", 5)], [("b",)], ordered=True)                      # yanlış değer hâlâ yanlış
    assert not evaluate.match_lenient([("a",)], [("a", 5)], ordered=True)                      # eksik kolon yanlış
    assert not evaluate.match_lenient([("b", 3), ("a", 5)], [("a",), ("b",)], ordered=True)   # sıra önemliyse sıra


def test_questions_file():
    qs = [json.loads(l) for l in open(agent.ROOT / "questions.jsonl", encoding="utf-8")]
    assert len(qs) == 60 and len({q["id"] for q in qs}) == 60
    assert all(q["gold_sql"].lstrip().upper().startswith(("SELECT", "WITH")) for q in qs)


@pytest.mark.skipif(not agent.DB_PATH.exists(), reason="oulad.db yok (python build_db.py)")
def test_gold_sql_runs_on_real_db():
    con = agent.connect_ro()
    q1 = json.loads(open(agent.ROOT / "questions.jsonl", encoding="utf-8").readline())
    assert agent.run_sql(con, q1["gold_sql"]) == ([(28785,)], None)
    assert "imd_band" in agent.schema_text(con, True) and "yüzde işaretsiz" in agent.schema_text(con, True)


def _cols():
    return {"studentinfo": {"code_module", "code_presentation", "id_student"}, "studentassessment": {"id_assessment", "id_student"},
            "assessments": {"id_assessment", "code_module", "code_presentation"}}


def test_lint_flags_partial_key_join():
    bad = "SELECT 1 FROM studentInfo t1 JOIN studentAssessment t2 ON t1.id_student = t2.id_student"
    assert "code_module" in agent.lint_sql(bad, _cols())


def test_lint_passes_complete_key_join():
    ok = ("SELECT 1 FROM studentAssessment sa JOIN assessments a ON a.id_assessment=sa.id_assessment "
          "JOIN studentInfo si ON si.id_student=sa.id_student AND si.code_module=a.code_module AND si.code_presentation=a.code_presentation")
    assert agent.lint_sql(ok, _cols()) is None
    assert agent.lint_sql("SELECT COUNT(*) FROM studentInfo", _cols()) is None


def test_lint_flags_derived_table_side():
    q = "SELECT 1 FROM studentInfo si JOIN (SELECT id_student, 1 x FROM v GROUP BY id_student) t ON si.id_student = t.id_student"
    assert agent.lint_sql(q, _cols())


def test_no_lint_cols_means_single_attempt(con):
    cols = {"t": {"a", "b"}}
    seen, replies = [], iter(["SELECT a FROM t", "SELECT a FROM t"])
    out = agent.answer(con, "q", lambda s, p: (seen.append(p), next(replies))[1], "sys", retries=1, lint_cols=cols)
    assert out["lint_hits"] == 0 and out["attempts"] == 1  # lint yoksa tek deneme


def test_clarify_short_circuits(con):
    out = agent.answer(con, "q", lambda s, p: "CLARIFY: Which module?", "sys")
    assert out["clarify"] == "Which module?" and out["sql"] is None


def test_gold_sql_never_flagged_by_lint():
    cols = {t: set(c) for t, c in {
        "studentinfo": {"code_module", "code_presentation", "id_student"},
        "studentregistration": {"code_module", "code_presentation", "id_student"},
        "studentvle": {"code_module", "code_presentation", "id_student", "id_site"},
        "studentassessment": {"id_assessment", "id_student"},
        "assessments": {"id_assessment", "code_module", "code_presentation"},
        "vle": {"id_site", "code_module", "code_presentation"}, "courses": {"code_module", "code_presentation"}}.items()}
    for f in ("questions.jsonl", "questions_holdout.jsonl"):
        for l in open(agent.ROOT / f, encoding="utf-8"):
            q = json.loads(l)
            assert agent.lint_sql(q["gold_sql"], cols) is None, q["id"]


def test_turkish_sets_mirror_english():
    for en, tr in (("questions.jsonl", "questions_tr.jsonl"), ("questions_holdout.jsonl", "questions_holdout_tr.jsonl")):
        E = [json.loads(l) for l in open(agent.ROOT / en, encoding="utf-8")]
        T = [json.loads(l) for l in open(agent.ROOT / tr, encoding="utf-8")]
        assert [q["id"] for q in E] == [q["id"] for q in T]
        assert all(e["gold_sql"] == t["gold_sql"] and e["question"] == t["question_en"] and e["question"] != t["question"] for e, t in zip(E, T))
