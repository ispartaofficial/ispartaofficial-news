# Günlük haber ve görsel kuralı — 24 Ekim 2026

## 15 Kasım 2026'dan itibaren: günlük sınır yok, güncel haber hemen

Kullanıcı 14 Kasım'da iki fabrika için de kuralı değiştirdi: günlük paylaşım sınırı
yoktur. Güncel bir haber bulunduğu turda, sıraya girmeden ve saat dilimi beklemeden
kendi story'siyle paylaşılır. Aşağıdaki üç/dört sınırı ve saat dilimleri yalnız
14 Kasım ve öncesinin kaydıdır.

- **Güncel haber:** Kaynağın tarihi son 24 saat içinde olmalı ve fabrika haberi son
  8 saatte ilk kez görmüş olmalı. Böylece eski birikmiş haberler topluca
  paylaşılmaz (`immediate_news_item`).
- **Saat:** Yayın 07:00–23:30 arasında yapılır. Gece bulunan haber sabah çıkar.
- **Tur başına:** En fazla 4 haber çifti paylaşılır, çiftler arasında 90 saniye
  bırakılır. Kalanlar bir sonraki turda çıkar.
- **Kontroller:** Kaynak, görsel, tekrar ve medya kontrolleri aynen geçerlidir.
  Kontrolü geçemeyen haber bekler.
- **Belirsiz teslim:** Sonucu belirsiz bir teslim turu durdurur ve o haber asla
  yeniden gönderilmez.
- **Diğer içerikler:** Etkinlik, özet ve eski haberler saat dilimlerinde kalır.
  Hemen paylaşılan haber bir saat dilimini doldurmaz, ama dilimdeki içerik ondan
  sonra 45 dakika bekler.
- **Story sınırları:** Elektrik kesintisi ve etkinlik story'lerinin günlük
  sınırları da kalktı.

## 22 Kasım 2026: rutin servis listeleri ve çelişen tarihler haber kartı olmaz

22 Kasım'da Haber32'nin "Isparta ve İlçelerde Nöbetçi Eczaneler (22 Kasım 2026)"
makalesi haber kartı ve story olarak paylaşıldı: eczane adı ve ilçesi olmayan
yapışık bir adres yığını, kaynağın logolu tanıtım grafiği ve kaynağın kendi yazım
hatasıyla "12 Kasım 2026 Pazar" tarihi. Günün listesi zaten ayrı ve doğrulanmış
nöbetçi eczane story'siyle (`docs/daily-pharmacy-story.md`) paylaşılıyor.

`news_editorial_reason` (`news_engine/quality.py`) artık şunları yayından tutar:

