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

Biletinial Seferihisar'da aynı alan adından bulutta okunuyor. etkinlik.io'nun bulut
erişimi ilk koşuda görülecek. Okunamazsa diğer kaynakları durdurmaz, panelde görünür.

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
- Kesinti kaynağı yok; ayrıntı [motor aktarımı](engine-port.md) belgesindedir.
