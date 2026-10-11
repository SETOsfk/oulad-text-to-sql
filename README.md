# OULAD Text-to-SQL

Açık Üniversite öğrenci verisi (OULAD, CC BY 4.0; 7 tablo, 10,6 milyon satır) üzerinde doğal dil sorusunu SQLite sorgusuna çeviren Gemini tabanlı ajan. Amaç, çalışan bir demo değil, **neyin işe yaradığının ölçülmesi**: her mekanizma aynı sorularla, aynı modelle ve önceden yazılmış tahminlerle test edildi.

## Nasıl çalışır
Şema + Türkçe veri sözlüğü + düşük çeşitlilikli kolonların değer listesi → LLM → SQL → **salt-okunur kapı** (yalnız SELECT/WITH, SQLite authorizer, 60 sn zaman aşımı, 1000 satır sınırı) → hata ya da lint uyarısında en çok 2 yeniden deneme. Gerçekten belirsiz soruda model `CLARIFY:` ile soru sorar.

## Ölçüm
60 geliştirme + 20 dondurulmuş hold-out (SHA256 `docs/dondurma_sha256.txt`) + 10 belirsiz soru. Gold SQL'ler elle yazıldı ve doğrulandı. Model: `gemini-3.5-flash-lite` (ücretsiz katman), sıcaklık 0, tek koşu. Metrik: sonuç kümesi eşleşmesi (execution accuracy, katı).

| Yapılandırma | Dev (60) | Hold-out (20) |
|---|---|---|
| yalnız DDL şeması | 93,3 | 80,0 |
| + veri sözlüğü | 93,3 | 95,0 |
| + değer ipuçları | 91,7 | 90,0 |
| + anahtar-bütünlüğü lint'i + yeniden deneme | 93,3 | 95,0 |
| + netleştirme (full) | 95,0 | 95,0 |

Türkçe sorular (aynı gold SQL): full dev 93,3 / hold-out 95,0; ddl dev 88,3 / hold-out 90,0.

## Bulgular (dürüst okuma)
- Hiçbir fark istatistiksel olarak anlamlı değil (McNemar tam test; ör. hold-out ddl–full p=0,25). Küçük kümeler.
- Hold-out'ta kazancı **veri sözlüğü** getirdi (özellikle tuzaklar: `imd_band` değerleri, Withdrawn ≠ boş `date_unregistration`, anahtar çiftleri).
- Değer ipuçları ölçülebilir ek fayda vermedi.
- Lint: 80 gold sorguda 0 yanlış alarm; hold-out'ta 1 hatayı yakaladı. Dar kapsam (türetilmiş alt sorgu, `USING`, mantık hataları kaçar).
- Yeniden deneme tek başına işe yaramadı (0/60 çalışma hatası); yalnız lint ile birlikte anlamlı.
- Netleştirme: 10 belirsiz sorunun 4'ünde soru sordu (önceden yazdığım "çoğunda" tahmini tutmadı), 80 net soruda 0 gereksiz soru.
- Uydurma tablo/kolon oranı tüm koşularda %0; salt-okunur kapı yazma girişimlerini engeller (test var).
- Türkçe: ölçülebilir kayıp yok (en büyük etki yalnız-DDD durumunda, anlamlı değil).

## Sınırlar
Tek model, tek koşu, küçük kümeler. h09'un gold'u tartışmalı (dondurulduğu için değiştirilmedi). q60 belirsizliği sonradan düzeltildi ve açıklandı. Tüm kararlar, tahminler ve hatalar: `docs/karar_gunlugu.md`.

## Kurulum
```
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python build_db.py                      # data/archive içindeki OULAD CSV'lerinden SQLite üretir
export GEMINI_API_KEY=...               # ücretsiz katman: yalnız herkese açık veri gönder
./run_all.sh                            # tüm değerlendirmeler (önbellekli, kaldığı yerden devam eder)
pytest tests                            # testler
```
### API
```
uvicorn api:app --port 8000
curl -X POST localhost:8000/ask -H 'content-type: application/json' -d '{"question":"Kaç farklı öğrenci var?"}'
```
### Docker
```
docker build -t oulad-sql .
docker run -p 8000:8000 -e GEMINI_API_KEY -v $PWD/data:/data oulad-sql   # /data/oulad.db gerekli
```
Veri: Kuzilek, Hlosta, Zdrahal, *Open University Learning Analytics Dataset*, Scientific Data 2017, CC BY 4.0.
