#!/bin/bash
# Türkçe soru setleri: yalnız iki uç yapılandırma (ddl ve full). Kod değişmeden çalıştırılır. Kullanım: ./run_all_tr.sh [rpm]
RPM=${1:-5}
set -e
for cfg in ddl full; do
  python evaluate.py --config $cfg --set holdout_tr --rpm $RPM
  python evaluate.py --config $cfg --set dev_tr --rpm $RPM
done
