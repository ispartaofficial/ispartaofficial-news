# Konser, festival ve tiyatro kaynakları

31 Ekim 2026 durumu. Panelde iki etkinlik vardı ve ikisi de eğitimdi. Tek bilet
kaynağı Bubilet 27 Ekim'den beri bulut sunucularına HTTP 403 dönüyor; engel aşılmaz,
kaynak kayıtlı kalır. Isparta Belediyesi'nin etkinlik sayfası 2022'de, SDÜ SKS
etkinlik arşivi 2021'de kalmış; ikisi de eklenmedi. Passo'nun şehir sayfasında
Isparta verisi yok.

İki kaynak eklendi:

| Kaynak | Sayfa | Kapsam |
|---|---|---|
| `biletinial-isparta` | Biletinial müzik, Isparta | Konser; fiyat, organizatör, yaş sınırı |
| `etkinlik-isparta` | etkinlik.io Isparta | Konser, festival, tiyatro; fiyat ve organizatör yok |

Biletinial bulutta okunuyor. etkinlik.io okunamazsa diğer kaynakları durdurmaz,
panelde görünür.

## `listed_sessions` okuyucusu

Şehir listesi yalnız gösteri sayfalarını verir. Bir gösterinin sayfası bütün turne
şehirlerini içerir, bu yüzden yer kanıtı seansın kendi `Event` kaydındaki Isparta
adresidir. Başka bir gösterinin kaydı alınmaz; başlık sayfanın başlığıyla aynı olmalıdır.

Biletli olma kanıtı Biletinial'da seansın `offers` alanı, etkinlik.io'da o etkinliğe
ait bilet bağlantısıdır. Kanıt yoksa kayıt `participation_conditions_unknown` ile bekler.
İptal, satışı kapanmış veya bilet durumu doğrulanmamış seans bekletilir. Tür yalnız
kaynağın kendi kaydından gelir: Biletinial sayfası konser, etkinlik.io'da etkinliğin
kendi kırıntı yolu. Konser ve festival genel yayın kapılarından geçer: açık başlangıç
saati, en fazla 30 gün sonrası, Isparta'daki mekân.

Biletinial'ın yapılandırılmış saati bazı yanıtlarda üç saat ileri kayar: 31 Ekim'de
aynı seans bir koşuda 20:30, sonrakinde 23:30 geldi. Saat bu yüzden sayfada görünen
seans satırından doğrulanır (`04 Kasım Çarşamba · 21:30 Isparta Holly Stone`). Satırla
eşleşmeyen kayıt `session_clock_unconfirmed` ile bekler. Aynı kayma kaydı iki kimliğe
bölüp ilk kartı "Etkinlik bilgisi güncellendi" başlığıyla çıkarıyordu. Artık yayımlanmış
bir kaydı olmayan etkinlik ilk duyuru sayılır; kaldırılan okuma bekletmesi de değişiklik
değildir.

Bir şehir listesi kısadır; `LISTED_SESSION_CAP` 14 sayfanın tamamını okur. Döndürerek
okumak, o turda görülmeyen etkinliği `not_reobserved_current_run` ile düşürürdü.

Aynı seans iki listede farklı yazılır (`Ozbi` / `Ozbi Konseri`, `Holly Stone Isparta` /
`Isparta Holly Stone`). Saat aynıysa ve başlıklardan biri diğerini içeriyorsa tek kayıt
sayılır; önce yazılan Biletinial kalır, çünkü fiyatı ve organizatörü vardır.

## 12 Kasım: tiyatro listesi, seans afişi ve yeni etkinlik story'si

Kullanıcı isteği: bilet sitelerindeki tiyatro ve konserler her gün taransın, her yeni
etkinlik kendi görseliyle story olarak çıksın.

- `biletinial-isparta-sahne` eklendi (`/tr-tr/tiyatro/isparta`). 12 Kasım'da bu liste
  13 gösteri veriyordu (tiyatro, çocuk oyunu, stand-up) ve hiç okunmuyordu. Tür
  listeden gelir: `theatre`.
