"""60 soruluk testi çalıştırır: python evaluate.py --config dict_retry [--limit N] [--rpm 5] [--max-calls 100]"""
import argparse, collections, itertools, json, re, sys, time
import agent

CONFIGS = {  # ad: kullanılan mekanizmalar
    "ddl": dict(use_dict=False, retries=0),
    "dict": dict(use_dict=True, retries=0),
    "dict_retry": dict(use_dict=True, retries=2),
    "dict_values": dict(use_dict=True, values=True, retries=0),
    "dict_values_lint": dict(use_dict=True, values=True, lint=True, retries=2),
    "full": dict(use_dict=True, values=True, lint=True, retries=2, clarify=True),
}
SETS = {"dev": "questions.jsonl", "holdout": "questions_holdout.jsonl", "ambiguous": "questions_ambiguous.jsonl",
        "dev_tr": "questions_tr.jsonl", "holdout_tr": "questions_holdout_tr.jsonl"}  # Türkçe çeviriler; gold SQL aynı


def norm(rows, ordered):
    v = lambda x: round(x, 1) if isinstance(x, float) else x
    t = [tuple(v(x) for x in r) for r in rows]
    return t if ordered else sorted(t, key=lambda r: tuple(str(float(x)) if isinstance(x, (int, float)) else str(x) for x in r))


def match(pred, gold, ordered):
    return norm(pred, ordered) == norm(gold, ordered)


def match_lenient(pred, gold, ordered):
    """Ek kolonları tolere eder: gold kolonları, pred kolonlarının bir alt dizisiyle (herhangi sırada) eşleşiyorsa doğru.
    Not: sonuçlar görüldükten sonra eklendi (post-hoc); katı metrik `match` ile birlikte raporlanır."""
    if match(pred, gold, ordered):
        return True
    if not pred or not gold or len(pred[0]) <= len(gold[0]):
        return False
    return any(match([tuple(r[i] for i in idx) for r in pred], gold, ordered)
               for idx in itertools.permutations(range(len(pred[0])), len(gold[0])))


def summarize(res, title):
    n = len(res)
    pct = lambda k, rs: f"{100 * sum(1 for r in rs if r[k]) / len(rs):.1f}%" if rs else "-"
    lines = [f"## {title}", "", f"- Soru: {n}", f"- Execution accuracy (katı): {pct('ex', res)}", f"- Execution accuracy (ek kolon toleranslı, post-hoc): {pct('ex_lenient', res)}",
             f"- Çalışan sorgu oranı: {pct('ok', res)}", f"- Uydurma tablo/kolon oranı: {pct('halluc', res)}",
             f"- Ortalama deneme: {sum(r['attempts'] for r in res) / n:.2f}",
             f"- Lint uyarısı alan soru: {sum(1 for r in res if r.get('lint_hits'))}",
             f"- Gereksiz netleştirme sorusu: {sum(1 for r in res if r.get('asked'))}/{n}", "",
             "| Kırılım | n | EX |", "|---|---|---|"]
    for key, label in (("difficulty", "zorluk"), ("n_joins", "join sayısı"), ("tag", "etiket")):
        groups = collections.defaultdict(list)
        for r in res:
            for g in (r["tags"] if key == "tag" else [r[key]]):
                groups[g].append(r)
        for g, rs in sorted(groups.items(), key=lambda x: str(x[0])):
            if key != "tag" or len(rs) >= 3:
                lines.append(f"| {label}: {g} | {len(rs)} | {pct('ex', rs)} |")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", choices=CONFIGS, required=True)
    p.add_argument("--set", choices=SETS, default="dev")
    p.add_argument("--model", default=agent.MODEL)
    p.add_argument("--rpm", type=float, default=5)
    p.add_argument("--max-calls", type=int)
    p.add_argument("--limit", type=int)
    a = p.parse_args()
    c = CONFIGS[a.config]
    if a.set == "ambiguous":
        assert c.get("clarify"), "belirsiz set yalnız netleştirme açık yapılandırmayla (--config full) anlamlı"
    qs = [json.loads(l) for l in open(agent.ROOT / SETS[a.set], encoding="utf-8")][: a.limit]
    con = agent.connect_ro()
    system = agent.schema_text(con, c.get("use_dict", False), c.get("values", False), c.get("clarify", False))
    cols = agent.table_columns(con) if c.get("lint") else None
    llm = agent.make_llm(a.model, a.rpm, a.max_calls)
    res = []
    try:
        for q in qs:
            out = agent.answer(con, q["question"], llm, system, c.get("retries", 0), cols)
            asked = out["clarify"] is not None
            if a.set == "ambiguous":
                res.append(dict(id=q["id"], question=q["question"], why_ambiguous=q["why_ambiguous"], asked=asked,
                                clarify=out["clarify"], pred_sql=out["sql"]))
                print(q["id"], "SORDU" if asked else "SQL   ", q["question"][:50], "->", (out["clarify"] or out["sql"] or "")[:70], flush=True)
                continue
            gold, gerr = agent.run_sql(con, q["gold_sql"], timeout=300)
            assert gerr is None, (q["id"], gerr)
            ok = out["error"] is None and not asked
            res.append(dict(id=q["id"], difficulty=q["difficulty"], n_joins=q["n_joins"], tags=q["tags"],
                            question=q["question"], gold_sql=q["gold_sql"], pred_sql=out["sql"], error=out["error"],
                            attempts=out["attempts"], ok=ok, asked=asked, clarify=out["clarify"], lint_hits=out["lint_hits"],
                            ex=ok and match(out["rows"], gold, q["order_matters"]),
                            ex_lenient=ok and match_lenient(out["rows"], gold, q["order_matters"]),
                            halluc=bool(out["error"] and re.search(r"no such (table|column)", out["error"]))))
            print(q["id"], "OK " if res[-1]["ex"] else "ASK" if asked else "ERR" if not ok else "BAD", q["question"][:60], flush=True)
    except agent.QuotaExhausted as e:
        print(f"\nDURDU: {e}. {len(res)}/{len(qs)} soru bitti; aynı komutu tekrar çalıştır, önbellekten devam eder.")
    if not res:
        return
    name = a.config if a.set == "dev" else f"{a.set}_{a.config}"
    (agent.ROOT / "results").mkdir(exist_ok=True)
    (agent.ROOT / "results" / f"{name}__{a.model}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in res), encoding="utf-8")
    if a.set == "ambiguous":
        n_ask = sum(r["asked"] for r in res)
        md = f"## ambiguous · {a.config} · {a.model}\n\n- Netleştirme sorusu soran: {n_ask}/{len(res)}\n" + "\n".join(
            f"- {r['id']}: {'SORDU: ' + r['clarify'] if r['asked'] else 'SQL üretti'} ({r['question']})" for r in res)
    else:
        md = summarize(res, f"{a.set} · {a.config} · {a.model}")
    (agent.ROOT / "results" / f"{name}__{a.model}.md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
