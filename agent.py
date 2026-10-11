"""OULAD text-to-SQL agent: şema (+ veri sözlüğü) -> SQL üret -> salt okunur kapıdan geçir -> hata varsa yeniden dene."""
import hashlib, json, os, pathlib, re, sqlite3, time

ROOT = pathlib.Path(__file__).parent
DB_PATH = pathlib.Path(os.environ.get("OULAD_DB", ROOT / "data" / "oulad.db"))
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

# ponytail: 7 tablo ~3 bin token'a sığıyor, şema erişimi (retrieval) yok; 50+ tabloda gerekir.
RULES = "Return exactly one SQLite SELECT query. Output only the SQL, no explanation, no markdown."
RULES_CLARIFY = (RULES + " If, and only if, the question is genuinely ambiguous (reasonable readings would give different answers"
                 " and the data dictionary offers no sensible default), reply with exactly one line instead: CLARIFY: <one short question>.")


class QuotaExhausted(Exception):
    """Günlük ücretsiz kota bitti; önbellek sayesinde yarın kaldığı yerden devam edilir."""


def value_hints(con, max_distinct=20):
    """Düşük kardinaliteli TEXT kolonların gerçek yazımları (LLM çağrısı yok, tamamen deterministik)."""
    lines = []
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
        for _, c, typ, *_ in con.execute(f"PRAGMA table_info({t})").fetchall():
            if typ.upper() != "TEXT":
                continue
            vals = [r[0] for r in con.execute(f"SELECT DISTINCT {c} FROM {t} LIMIT {max_distinct + 1}")]
            if len(vals) <= max_distinct:
                shown = ", ".join(repr(v) for v in sorted(v for v in vals if v is not None))
                lines.append(f"{t}.{c}: {shown}" + (" (also NULL)" if None in vals else ""))
    return "\n".join(lines)


def schema_text(con, use_dict, values=False, clarify=False):
    ddl = "\n".join(r[0] + ";" for r in con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' ORDER BY name"))
    out = f"{RULES_CLARIFY if clarify else RULES}\n\nSCHEMA:\n{ddl}"
    if use_dict:
        d = json.load(open(ROOT / "dictionary.json", encoding="utf-8"))
        lines = []
        for t, v in d["tables"].items():
            lines.append(f"{t}: {v['desc']}")
            lines += [f"  - {c}: {x}" for c, x in v["columns"].items()]
        out += "\n\nDATA DICTIONARY:\n" + "\n".join(lines) + "\n\nJOINS:\n" + "\n".join(d["joins"])
    if values:
        out += "\n\nCATEGORICAL VALUES (exact spellings stored in the database):\n" + value_hints(con)
    return out


def extract_sql(text):
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip().rstrip(";").strip()


_OK = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}


def connect_ro(path=None):
    return sqlite3.connect(f"file:{path or DB_PATH}?mode=ro", uri=True)


def run_sql(con, sql, timeout=60, max_rows=1000):
    """Sorgu kapısı: yalnız SELECT/WITH, tek ifade, salt okunur bağlantı, authorizer, zaman aşımı, satır sınırı.
    Döner: (rows, None) ya da (None, hata_metni)."""
    if not re.match(r"\s*(select|with)\b", sql, re.I):
        return None, "blocked: only SELECT/WITH statements are allowed"
    con.set_authorizer(lambda action, *_: sqlite3.SQLITE_OK if action in _OK else sqlite3.SQLITE_DENY)
    t0 = time.time()
    con.set_progress_handler(lambda: time.time() - t0 > timeout, 10000)
    try:
        return con.execute(sql).fetchmany(max_rows), None
    except Exception as e:  # sqlite3.Error, ProgrammingError (çoklu ifade) vb.
        return None, f"{type(e).__name__}: {e}"
    finally:
        con.set_progress_handler(None, 0)
        con.set_authorizer(lambda *_: sqlite3.SQLITE_OK)  # ponytail: None Python 3.10'da her şeyi reddeder


_KW = {"on", "where", "group", "order", "left", "right", "inner", "outer", "cross", "join", "using", "limit",
       "having", "union", "select", "natural"}
_KEY = ("code_module", "code_presentation")