- **`dedicated_pharmacy_story`:** Başlıkta veya makale adresinde nöbetçi eczane
  *listesi* ("nöbetçi eczaneler", "nöbetçi eczane listesi", "hangi eczaneler
  nöbetçi", "nöbetçi eczaneler nerede") ya da açıklamada "nöbetçi olan eczaneler" /
  "nöbetçi eczane listesi". Büyük/küçük harf ve şapkasız yazımlar aynı sayılır.
  Başlıkta soygun, saldırı, olay, açıklama, oda/eczacı, zam, ücret gibi bir haber
  sözcüğü varsa haber yayına devam eder.
- **`dedicated_weather_story`:** Başlığında "hava durumu" geçen rutin bülten (günlük
  hava story'si ayrıdır). Uyarı, sarı/turuncu/kırmızı kod, fırtına, sağanak, kuvvetli,
  kar/dolu yağışı, sel, zirai don gibi bir uyarı sözcüğü varsa haber yayına devam eder.
- **`date_mismatch`:** Yalnız gün+ay(+yıl) biçimli açık tarihler karşılaştırılır.
  Başlıkta tek bir tarih varsa ve açıklama tarih verip bu tarihi hiç anmıyorsa (yıl
  ikisinde de yazılıysa yıl da eşleşmeli) ya da yıl ve gün adıyla yazılmış bir tarihin
  gün adı takvime uymuyorsa ("12 Kasım 2026 Pazar") kart yayınlanmaz. Göreli ifadeler
  (bugün, yarın), sayısal tarihler, başlıkta birden çok tarih ve "6 Mart Spor Salonu",
  "29 Ekim Caddesi" gibi yer adları karşılaştırılmaz.

Bu kapı her araştırma turunda ve her yayın denemesinden önce `prepare` içinde
yeniden çalışır; bu yüzden kapıdan önce kuyruğa girmiş hazır kart da
`blocked_source` olur ve Pages dışa aktarımı onu `editorial_review_required` ile
tutar. Sebep `withheld` tablosuna ve paneldeki `operations.editorial_holds`
sayaçlarına yazılır. Yayımlanmış gönderilere dokunulmaz. 22 Kasım durum
veritabanındaki 422 haber kaydında kapı yalnız bu eczane listesini ve 25 Ekim'deki
"Isparta Hava Durumu Raporu"nu yakaladı; eczacı odası haberi ve tarihli diğer
başlıklar etkilenmedi.

## 16 Kasım 2026'dan itibaren: şehir köşesi

Kullanıcı 14 Kasım'da kaynak haberlerinin yanında etkileşim alacak şehir içerikleri
de istedi. Bunlar `config/city-features.json` içindeki gözden geçirilmiş metinlerden
ve `news_engine/assets/city-features/` içindeki lisanslı fotoğraflardan gelir.
Çalışma sırasında hiçbir metin veya görsel üretilmez.

- **Gönderi (Salı ve Cumartesi, 19:30–22:30):** "Şehir hafızası" kartı. Kaynaklı bir
  tarih veya şehir bilgisi ve yorum isteyen bir soru içerir. Açıklamada kaynak
  bağlantısı, fotoğrafçı ve lisans yazar.
- **Story (Pazartesi, Çarşamba, Cuma, 20:30–23:30):** "Size soruyoruz" kartı.
  Instagram'ın API'si anket veya soru çıkartması eklemeye izin vermez. Bu yüzden
  story yanıt ister; yanıtlar hesaba mesaj olarak gelir.
- **Fotoğraflar:** Wikimedia Commons'tan lisanslı gerçek fotoğraflar kullanılır.
  Fotoğrafçı ve lisans kartın üzerinde ve açıklamada yazar. Her dosya SHA-256 ile
  sabitlenir; değişen dosya reddedilir.
- **Sıra:** Her gün bankadaki sıradaki kullanılmamış giriş paylaşılır. Paylaşılan
  giriş tekrar edilmez. Banka biterse `bank_empty` görünür ve yeni giriş eklenene
  kadar paylaşım yapılmaz.
- **Güvenlik:** Haberlerle aynı kurallar geçerlidir. Kart Pages'te yayınlanıp
  hash'i doğrulanmadan gönderilmez. Talep Meta'ya gitmeden önce kaydedilir.
  Belirsiz teslim asla yeniden gönderilmez ve çözülene kadar seriyi durdurur.
- **Yeni içerik:** Yeni giriş eklerken metin yalnız belirtilen kaynaktaki bilgiyi
  içermelidir. Fotoğraf yalnız Commons'taki açık lisanslı bir dosya olmalıdır.
  `tests/test_city_features.py` her kartın sığdığını denetler.

Kullanıcı her iki hesap için günde **en fazla üç haber gönderisi ve üç haber
story'si** istedi. Sonraki açık yanıtıyla hava durumu ve nöbetçi eczane
story'lerinin bu üç haber story'sine **ek** kalacağını belirtti. Bu sayı
kalite kapısını geçmeyen içeriğin paylaşılacağı bir hedef değildir.

Haber bütçesi Türkiye takvim gününde sayılır. Başlamış ve sonucu belirsiz
iddialar da bütçeyi tüketir; yeniden başlatmak bütçeyi geri açmaz. Hava ve
eczane ayrı günlük tablolarda kalır. Haber story'si yayımlanmış haberin ilk
eşleşen kartıdır; geçmiş pencere kaçırıldı diye eski story topluca gönderilmez.
Mevcut haber pencereleri ve içerikler arasındaki aralık korunur.

## Akşam yeni haber istisnası — Isparta başlangıcı 25 Ekim 2026

Sonraki kullanıcı talimatıyla temel üç haber gönderisi ve ilk eşleşen üç
haber story'si korunur. Kaynağın asıl yayım zamanı aynı Türkiye gününde
20:00–22:59 olan **yeni bir haber** için günlük toplam en fazla dört
haber gönderisi ve dört haber story'si olabilir. Bu sınırsız akşam kotası
değildir. Etkinlik/takvim/hatırlatma veya eski haberi yeniden tarihlemek
dördüncü hakkı açmaz. İlk keşif de aynı gün 20:00'dan sonra olmalı ve kalıcı
kaynak kaydı ilk revizyonda kalmalıdır; eski/yeniden yazılan kayıt bu dar
ek hak için yeterli kanıt değildir. Önceki yayımlanmış kartların metni,
medya kimliği, kayıtları ve tekrar koruması değişmez.

Isparta'da hem yeni 20:00/22:00 pencereleri hem bu dördüncü haber hakkı
**25 Ekim 2026** tarihinde etkinleşir. 24 Ekim akşamına ek hak açılmaz.
Mevcut 21:00 penceresi kalır. Akşam geç çalışan işler en geç 23:30'dan önce,
yalnız bu yeni haber koşuluyla teslim deneyebilir. 23:30 sonrasında veya
ertesi güne taşan toplu telafi yoktur. Diğer zaman, kaynak, görsel/metin,
45 dakika aralığı ve günlük kalıcı iddia kontrolleri korunur. Bu dar
koşullar sağlanmazsa normal üçlük bütçe geçerlidir.

Hava durumu ve nöbetçi eczane story'leri ayrı günlük sınırlardadır;
haberlerin üçüncü veya koşullu dördüncü eşleşen story'sine dahil edilmez.
Başarılı kod/test/dağıtım, ilk doğal akşam tesliminin görüldüğü anlamına gelmez.

Seferihisar'da aynı kesinti, iki revizyon altında aynı kartla paylaşılmıştı.
Tekrar koruması yalnız kayıt kimliğine güvenmemelidir: donmuş önceki kart
içeriği ve görsel bağları da denetlenir. Donmuş gönderi/story/Meta kimlikleri
değiştirilmez. Gerçek değişiklik veya iptal duyurusu ile aynı kartın yeni
revizyonu ayrılır.

9 Kasım 2026: Seferihisar'da kaynak, bir gün önce paylaşılan haberin başlığını
değiştirdi; revizyon 2 yeni kart metni aldı ve aynı haber ertesi sabah ikinci
kez akışa ve story'ye çıktı. Kart metni farklı olduğu için yukarıdaki koruma
yakalamadı. Haberin "güncelleme" gönderisi yoktur: bir revizyonu yayımlanan
haber (`kind=news`) sonraki revizyonlarla yeniden paylaşılmaz
(`duplicate_reason`). Yayımlanmamış kart yeni revizyonla yenilenmeye devam
eder; elektrik kesintisi story'lerinin gerçek değişiklik kuralı değişmez.
Isparta geçmişinde bu durum görülmedi; koruma önceden eklendi.

Görsel tercih sırası kaynağın o habere/etkinliğe ait doğrulanmış gerçek
fotoğrafı veya afişi, konuya uygun denetlenmiş etkinlik sahnesi ve logolu
bilgi kartıdır. Başlık, tarih ve makale bağlantısı doğrulanmadan resim
eklenmez. Kaynağın logosu, genel site görseli, ilgisiz başka haberin fotoğrafı
veya modelin yalnız benzer bulduğu bir görüntü yeterli kanıt değildir.
Model skoru olay/kişi/mekân kimliğini kanıtlamaz. Kaynak engeli veya
onaylanmış uygun görsel yokluğu dürüstçe kaydedilir; her habere resim
garantisi verilmez.

Kod, başarılı hazırlık/dağıtım ve gerçek Meta teslimi ayrı kanıtlardır.
Doğal yeni yayının teslimi ayrıca kalıcı kayıt ve mümkün olan GET
gözlemiyle doğrulanır; bu belge tek başına yayın kanıtı değildir.