- Bilet sitesindeki yeni etkinliğin duyurusu (`publication_policy.event_story`:
  Biletinial, Bubilet, etkinlik.io) artık akış sırası beklemez; bulunduğu turda
  yalnızca story olarak çıkar, akışta yer tutmaz. Günde en fazla 3 etkinlik story'si
  (`EVENT_STORY_LIMIT`), elektrik kesintisi ve güncelleme story'lerinden ayrı sayılır,
  yakın tarihli olan önce gelir. "3 gün kaldı" ve "bugün" hatırlatmaları akışta kalır.
  Ezginin Günlüğü duyurusu 9–12 Kasım arasında haberlerin arkasında beklemişti.
- Seansın kendi `Event` kaydındaki afiş kullanılır (`source_images` artık
  `listed_sessions` okuyucusunu da tanır). Afiş Biletinial'ın görsel sunucusundadır
  (`IMAGE_ORIGINS`). OCR ve konu kontrolü bu afişi artık reddetmez, yalnızca sıralar;
  bir gösterinin bütün seansları aynı afişi kullanabilir (`same_event_artwork`).
- Afişi olan etkinliğe sahne üretilmez: afiş okunamıyorsa kart bekler. Seans kaydında
  hiç görsel yoksa sahne üretilebilir.
- Kullanıcı kararı (12 Kasım): Biletinial'ın görsel sunucusu
  `b6s54eznn8xq.merlincdn.net` her afişi herkese açık verir, ama sahip olmadığı
  `robots.txt` için HTTP 403 döner (nesne deposu davranışı). Yalnızca bu incelenmiş
  sunucu için 403 "robots dosyası yok" sayılır (`robots_absent_as_403`,
  `delivery_sources`). Başka her sunucuda ve 401/429/5xx yanıtlarında kural
  değişmedi: okuma durur. Sayfaları 403 dönen kaynaklar (Bubilet, etkinlik.io) bu
  istisnanın dışındadır.
- 13 Kasım: merge sonrası ilk iki turda turdaki altı görsel okuma hakkının hepsi haber
  görsellerine gitti, hiçbir gösteri afiş alamadı. Afişlerin artık haberlerden ayrı,
  tur başına 4 okuma hakkı var (`MAX_ARTWORK_READS`, `MAX_ARTWORK_CHECKS`). Bubilet'in
  görsel adreslerine eklenen `format=auto` seçeneği de tanındı.

## Sınırlar

- Bubilet ve etkinlik.io bulut sunucularına hâlâ HTTP 403 dönüyor; engel aşılmaz.
- Aynı gün iki seansı olan gösteri (Kübik Prens 13:00 ve 15:00) iki ayrı story olur.
- "İçimizdeki Şeytan" ve "Yarım Kalan Aşklar" gibi adlar haberler için yazılmış hassas
  içerik kuralına takılıp `sensitive_claim_requires_review` ile bekliyor.
- etkinlik.io'nun festival listesi şu an boş. Isparta festivalleri mevsimlik.
- Yerel haberlerde başlığı veya metni konser, festival, kermes gibi sözcükler içeren
  kayıtlar `event_or_notice_validity_requires_review` ile bekler. Bu koruma değişmedi;
  festival duyurusu bu yüzden haberden değil etkinlik kaynağından gelmelidir.
- etkinlik.io ilk bulut koşusunda okunamadı. Site Cloudflare arkasında; neden doğrulanmadı.

## Kart yazı ölçeği

31 Ekim kullanıcı geri bildirimi: her kart farklı yazı boyutuyla çıkıyordu. Sürüm 2
(`isparta-editorial-v2`) Seferihisar ile aynı ölçeği kullanır: başlık 52, tarih 34,
metin 30, açıklama notu 26, kategori 28, marka 34/24, kullanıcı adı 23. Yalnız sığmayan
başlık 44'e, sığmayan kategori 24'e iner. Yayımlanmış kartlar sürüm 1 boyutlarını korur.
Bulut kartları DejaVu Sans kullanır; aynı yazı tipi `news_engine/assets/fonts` içindedir.
