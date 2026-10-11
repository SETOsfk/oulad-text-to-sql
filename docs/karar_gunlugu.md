# Karar günlüğü

## 2026-10-11 · Çalıştırma 1: `ddl` (yalnız şema), gemini-3.5-flash-lite, 60 soru
**Sonuç:** execution accuracy 55/60 = %91,7 · çalışan sorgu %100 · uydurma tablo/kolon %0 · ortalama deneme 1,00.
**Join sayısına göre:** 0 join %95,1 (n=41) · 1 join %92,9 (n=14) · 2 join %60,0 (n=5).

**5 hatanın sınıflandırması (hepsi sessiz yanlış: sorgu çalıştı, sonuç yanlış):**
| Soru | Hata | Sınıf |
|---|---|---|
| q11 | `activity_type='forum'` yazdı, veride değer `forumng` | Kategorik değeri tahmin etme |
| q29 | `imd_band='10-20%'` yazdı, veride `10-20` (yüzde işaretsiz) | Kategorik değeri tahmin etme (veri tutarsızlığı) |
| q39 | `studentInfo` ile `studentAssessment`'ı yalnız `id_student` üzerinden birleştirdi, ders/sunum anahtarları eksik | Bileşik anahtar (join çoğalması) |
| q41 | Aynı hata: öğrenci başka sunumda teslim etmişse "teslim etmiş" saydı | Bileşik anahtar |
| q60 | `assessment_type` bazında gruplayıp `id_assessment` yerine tür döndürdü | **Soru belirsizdi** (benim hatam, model değil) |

**Çıkarımlar**
- Yeniden deneme bu hatalara yardım etmez: hata mesajı yok, sorgu çalışıyor. Yeniden denemenin tavanı burada ~0 görünüyor; `dict_retry`'nin `dict`'ten farkını bu yüzden beklemiyorum.
- Taban modeli güçlü: 41 join'siz sorunun %95'i doğru. Benchmark'taki fark join sayısı 2'de ortaya çıkıyor (n=5, küçük örneklem; kesin konuşulamaz).

**Ön kayıt (sonuçları görmeden önce yazılan tahmin, `dict` için):** veri sözlüğü q11, q29 (değer bilgisi) ile q39, q41'i (JOINS bölümü) düzeltir; q60'a etkisi yok. Tahmin tutarsa veri sözlüğü etkisi mekanizmayla açıklanır, tutmazsa bu da raporlanır.

**q60 yeniden ifadelendirildi** (ilk çalıştırma sonrası, model çıktısına bakarak): "which assessment" → "which individual assessment (by id_assessment)". Gerekçe: gold ile soru uyuşmuyordu. Orijinal sonuç `results/ddl_v1_orijinal_q60.*` içinde saklı. Not: soruyu sonuçtan sonra değiştirmek küçük bir esneklik; raporda her iki sayı da yazılacak (55/60 orijinal, yeniden çalıştırma sonrası).

## 2026-10-11 · Çalıştırma 2–4: `ddl` (q60 düzeltilmiş), `dict`, `dict_retry` — gemini-3.5-flash-lite, 60 soru, temperature 0
| Yapılandırma | EX (katı) | EX (ek kolon toleranslı, post-hoc) | Çalışan sorgu | Uydurma tablo/kolon | Ort. deneme |
|---|---|---|---|---|---|
| ddl | 56/60 = %93,3 | 56/60 = %93,3 | %100 | %0 | 1,00 |
| dict | 56/60 = %93,3 | 58/60 = %96,7 | %100 | %0 | 1,00 |
| dict_retry | 56/60 = %93,3 | 58/60 = %96,7 | %100 | %0 | 1,00 |

(Orijinal q60 ifadesiyle `ddl`: 55/60 = %91,7.)

