"""İki çalıştırmayı soru bazında eşleştirir (McNemar tam testi): python compare.py ddl dict"""
import json, sys
from math import comb
M = "gemini-3.5-flash-lite"
load = lambda c: {r["id"]: r for r in map(json.loads, open(f"results/{c}__{M}.jsonl", encoding="utf-8"))}
a, b = load(sys.argv[1]), load(sys.argv[2])
for key in ("ex", "ex_lenient"):
    only_a = sorted(i for i in a if a[i][key] and not b[i][key])
    only_b = sorted(i for i in a if b[i][key] and not a[i][key])
    n = len(only_a) + len(only_b)
    p = min(1.0, 2 * sum(comb(n, k) for k in range(min(len(only_a), len(only_b)) + 1)) / 2 ** n) if n else 1.0
    print(f"{key}: yalnız {sys.argv[1]} doğru {only_a} · yalnız {sys.argv[2]} doğru {only_b} · McNemar tam p={p:.2f}")
