# Mevcut üretim motorunun Isparta aktarımı

22 Ekim 2026. Yeni bir haber motoru yazmak yerine Seferihisar üretiminin
`7a862a9b98bf4c63120d550b30406ba961397d7d` sürümündeki Python çekirdeği
`news_engine/` altında bağımsız kopya olarak uyarlanmıştır. Dosya kökeni
`engine-provenance.json` içindedir. Seferihisar deposunda değişiklik yapılmaz.

## Yeniden kullanılan bölümler

- Kalıcı SQLite kayıtları, içerik sürümleri, tekrar engeli ve değişmez yayın iddiaları.
- Haber yaşı, etkinlik başlangıç/bitişi ve zamanlı hizmet uyarısı kontrolleri.
- Tarafsız metin, okunabilir başlık, Türkçe karakter ve ilgili küçük harfli etiketler.
- Ölçülmüş başlık/tarih/mekân/ücret alanları; ilk kart altında açıklama notu.
- Kaynağa bağlı fotoğraf, OCR/konu kontrolü, gerçek kart kırpması, JPEG/manifest eşleme.
- Instagram gönderi/ilk eşleşen story, belirsiz yanıtta yeniden göndermeme,
  yayın öncesi kalıcı kayıt ve zaman/gün sınırları.
- Bağımsız durum dalı, güvenli dışa aktarım ve yedekten geri yükleme yardımcıları.

Facebook, ölçüm ve kaynak keşfi yardımcıları kodda korunur; bağımsız hesap/saha
bağlantıları olmadan çalışıyor sayılmaz. Isparta'da hava kaynağı veya salyangoz
stokları kurulmamıştır. Başka şehrin özel okuyucuları aktarılmaz.

## Isparta sınırı

`isparta.runtime`, 29 gözden geçirilmiş okuyucunun aynı turda okuduğu **tam kaynak**
metnini mevcut kapılardan geçirir. Kamuya açık kısa araştırma alıntısı kanıt diye
yeniden içeri alınamaz. Tarih/mekân/katılım belirsizliği veya hassas içerik bekler.
Kısıtlı/öğrenci/biletli etkinliğin katılım koşulu kartta ve açıklamada korunur.
Kaynak adı/adresi açıklamadadır. Kalıcı veride en fazla 600 karakter kaynak
alıntısı tutulur; ham tam makale, anahtar veya oturum aktarılmaz.

Bir önceki turda uygun olup yeni turda engellenen veya görülmeyen kaydın bekleyen
kartı aynı turda durdurulur. Başlamış/yayımlanmış/belirsiz iddiaların metni ve
medya bağlantıları değiştirilmez. Her eski kayıt tekrar yayınlanmak için kuyruklanmaz.

Marka mevcut Isparta gül logosu, mürdüm/füşya ve açık zemindir. Seferihisar logosu,
anahtarı, veritabanı, takipçileri veya teslim geçmişi taşınmaz. Veritabanı Isparta
kurulum kimliği olmadan açılamaz; yanlış GitHub deposuna durum yazımı reddedilir.

## Bulut akışı

`research.yml`, Türkiye saati 07:20–23:50 arasında saatte iki kez çalışacak
şekilde tanımlıdır. GitHub işleri gecikebilir; bu bir kesintisiz süreç/saniye
garantisi değildir. Tek üretim kilidi altında kaynakları okur, bağımsız
`automation-state` dalını geri yükler, içerikleri hazırlar, güvenli durumu kaydeder
ve Pages paneline yalnız doğrulanmış kamu dosyalarını dağıtır. Durum dalına erişim
hatası yeni boş veriyle devam etme nedeni değildir.

Bağımsız işletim izlemesi ve günlük yedek/geri yükleme denemesi
[ayrı belgede](operations-watch.md) açıklanır (30 Ekim 2026).

Araştırma artifact'i kısa metinli rapordur. Pages kartların dağıtımıdır.
`prepared` veya yeşil workflow sosyal medya paylaşımı anlamına gelmez.

## Bağlantıların durumu (29 Ekim 2026)

