# OULAD Text-to-SQL — mülakat notu

## Tek cümle
Gemini'yi açık bir üniversite veri setine bağlayan bir ajan yaptım; asıl iş, hangi mekanizmanın gerçekten işe yaradığını önceden yazılmış tahminler ve dondurulmuş bir hold-out ile ölçmekti.

## CV satırı (TR)
**OULAD Text-to-SQL ajanı** — 7 tablo / 10,6 milyon satırlık açık veride Gemini ile doğal dilden salt-okunur SQL; 60 geliştirme + dondurulmuş 20 soruluk hold-out üzerinde 5 yapılandırmayı ölçtüm. Veri sözlüğü hold-out doğruluğunu 16/20'den 19/20'ye çıkardı (anlamlı değil, p=0,25); anahtar-bütünlüğü kontrolü 80 gold sorguda 0 yanlış alarm verdi; Türkçe sorularda kayıp ölçülmedi. FastAPI + Docker. *(Docker imajı kendi makinende derlenip doğrulanınca yaz.)*

## CV line (EN)
**OULAD Text-to-SQL agent** — Gemini-based natural-language to read-only SQL over 7 tables / 10.6M rows; benchmarked 5 configurations on 60 dev + a frozen 20-question hold-out. A data dictionary raised hold-out accuracy from 16/20 to 19/20 (not significant, p=0.25); a key-integrity lint had 0 false alarms on 80 gold queries; no measurable loss on Turkish questions. FastAPI + Docker.

## Beş soru, kısa cevap
1. **Ne ölçtün?** Sonuç kümesi eşleşmesi (execution accuracy); SQL metni değil, çalıştırınca aynı sonucu veriyor mu.
2. **Hangi mekanizma işe yaradı?** Veri sözlüğü (özellikle tuzaklar). Değer ipuçları ek fayda vermedi. Yeniden deneme tek başına işe yaramadı.
3. **Anlamlı mı?** Hayır. Kümeler küçük (20/60), tek model, tek koşu; McNemar p 0,25–1,00. Bunu kendim yazdım.
4. **Yanlış çıkan tahminin?** "Netleştirme belirsiz soruların çoğunda soracak" dedim; 10'da 4'ünde sordu (0/80 gereksiz soru).
5. **Hata yaptığın yer?** q60 belirsizdi, sonradan düzelttim ve orijinal sonucu sakladım; h09 gold'u tartışmalı, dondurulduğu için değiştirmedim.

## Savunulabilir / savunulamaz
- Savunulur: ölçüm tasarımı, güvenlik kapısı (yalnız SELECT, authorizer, zaman aşımı), tuzak listesi (imd_band, Withdrawn ≠ boş tarih, anahtar çiftleri).
- Savunulmaz: "%95 doğruluk" demek (20 soru), "Türkçede de çalışır" demek (kayıp ölçülmedi diyebilirsin, kanıtlandı değil), üretime hazır demek.
- Veri: OULAD, CC BY 4.0. Ücretsiz Gemini katmanına yalnız açık veri gönderildi.
