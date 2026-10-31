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

## Sınırlar

- Afiş henüz kullanılmıyor. Kartlar konser ve tiyatro için incelenmiş stok sahneyle çıkar.
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
