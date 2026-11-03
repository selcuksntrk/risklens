# Selçuk: son kontroller

Toplam hedef: 3–5 saat. Ev videon çekildi ve demoya alındı (fotoğraflar bulanık, ses yok); yüzünü çekmen gerekmiyor.

## 1. Görsel gözlem ve sonuç incelemesi — 60–90 dakika

`eval/synthetic-observations.json` dosyası model çalıştırmalarından önce ajan tarafından incelenmiş gözlemleri içeriyor; insan/uzman etiketi değil. Mevcut beş sahne daha önce geliştirmede kullanıldı.

- Klipleri ve raporların kanıt karelerini karşılaştır. Nesne, ilişki ve “bilinmiyor” ayrımını kontrol et.
- Görünmeyen ankrajı “yok” diye etiketleme. Her belirsizlik ve uyuşmazlığı kaydet.
- Aynı nesneye ait tekrarları ayrı doğru bulgu gibi sayma. Hataları ve atlananları koru.
- İnsan incelemesi tamamlanmazsa precision/recall yayımlama; operasyonel sonuçlar kullanılabilir.

## 2. iPhone / Safari — 30–45 dakika

Kullanılacak dosya: `docs/submission/private/phone-sample.mp4` (lisanslı sentetik örnek). AirDrop veya kendi dosya aktarım yönteminle iPhone'da Dosyalar'a kaydet.

1. Safari'de canlı ürünü aç (beyaz sayfa görürsen bir kez yenile; eski önbellek sorunu düzeltildi). İlk ekranda “Record a room” ve “Upload a video” görünmeli. iPhone modeli, iOS sürümü, tarih ve sayfadaki release kimliğini not al.
2. Üstteki “Samples” → dört örnek kartı (gerçek ev + üç tasarlanmış sahne). Her birinde “Open report” ve “Watch analysis replay”: rapor, kanıt kareleri, video oynatıcı ve replay açılıyor mu? Yatay taşma veya okunamayan yazı var mı? Tasarlanmış sahnelerde “answer key” kutusu doğru mu (5/5, 4/4, 4/5)?
3. Ana ekrana dön, “Upload a video” ile Dosyalar'daki örneği seç. Doğrudan önizleme ekranı açılmalı. Kamera/mikrofon izni vermen gerekmez. Önizleme ve yön doğru mu?
4. Bağlam: “Synthetic interior. Attachment conditions are unknown.” Yükle; süreç ve bitmiş/kısmi durum anlaşılır mı?
5. Kaynak bağlantısını açıp geri dön. Aynı rapor kalıyor mu?
6. Aynı dosyayla karşılaştırma yap. Yeni fiziksel değişiklik onayı çıkmamalı. Bunun dosya eşitliği kontrolü olduğunu kaydet.
7. Başka özel Safari oturumunda özel rapor linkini aç: rapor erişilebilir olmamalı; public örnek açılmalı.
8. Sonucu `HANDOFF.md` alanlarına yaz. Kamera kaydı, mikrofon veya Android testlerini yapılmış sayma.

## 3. Ses kaydı ve video — 60–90 dakika

Uygulama ekran kayıtları ajan tarafından **canlı üründen** alındı (headless Chrome, 1920×1080), 4 Kasım arayüzüyle: `docs/submission/private/footage-v2/01.mp4`–`07.mp4` (eski set `footage-final/` olduğu gibi duruyor). 01 senin evinin örnek raporu (her karede “Real recording · Selçuk's home” etiketi), 02 ana sayfa ve örnekler, 03 tasarlanmış çocuk odasının yeni canlı çalıştırması (bekleme kısaltıldı, etikette gerçek süre), 04 kanıt + FEMA adımları + Muse Image çizimi, 05 aynı dosya kontrolü, 06 tasarlanmış sahneler kartı + answer key, 07 senin evinin replay'i + kapanış kartı. Ayrıntılar `footage-v2/recording-log.json`.

1. Önce prova videosunu izle: `docs/submission/output/preview-v2/SILENT-PREVIEW-not-for-submission.mp4` (sessiz, taslak altyazılı). Görüntü ile `NARRATION.md` metninin uyuştuğunu kontrol et; uymayan cümle varsa not al.
2. `NARRATION.md` metnini iki kez oku; `private/voice-take-1.m4a` ve `voice-take-2.m4a` olarak kaydet (150–175 sn). Müzik yok. Videoyu açıp üzerine okumak zamanlamayı kolaylaştırır.
3. Seçtiğin kayda göre `captions-draft.srt` zamanlarını düzelt → `private/captions-aligned.srt` (istersen ajana ses dosyasını verip hizalatabilirsin).
4. Birleştir: `python3 scripts/assemble_demo.py --clips docs/submission/private/footage-v2 --voice docs/submission/private/voice-take-1.m4a --captions docs/submission/private/captions-aligned.srt`
   (Metni değiştirirsen taslak altyazıyı yenile: `python3 scripts/draft_captions.py`.)
5. Çıktıyı (`docs/submission/output/review-1/risklens-review.mp4`) telefonda sesli ve sessiz izle; okunamayan yer veya fazla iddia varsa düzelt.

## 4. Son teslim — 30–45 dakika

PR #1 `main`'e birleştirildi (3 Kasım); form ve videodaki linkler `main`'i gösteriyor.

`FORM.md` ve `RIGHTS.md` ile gerçek platform alanlarını/deklarasyonlarını kontrol et. Video bağlantısını giriş yapmadan aç; public kaynak dalının linkini kullan. Platformda gönderimi tamamla ve teyit kaydını `HANDOFF.md` içine yaz.

İç hedef: **4 Kasım 22:00 İstanbul / 14:00 ET**. Resmî son tarih: **5 Kasım 05:00 İstanbul / 4 Kasım 21:00 ET**. Taslak form, video dosyası veya çalışan site teslim teyidi yerine geçmez.