def table_columns(con):
    return {t.lower(): {c[1].lower() for c in con.execute(f"PRAGMA table_info({t})")}
            for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def lint_sql(sql, cols):
    """Anahtar bütünlüğü kontrolü: id_student eşitliğine giren bir takma adın tablosu code_module/code_presentation
    taşıyorsa, bu iki kolonda da bir eşitlik olmalı. Uyarı metni ya da None döner.
    ponytail: regex tabanlı; türetilmiş tablo (alt sorgu) içini görmez, USING(...) ve dolaylı eşitlikleri kaçırır."""
    s = re.sub(r"\s+", " ", sql)
    alias = {}
    for m in re.finditer(r"\b(?:from|join)\s+(\w+)(?:\s+(?:as\s+)?(\w+))?", s, re.I):
        t, a = m.group(1).lower(), m.group(2)
        if t in cols:
            alias.setdefault(t, t)
            if a and a.lower() not in _KW:
                alias[a.lower()] = t
    links, id_pairs = {}, []
    for m in re.finditer(r"(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)", s):
        x, cx, y, cy = (g.lower() for g in m.groups())
        if cx == cy:
            links.setdefault((x, cx), set()).add(y); links.setdefault((y, cx), set()).add(x)
            if cx == "id_student":
                id_pairs.append((x, y))
    for side in dict.fromkeys(a for p in id_pairs for a in p):
        if side in alias and set(_KEY) <= cols[alias[side]]:
            missing = [k for k in _KEY if not links.get((side, k))]
            if missing:
                return (f"LINT: '{side}' ({alias[side]}) is joined on id_student but not matched on {', '.join(missing)}. "
                        "A student id repeats across modules and presentations, so this join mixes or duplicates rows. "
                        "Also match code_module and code_presentation (studentAssessment has neither: link it through "
                        "assessments.id_assessment and use assessments.code_module/code_presentation). "
                        "If a cross-presentation join is truly intended, keep the query as is.")
    return None


def retry_prompt(question, sql, err):
    return f"Question: {question}\n\nYour previous SQL:\n{sql}\n\nProblem: {err}\n\nReturn the corrected SQL only."


def answer(con, question, llm, system, retries=0, lint_cols=None):
    text = llm(system, f"Question: {question}")
    if text.strip().upper().startswith("CLARIFY:"):
        return dict(sql=None, rows=None, error=None, attempts=1, clarify=text.strip()[8:].strip(), lint_hits=0)
    sql, hits = extract_sql(text), 0
    for attempt in range(1, retries + 2):
        rows, err = run_sql(con, sql)
        warn = lint_sql(sql, lint_cols) if lint_cols and err is None else None
        hits += bool(warn)
        problem = err or warn
        if problem is None or attempt > retries:
            return dict(sql=sql, rows=rows, error=err, attempts=attempt, clarify=None, lint_hits=hits)
        sql = extract_sql(llm(system, retry_prompt(question, sql, problem)))


def make_llm(model=MODEL, rpm=5, max_calls=None, cache_dir=ROOT / "cache"):
    """Gemini çağrısı: diske önbellek, dakika başı istek sınırı, 429'da geri çekilme."""
    from google import genai
    from google.genai import errors, types
    client = genai.Client()  # GEMINI_API_KEY ortam değişkenini okur
    cache_dir = pathlib.Path(cache_dir); cache_dir.mkdir(exist_ok=True)
    state = dict(calls=0, last=0.0)

    def llm(system, prompt):
        key = hashlib.sha256(json.dumps([model, system, prompt]).encode()).hexdigest()
        f = cache_dir / f"{key}.txt"
        if f.exists():
            return f.read_text(encoding="utf-8")
        if max_calls is not None and state["calls"] >= max_calls:
            raise QuotaExhausted(f"--max-calls={max_calls} doldu")
        for k in range(5):
            time.sleep(max(0, 60 / rpm - (time.time() - state["last"])))
            state["last"] = time.time()
            try:
                r = client.models.generate_content(model=model, contents=prompt,
                    config=types.GenerateContentConfig(system_instruction=system, temperature=0))
                state["calls"] += 1
                f.write_text(r.text or "", encoding="utf-8")
                return r.text or ""
            except errors.APIError as e:
                if e.code == 429 and re.search(r"per ?day|PerDay", str(e)):
                    raise QuotaExhausted("günlük kota bitti") from e
                if e.code not in (429, 500, 502, 503, 504):
                    raise
                time.sleep(15 * 2 ** k)  # dakikalık sınır ya da geçici sunucu hatası: bekle ve tekrar dene
        raise QuotaExhausted("API 5 denemede yanıt vermedi (429/5xx)")

    llm.state = state
    return llm