Bu bölümün 22 Ekim aktarım sürümü yayını kapalı gösteriyordu; o durum geçmişte
kaldı. Güncel `config/runtime.json` Instagram yayınını ve bağımsız Meta bağlantısını,
hava ve nöbetçi eczane story'lerini, kaynak fotoğrafı ve görsel üretim kapılarını
açık gösterir. GitHub ortam değişkenleri ayrı kapıdır; config tek başına izin kanıtı
değildir. Facebook sayfası yoktur; Facebook teslimi, ölçüme dayalı öğrenme ve yeni
okuyucu etkinleştirme kapalıdır.

Günlük sınır en fazla üç haber gönderisi ve bunların ilk eşleşen üç story'sidir.
Aynı gün 20:00–22:59 arasında aslen yayımlanan ve ilk kez o akşam bulunan yeni bir
haber için en fazla dördüncü gönderi mümkündür; 23:30 sonrası telafi yoktur. Hava
(08:00) ve nöbetçi eczane (17:00) story'leri bu sayıya ektir. Sayı, kaliteyi
geçmeyen içeriği doldurma hedefi değildir.

Kaynağa ait resimler `SOURCE_PHOTOS_ENABLED` kapısı ve yerel OCR/konu modeliyle
değerlendirilir; [kaynak görseli denetimi](source-images.md) sınırları açıklar.
Doğrulanmış kapağı olmayan yeni haber `awaiting_content_visual` olarak bekler.
Instagram Login bağlantısı [bağlantı sözleşmesinde](meta-connection.md) açıklanır.
Hazırlık görevi Meta anahtarı almaz ve eski içerikleri topluca yayınlamaz; yayın
ayrı `publish` işindedir. Hazır kart, yeşil iş, kalıcı Meta yanıt kaydı ve platform
ekranında görülme ayrı kanıtlardır.

## Elektrik kesintisi yalnız story

31 Ekim kullanıcı kararı iki şehirde aynıdır: başlığında elektrik geçen `outage`
kayıtları feed'e çıkmaz. `publish_outage_story` 08:30–21:00 arasında her yayın
kontrolünde en fazla bir story dener, günde en fazla 2 tane, bugünkü ve yarınki
kesintiler için. Haberin 3 story hakkını tüketmez ve haberi geciktirmez.

Kaynak `aedas-planli`: resmî dağıtım şirketi AEDAŞ'ın sorgu sayfasının okuduğu
herkese açık liste, tek GET isteği. Bütün iller aynı listededir. `county` alanı çok
ilçeli kaydın yalnız birini gösterir ve bazen yanlıştır, bir kayıt Antalya veya
Burdur da içerebilir. Bu yüzden ilçe ve yer adları mesajın Isparta bölümlerinden
okunur. Alan ile mesajdaki saat çelişirse kayıt alınmaz. Aynı ilçe ve saatteki
kayıtlar tek kartta birleşir. Yer adları özettir; sokak için kart resmî duyuruya
yollar.

Sitede `robots.txt` yok ve `isparta/fetch.py` bu durumda kapalı kalır. Kullanıcı 31
Ekim'de yalnız bu kaynak için izin verdi: `allow_missing_robots` tek bu kayıtta
vardır ve yalnız 404 veya 410 yanıtını kabul eder. 403, 429 ve 5xx kapalı kalır.
Site ileride robots dosyası yayımlarsa ona uyulur.

## Doğrulama

Mevcut Isparta okuyucu testleri korunur. Üretim motorunun 15 regresyon dosyası
yapay test konumlarıyla taşınır; gerçek yayın geçmişi değildir. Isparta bütün
ilçeleri kapsadığı için Yalvaç'ın yerellik sırası merkezle aynıdır. Başka şehrin
bir hastanesine özel başlık düzeltmesi Isparta'da gerçekmiş gibi uygulanmaz.
Ek uçtan uca test tam kaynak → kalıcı kuyruk → açıklama → gerçek JPEG → kamu
manifesti zincirini, yeni engelin hazırlığı iptal etmesini ve yabancı durum
dosyasının reddedilmesini doğrular. Testlerde sosyal API istekleri sahtedir.

Canlı Actions, Pages ve kalıcı durum kanıtları dağıtım sonrasında ayrıca
raporlanır; bu belge kendi başına dağıtım veya Meta teslim kanıtı değildir.
