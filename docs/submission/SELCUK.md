# Selçuk: ev çekmeden son kontroller

Toplam hedef: 3–5 saat. Kendi evini veya yüzünü çekmen gerekmiyor.

## 1. Görsel gözlem ve sonuç incelemesi — 60–90 dakika

`eval/synthetic-observations.json` dosyası model çalıştırmalarından önce ajan tarafından incelenmiş gözlemleri içeriyor; insan/uzman etiketi değil. Mevcut beş sahne daha önce geliştirmede kullanıldı.

- Klipleri ve raporların kanıt karelerini karşılaştır. Nesne, ilişki ve “bilinmiyor” ayrımını kontrol et.
- Görünmeyen ankrajı “yok” diye etiketleme. Her belirsizlik ve uyuşmazlığı kaydet.
- Aynı nesneye ait tekrarları ayrı doğru bulgu gibi sayma. Hataları ve atlananları koru.
- İnsan incelemesi tamamlanmazsa precision/recall yayımlama; operasyonel sonuçlar kullanılabilir.

## 2. iPhone / Safari — 30–45 dakika

Kullanılacak dosya: `docs/submission/private/phone-sample.mp4` (lisanslı sentetik örnek). AirDrop veya kendi dosya aktarım yönteminle iPhone'da Dosyalar'a kaydet.

1. Safari'de canlı ürünü aç. iPhone modeli, iOS sürümü, tarih ve sayfadaki release kimliğini not al.
2. “Open completed report”: rapor ve kanıt kareleri açılıyor mu? Yatay taşma veya okunamayan yazı var mı?
3. “Use your own video” üzerinden Dosyalar'daki örneği seç. Kamera/mikrofon izni vermen gerekmez. Önizleme ve yön doğru mu?
4. Bağlam: “Synthetic interior. Attachment conditions are unknown.” Yükle; süreç ve bitmiş/kısmi durum anlaşılır mı?
5. Kaynak bağlantısını açıp geri dön. Aynı rapor kalıyor mu?
6. Aynı dosyayla karşılaştırma yap. Yeni fiziksel değişiklik onayı çıkmamalı. Bunun dosya eşitliği kontrolü olduğunu kaydet.
7. Başka özel Safari oturumunda özel rapor linkini aç: rapor erişilebilir olmamalı; public örnek açılmalı.
8. Sonucu `HANDOFF.md` alanlarına yaz. Kamera kaydı, mikrofon veya Android testlerini yapılmış sayma.

## 3. Ses kaydı ve video — 60–90 dakika

Uygulama ekran kayıtları ajan tarafından **canlı üründen** alındı (headless Chrome, 1920×1080): `docs/submission/private/footage/01.mp4`–`07.mp4`, kesintisiz ham kayıt `raw-run.mp4`, ayrıntılar `recording-log.json`. Bekleme kısaltılan yerlerde ekranda gerçek süreyi yazan etiket var.

1. Önce prova videosunu izle: `docs/submission/output/preview/SILENT-PREVIEW-not-for-submission.mp4` (sessiz, taslak altyazılı). Görüntü ile `NARRATION.md` metninin uyuştuğunu kontrol et; uymayan cümle varsa not al.
2. `NARRATION.md` metnini iki kez oku; `private/voice-take-1.m4a` ve `voice-take-2.m4a` olarak kaydet (150–175 sn). Müzik yok. Videoyu açıp üzerine okumak zamanlamayı kolaylaştırır.
3. Seçtiğin kayda göre `captions-draft.srt` zamanlarını düzelt → `private/captions-aligned.srt` (istersen ajana ses dosyasını verip hizalatabilirsin).
4. Birleştir: `python3 scripts/assemble_demo.py --voice docs/submission/private/voice-take-1.m4a --captions docs/submission/private/captions-aligned.srt`
5. Çıktıyı (`docs/submission/output/review-1/risklens-review.mp4`) telefonda sesli ve sessiz izle; okunamayan yer veya fazla iddia varsa düzelt.

## 4. Son teslim — 30–45 dakika

**İlk iş:** PR #1'i (`codex/home-test-readiness` → `main`) *merge commit* ile birleştir: `gh pr ready 1 && gh pr merge 1 --merge`. Form ve videodaki linkler `main`'i gösteriyor.

`FORM.md` ve `RIGHTS.md` ile gerçek platform alanlarını/deklarasyonlarını kontrol et. Video bağlantısını giriş yapmadan aç; public kaynak dalının linkini kullan. Platformda gönderimi tamamla ve teyit kaydını `HANDOFF.md` içine yaz.

İç hedef: **4 Kasım 22:00 İstanbul / 14:00 ET**. Resmî son tarih: **5 Kasım 05:00 İstanbul / 4 Kasım 21:00 ET**. Taslak form, video dosyası veya çalışan site teslim teyidi yerine geçmez.