**Ön kayıt tahmini ve sonuç:** q11, q39, q41 tahmin edildiği gibi `dict` ile düzeldi. **q29 düzelmedi**: sözlük "yüzde işaretsiz" dese de model sorudaki "10-20%" ifadesini kopyaladı. Ayrıca `dict` yeni bir gerçek hata ekledi (q46: 2014J'de modülü atlayıp yalnız `id_student` ile birleştirdi; `ddl` bunu doğru yapmıştı).

**Metrik bulgusu (post-hoc):** `dict`'te q34 ve q43 yanlış görünüyordu ama sonuç doğruydu: model istenen sütuna ek bir sütun (oran/toplam) ekledi. Katı karşılaştırma bunu yanlış sayıyor. Sonuçları gördükten sonra "ek kolon toleranslı" ikinci bir metrik ekledim; **ikisi de raporlanır, katı olan ana sayıdır.** Tolerans kuralı: gold kolonları, tahmindeki kolonların bir alt kümesiyle (herhangi sırada) eşleşmeli; yanlış değer, eksik kolon, yanlış sıra hâlâ yanlış.

**Eşleştirilmiş karşılaştırma (McNemar tam test, soru bazında):**
- ddl vs dict, katı: yalnız ddl doğru {q34, q43, q46}, yalnız dict doğru {q11, q39, q41} → p = 1,00
- ddl vs dict, toleranslı: yalnız ddl {q46}, yalnız dict {q11, q39, q41} → p = 0,62
- dict vs dict_retry: fark yok.

**Sonuçlar**
1. Veri sözlüğü, tahmin edilen mekanizmayla 3 hatayı düzeltti (kategorik değer, bileşik anahtar), ama bir başkasını bozdu. Fark istatistiksel olarak ayırt edilemiyor (n=60, tek çalıştırma). "Sözlük iyileştirdi" **iddia edilmeyecek**.
2. **Yeniden deneme etkisiz: 0/60 sorgu hata verdi.** Kalan hataların hepsi "sessiz yanlış" (çalışan ama yanlış sorgu); yeniden deneme yalnız çalışmayan sorguyu yakalar. Yanlış sonucu yakalamak için başka bir mekanizma (sonuç doğrulama, netleştirme sorusu, çoklu aday + oylama) gerekir.
3. Taban model bu veride güçlü; kalan hata alanı küçük (4 soru). Test seti bu model için tavan etkisine yakın; yapılandırmalar arası farkı ölçmek için yeterince ayırt edici değil.
4. `dict_retry` ve `dict` çıktıları birebir aynı (aynı istemler, önbellek).

## 2026-10-11 · Hold-out ve belirsiz soru setleri donduruldu (mekanizmalar yazılmadan ÖNCE)
**Neden:** `lint`/değer ipuçları gibi mekanizmaları `questions.jsonl`'deki hatalara bakarak tasarlayacağım; bu 60 soru artık "geliştirme seti" ve onda ölçülen iyileşme iyimser olur. Gerçek ölçüm için daha önce görülmemiş **20 soruluk hold-out** (`questions_holdout.jsonl`, doğal ifadeli kategorik değerler + bileşik anahtar sorguları) ve **10 belirsiz soru** (`questions_ambiguous.jsonl`, netleştirme için) yazıldı. Gold SQL'ler veritabanında doğrulandı (sıfır sonuçlu h18 değiştirildi, yavaş h13 hızlandırıldı; bunlar model çalışmadan yapıldı).
**Kural:** Hold-out her yapılandırmada **bir kez** çalıştırılır; sonuçlara bakıp mekanizma değiştirilmez. Değiştirilirse ayrı bir hold-out gerekir. Dosya özetleri `docs/dondurma_sha256.txt` içinde.

**Ön kayıt tahminleri (dev seti hatalarına bakılarak, hold-out için):**
1. Değer ipuçları (kategorik değerlerin gerçek yazımı istemde) "değer" etiketli hold-out sorularını (h01–h04, h06, h07, h09) iyileştirir; `ddl`'de bunların en az biri yanlış çıkar.
2. Anahtar lint'i + yeniden deneme, "composite" etiketli (h10–h13, h15, h18, h19) sorularda hata yakalar; derived-table içine saklanan bileşik anahtar hatalarını (q46 türü) yakalayamaz.
3. Netleştirme: belirsiz 10 sorunun çoğunda soru sorar; net 80 soruda yanlış soru sorma oranı <%5.

## 2026-10-11 · Üç mekanizma eklendi (kod hazır, henüz modelle çalıştırılmadı)
1. **Değer ipuçları** (`value_hints`): ≤20 farklı değeri olan TEXT kolonların gerçek yazımları (ör. `imd_band: '10-20', '20-30%'`) isteme eklenir. LLM çağrısı yok, deterministik. Gerekçe: dev setinde en sık hata sınıfı "kategorik değeri tahmin etme" (q11, q29) ve `dict`'teki metin açıklaması q29'u düzeltmedi.
2. **Anahtar bütünlüğü kontrolü** (`lint_sql`): `id_student` üzerinden eşleşen bir takma adın tablosu `code_module`/`code_presentation` taşıyorsa, bu kolonlarda da eşitlik beklenir; yoksa uyarı, uyarı mevcut yeniden deneme döngüsüne hata gibi verilir. Yani yeniden deneme artık "çalışan ama yanlış" sorguları da yakalayabilir. **Bilinen sınır:** regex tabanlı; `USING(...)` ve dolaylı eşitlikleri kaçırır.
3. **Netleştirme** (`CLARIFY:`): model gerçekten belirsiz soruda SQL yerine tek satır soru döndürebilir. Ölçüt: 10 belirsiz soruda soru sorma oranı, 80 net soruda gereksiz soru oranı.

**Çevrimdışı kontrol (model çağrısı yok, dev seti, tasarımı bilen bir ölçüm):**
- Lint, 80 gold sorgunun **hiçbirini** işaretlemedi (yanlış alarm 0/80).
- Mevcut tahminlerde yalnız gerçekten yanlış olanları işaretledi: `ddl` → q39, q41; `dict` → q46 (3/3 isabet, 0 yanlış alarm). Bu, dev setine bakarak yazılmış bir kuralın dev setindeki sonucudur ve **kanıt sayılmaz**; asıl test hold-out.
- q46 türü (alt sorguya gizlenmiş eşleşme) yakalandı çünkü dış sorgudaki `studentInfo` tarafı eksikti; alt sorgunun içindeki hatayı görmez.

**Doğrulama:** 21 test geçti. "Kusursuz model" simülasyonu (gold SQL döndüren sahte LLM) hold-out'ta 20/20, belirsiz sette 10/10 soru, mevcut yapılandırmaların istemi birebir aynı kaldı (önbellek geçerli).

**Çalıştırma planı:** `./run_all.sh` — dev: dict_values, dict_values_lint, full · hold-out: ddl, dict, dict_values, dict_values_lint, full · belirsiz: full. Tahmini ~300 istek.

## 2026-10-11 · Geliştirme setinde ara sonuçlar: `dict_values` ve `dict_values_lint` (hold-out henüz çalışmadı)
| Yapılandırma | EX (katı) | EX (toleranslı) | Ort. deneme | Lint uyarısı |
|---|---|---|---|---|
| ddl | 93,3 | 93,3 | 1,00 | – |
| dict | 93,3 | 96,7 | 1,00 | – |
| dict_values | 91,7 | 95,0 | 1,00 | – |
| dict_values_lint | 93,3 | 96,7 | 1,03 | 2 (q39, q41) |

- **Değer ipuçları çalıştı:** q29 ve q11 düzeldi. q29, sözlükteki metin açıklamasına rağmen yanlış kalmıştı; gerçek değerlerin listesi bunu çözdü.
- **Lint çalıştı:** q39 ve q41 işaretlendi, ikisinde de ikinci denemede çalışan ve doğru sorgu üretildi. Yeniden deneme ilk kez bir işe yaradı (önceki yapılandırmalarda 0/60 sorgu hata vermişti).
- **İstem hassasiyeti (en önemli bulgu):** İstem değişince aynı soruların bir kısmı rastgele gibi çevriliyor. q39 `dict`'te doğruydu, `dict_values`'ta yanlış oldu (aynı bilgi, farklı çıktı). Geliştirme setinde 1–3 soruluk farklar sinyal değil, gürültü olarak okunmalı. Bu yüzden karar hold-out ve eşleştirilmiş testle verilecek.
- **q46 belirsiz çıktı (benim hatam, q60 gibi):** "per student" ifadesi hem öğrenci hem kayıt (öğrenci–modül çifti) olarak okunabiliyor. `dict_values_lint`'in cevabı anahtarları doğru kullanıyor ve savunulabilir bir okuma; gold "kayıt başına" okudu. Geliştirme setini daha fazla sonuca göre değiştirmemek için **q46 yeniden yazılmadı**; belirsiz olarak işaretli kalıyor ve gerçek hata sayılmaz. Hold-out (h12) "per enrolment" diyerek bu belirsizliği baştan kapattı.
- **q57 gerçek mantık hatası:** `COUNT(DISTINCT …) … GROUP BY id_student HAVING …` doğru öğrencileri buluyor ama her biri için "1" döndürüyor (891 satır), gold tek sayı (891) bekliyor. Lint bunu yakalayamaz; olası bir sonuç-biçimi kontrolü ("how many" → tek satır) yalnız fikir olarak not edildi, kodlanmadı.
- q34 ve q43 yine fazladan sütun nedeniyle katı metrikte yanlış (sonuç doğru).

**Çalışma notu:** 503 (Gemini sunucu hatası) `full` çalıştırmasını q36'da kesti. `make_llm` yalnız 429'u yeniden deniyordu; artık 500/502/503/504'te de bekleyip yeniden deniyor, 5 denemeden sonra temiz biçimde durup devam ettiriyor.

## 2026-10-11 · Tüm sonuçlar: dev (60), dondurulmuş hold-out (20), belirsiz set (10) — gemini-3.5-flash-lite, temperature 0, tek çalıştırma
**Hold-out (kural gereği her yapılandırma bir kez; sonuca bakıp mekanizma değiştirilmedi)**
| Yapılandırma | EX (katı) | Yanlışlar |
|---|---|---|
| ddl | 16/20 = %80 | h02, h09, h10, h13 |
| dict | 19/20 = %95 | h09 |
| dict_values | 18/20 = %90 | h09, h10 |
| dict_values_lint | 19/20 = %95 | h09 |
| full | 19/20 = %95 | h09 |

**Geliştirme seti (mekanizmalar bu sete bakılarak tasarlandı, iyimser):** ddl %93,3 · dict %93,3 · dict_values %91,7 · dict_values_lint %93,3 · full %95,0 (toleranslı: %93,3 / %96,7 / %95,0 / %96,7 / %98,3).

**Eşleştirilmiş testler (McNemar tam, soru bazında)**
- Hold-out, ddl vs dict (ve vs full): yalnız dict/full doğru {h02, h10, h13}, yalnız ddl doğru {} → p = 0,25.
- Hold-out, dict_values vs dict_values_lint: lint h10'u düzeltti → p = 1,00.
- 80 soru birleşik, ddl vs full, toleranslı: yalnız full {q11, q29, q39, q41, h02, h10, h13}, yalnız ddl {q57} → p = 0,07. (Yedi sorunun dördü dev'den; mekanizma onlara göre tasarlandı.)
- Hiçbir fark p < 0,05 değil. Yön tutarlı, kesinlik yok (n küçük, tek model, tek çalıştırma).

**h09 gold hatalı çıktı (benim hatam, hold-out dondurulduğu için dosya değiştirilmedi):** soru "highest education below A level", gold yalnız `'Lower Than A Level'`. Veri sözlüğündeki sıraya göre (`No Formal quals < Lower Than A Level < A Level`) `No Formal quals` de "A level'ın altında"; `dict`, `dict_values_lint` ve `full` tam bunu döndürdü. Savunulabilir okumayla bu üç yapılandırma 20/20, ddl yine hatalı (A Level'ı da dahil etti). Rapor kuralı: **dondurulmuş gold'a göre 19/20 ana sayıdır, h09 notla birlikte yazılır.**

**Mekanizma bazında bulgular**
- **Veri sözlüğü:** hold-out'ta tüm kazancın kaynağı (+3 soru: h02 değer yazımı, h10 ve h13 bileşik anahtar). Değer ipuçları hold-out'ta sözlüğün üzerine **ölçülebilir ek kazanç getirmedi** (dict 19/20, dict_values 18/20); dev'de q29'u düzeltti. Not: `dict_values`'ın h10'u kaçırması istem hassasiyetiyle uyumlu.
- **Anahtar kontrolü (lint):** hold-out'ta 1 uyarı (h10), ikinci denemede düzeldi. Yanlış alarm: 0/80 gold sorgu, 0 hold-out tahmini. Yakalamadığı: alt sorgu içindeki hatalar, `USING(...)`, mantık hataları (q57).
- **Yeniden deneme:** tek başına işe yaramadı (0/60 sorgu hata verdi). Lint ile birleşince ilk kez iş yaptı (dev: q39, q41; hold-out: h10).
- **Netleştirme:** belirsiz 10 sorudan 4'ünde soru sordu (a03, a05, a08, a09), 6'sında varsayılan bir yorumla SQL üretti (a01, a02, a04, a06, a07, a10). Net 80 sorunun hiçbirinde gereksiz soru sormadı (0/80). **Ön kayıt tahminim ("çoğunda sorar") tutmadı.** Not: "belirsiz" etiketleri benim öznel kararım; varsayılanlardan bazıları savunulabilir (a02 genel ortalama, a04 Withdrawn). En zayıfı a10: teslim süresini kayıt gününe göre hesaplıyor, son teslim tarihine göre değil, ve bu varsayımı kullanıcıya söylemiyor. Olası iyileştirme: model SQL ile birlikte kullandığı varsayımı da döndürsün (yapılmadı).

**Ön kayıt tahminleri, sonuç:** (1) değer ipuçları value-etiketli soruları iyileştirir: ddl'de 2/7 yanlıştı ✓, ama kazanç sözlükten geliyor, ipuçlarından değil. (2) lint bileşik anahtar hatası yakalar, alt sorguyu yakalayamaz: ✓ (h10 yakalandı; alt sorgu örneği hold-out'ta yoktu, test edilemedi). (3) netleştirme: çoğunda sorar ✗ (4/10); gereksiz soru <%5 ✓ (0/80).

## 2026-10-11 · Türkçe soru seti (çalıştırmadan önce yazılan plan ve tahminler)
**Ne:** dev (60) ve hold-out (20) soruların Türkçe çevirisi (`questions_tr.jsonl`, `questions_holdout_tr.jsonl`); gold SQL ve etiketler aynı, İngilizce metin `question_en` alanında. Çeviriyi ben yaptım; alan terimleri (VLE, TMA, CMA, Exam, Distinction, Withdrawn) kullanıcıların yazacağı gibi İngilizce bırakıldı. "enrolment" → "kayıt" (öğrenci–sunum çifti). **Bilinen risk:** Türkçede "kayıt" `studentRegistration` tablosuyla karışabilir; bu gerçek bir Türkçe kullanıcı sorunu ve bilerek çevirinin parçası.
**Kural:** Kod, istem ve mekanizmalar bu çalıştırma için **dondurulmuş** (yalnız `SETS` girdisi eklendi). Sonuçlara göre değişiklik yapılmaz. Hold-out'un Türkçe sürümü, İngilizce hold-out görüldüğü için "tamamen yeni" değil; yalnız dil etkisini ölçer.
**Çalıştırılacak:** yalnız iki uç yapılandırma, `ddl` ve `full`, iki sette (≈160 istek).
**Ön kayıt tahminleri:**
1. Türkçe, `ddl`'de İngilizceden daha fazla düşüş yaratır; `full`'de düşüş daha küçüktür (sözlük ve değer listesi yazımı sabitler). Kıyas: İngilizce hold-out ddl %80, full %95; dev ddl %93,3, full %95,0.
2. Değer yazımı hataları artar (ör. "Galler" → `Wales`, "%10-20" → `'10-20'`, "lisansüstü" → `Post Graduate Qualification`); uydurma tablo/kolon oranı %0 kalır.
3. `full`'de netleştirme sorusu gereksiz çıkmaz (<%5), ama Türkçe soruların belirsizliği nedeniyle birkaç gereksiz soru görülürse bu raporlanır.

### Sonuçlar (Türkçe, gemini-3.5-flash-lite, temp 0, tek koşu; katı EX)
| Küme | İngilizce | Türkçe | Fark | McNemar p |
|---|---|---|---|---|
| dev ddl | 93,3 | 88,3 | −5,0 (q37, q50, q57 kaybı) | 0,25 |
| dev full | 95,0 | 93,3 | −1,7 (q41 kaybı) | 1,00 |
| hold-out ddl | 80,0 | 90,0 | +10,0 (h02, h09 kazanç) | 0,50 |
| hold-out full | 95,0 | 95,0 | 0 (h13 kaybı, h09 kazanç) | 1,00 |
Uydurma tablo/kolon: 0/4 koşuda %0. Gereksiz netleştirme: full'de 0/60 ve 0/20.
**Tahminlerle karşılaştırma:** (1) dev'de yön tuttu (ddl −5,0, full −1,7) ama hold-out ddl'de ters yöne gitti (+10); hiçbir fark anlamlı değil. (2) Uydurma oranı %0 tuttu; değer yazımı hatası artışı ayrıca sayılmadı, iddia edilmiyor. (3) Tuttu.
**Sonuç:** Türkçe soru, bu modelde ölçülebilir bir kayıp yaratmadı; en büyük etki ddl'de, 20 soruluk kümede fark gürültü düzeyinde. h09 Türkçede "doğru" çıkması gold'un tartışmalı olmasının yan etkisi, gerçek kazanç sayılmaz.

## 2026-10-11 · Paketleme
`api.py` (FastAPI, /ask ve /health, en iyi yapılandırma sabit), `Dockerfile`, `README.md`, `tests/test_api.py` (sahte LLM, 23 test geçti). Docker imajı bu ortamda **derlenmedi** (Docker yok); kullanıcı kendi makinesinde `docker build` ile doğrulamalı.
