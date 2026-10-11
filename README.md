# OULAD Text-to-SQL

## Bu araç ne yapıyor
Senin dilinden SQL'e anlık çeviri yapıyor. Örneğin "Kaç farklı öğrenci var?" ya da "Her modülün başarı oranı nedir?" yazıyorsun. Araç soruyu Gemini'ye gönderiyor, Gemini bunu SQL'ın anlayacağı dile çeviriyor, araç bu çeviriyi veritabanında çalıştırıp sonucu veriyor.

Burada soruların sorulduğu veri: Open University'nin açık öğrenci verisi (OULAD). Öğrencilerin kayıtları, notları ve online derslerdeki tıklamaları var.

Soruları Türkçe ya da İngilizce sorabilirsin. Asıl amacım aracı yapmak değil, ona eklediğim her şeyin gerçekten işe yarayıp yaramadığını ölçmekti.

Veri: 7 tablo, 10,6 milyon satır (CC BY 4.0). Model: `gemini-3.5-flash-lite`, ücretsiz katman.

## Nasıl çalışıyor
1. Modele tablo şemasını, veri sözlüğünü (kolonların anlamını ve verideki tuzakları anlatan, elle yazdığım Türkçe not dosyası: `dictionary.json`) ve az değerli kolonların değerlerini veriyorum.
2. Model SQL yazıyor.
3. Sorgu önce bir güvenlik kapısından geçiyor: sadece SELECT, 60 saniye sınır, en fazla 1000 satır.
4. Sorgu hata verirse ya da anahtar kontrolüm (lint) bir şey bulursa model en fazla 2 kez tekrar deniyor.
5. Soru gerçekten belirsizse model cevap yerine soru soruyor.

## Test
60 geliştirme sorusu, 20 soruluk dondurulmuş hold-out (dosyanın hash'i `docs/dondurma_sha256.txt` içinde) ve 10 belirsiz soru. Cevap doğru sayılması için sorgunun sonucu, benim elle yazdığım doğru sorgunun sonucuyla aynı olmalı.

| Yapılandırma | Geliştirme (60) | Hold-out (20) |
|---|---|---|
| Sadece tablo şeması | %93,3 | %80 |
| + veri sözlüğü | %93,3 | %95 |
| + kolon değerleri | %91,7 | %90 |
| + lint ve tekrar deneme | %93,3 | %95 |
| hepsi + netleştirme soruları | %95,0 | %95 |

Soruları Türkçeye çevirince sonuç: hepsi açıkken %93,3 / %95, sadece şemayla %88,3 / %90.

## Ne çıktı
- **En çok işe yarayan veri sözlüğü oldu.** Verideki tuzakları (örneğin `imd_band` değerlerinde `%` yok, Withdrawn sayısı ile boş `date_unregistration` sayısı aynı değil) modele yazınca hold-out 16/20'den 19/20'ye çıktı.
- **Kolon değerlerini eklemek bir şey katmadı.**
- **Tek başına tekrar deneme işe yaramadı.** 60 sorunun hiçbirinde çalışma hatası yoktu, düzeltilecek bir şey çıkmadı. Sorgular çalışıyor ama bazen yanlış sonuç veriyor.
- **Lint:** 80 doğru sorguda hiç yanlış alarm vermedi, hold-out'ta bir hatayı yakaladı. Ama sadece belli bir hata türüne bakıyor.
- **Netleştirme:** 10 belirsiz sorunun 4'ünde soru sordu, 80 net soruda hiç sormadı. Bunu önceden "çoğunda soracak" diye tahmin etmiştim, yanılmışım.
- Modelin uydurduğu tablo ya da kolon: hiç yok. Yazma denemeleri güvenlik kapısında takılıyor (testi var).

## Dikkat
Hiçbir fark istatistiksel olarak anlamlı değil. Sorular az (20 ve 60), model tek, her yapılandırmayı bir kez çalıştırdım (McNemar p, 0,25 ile 1,00 arası). Yani "sözlük işe yarıyor" demek yerine "bu denemede işe yaramış gibi görünüyor" demek daha doğru.

Bilinen sorunlar: q60 sorusu belirsizdi, sonradan düzelttim, ilk sonucu `results/` içinde sakladım. h09'un doğru cevabı tartışmalı ama hold-out dondurulduğu için dokunmadım. Karar günlüğü: `docs/karar_gunlugu.md`.

## Çalıştırma
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python build_db.py          # data/archive içindeki OULAD CSV'lerinden veritabanı yapar
export GEMINI_API_KEY=...   # ücretsiz katmanda sadece açık veri gönder
./run_all.sh                # tüm testler
pytest tests
```

API:
```
uvicorn api:app --port 8000
curl -X POST localhost:8000/ask -H 'content-type: application/json' -d '{"question":"Kaç farklı öğrenci var?"}'
```

Docker (`data/oulad.db` gerekli):
```
docker build -t oulad-sql .
docker run -p 8000:8000 -e GEMINI_API_KEY -v $PWD/data:/data oulad-sql
```

Veri: Kuzilek, Hlosta, Zdrahal, *Open University Learning Analytics Dataset*, Scientific Data, 2017.
