#!/bin/bash
# Sırayla tüm yapılandırmaları çalıştırır; kota biterse durur, tekrar çalıştırınca önbellekten devam eder.
# Kullanım: GEMINI_API_KEY=... ./run_all.sh [rpm]
RPM=${1:-5}
set -e
for cfg in dict_values dict_values_lint full; do python evaluate.py --config $cfg --rpm $RPM; done            # geliştirme seti
for cfg in ddl dict dict_values dict_values_lint full; do python evaluate.py --config $cfg --set holdout --rpm $RPM; done  # hold-out (her biri bir kez)
python evaluate.py --config full --set ambiguous --rpm $RPM
