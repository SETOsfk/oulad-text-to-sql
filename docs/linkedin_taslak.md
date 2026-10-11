Bir text-to-SQL ajanına eklediğim her mekanizmayı ölçtüm. Beklediğimden az şey işe yaradı.

Gemini'ye Open University'nin açık öğrenci verisini (7 tablo, 10,6 milyon satır) bağladım ve 60 geliştirme sorusu ile dondurulmuş 20 soruluk bir hold-out hazırladım. Sonra tek tek denedim.

Veri sözlüğü hold-out doğruluğunu 16/20'den 19/20'ye çıkardı. Kolon değerlerini isteme eklemek ek bir fayda vermedi. Yeniden deneme tek başına bir şey değiştirmedi: 60 sorunun hiçbirinde düzeltilecek çalışma hatası çıkmadı. Anahtar-bütünlüğü kontrolüm 80 doğru sorguda sıfır yanlış alarm verdi, ama dar bir hata türünü yakalıyor. Soruları Türkçeye çevirince ölçülebilir kayıp olmadı.

Hiçbir fark istatistiksel olarak anlamlı değil (20 ve 60 soru, tek model, McNemar p 0,25 ve üzeri). Tahminlerimi çalıştırmadan önce yazdım. Netleştirme sorusu için "çoğunda soracak" dedim; 10 belirsiz sorunun 4'ünde sordu.

API'ye bağlanmak 15 satır. Zor olan, cevabın doğru olduğunu ölçmekti.

Kod, sonuçlar ve karar günlüğü: github.com/SETOsfk/oulad-text-to-sql

---
I wired Gemini to the open OULAD student dataset and measured every mechanism I added. A data dictionary lifted hold-out accuracy from 16/20 to 19/20, but nothing was statistically significant on 20 and 60 questions. Connecting the API takes 15 lines; proving the answers are right is the work.

#TextToSQL #LLM #DataScience #Gemini
