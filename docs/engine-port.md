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

Araştırma artifact'i kısa metinli rapordur. Pages kartların dağıtımıdır.
`prepared` veya yeşil workflow sosyal medya paylaşımı anlamına gelmez.

## Etkin olmayan bağlantılar

`config/runtime.json` içinde yayın kapalıdır. Meta bağlantısı doğrulanmamıştır;
Facebook sayfası henüz yoktur. Görsel üretim hizmeti bağlı değildir. Kaynağa ait
resimler, üretim hizmetinden ayrı `SOURCE_PHOTOS_ENABLED` kapısı ve yerel OCR/konu
modeliyle değerlendirilir; [kaynak görseli denetimi](source-images.md) sınırları
açıklar. Denetlenmemiş görsel eklenmez, logolu bilgi kartı kullanılır. Bulut model
kurulumu ve gerçekten onaylanan resim ayrıca tarihli kanıt gerektirir. Koddaki
fotoğraf/üretim yeteneği çalışan görsel teslimi olarak sunulmaz. Öğrenme ve yeni
okuyucu etkinleştirme de şimdilik bağlı değildir.

Instagram etkinleştirilmeden önce hesap kimliği `ispartaofficial` olarak GET ile
doğrulanmalı, doğru bağımsız izinler ve medya adresleri kontrol edilmeli, günlük
yayın düzeni netleştirilmelidir. Çekirdeğin iki gönderilik üst sınırı şu anda
**etkin olmayan güvenlik tavanıdır**; yeni yayın kotası ilanı değildir. Hazırlık
görevi Meta anahtarı almaz, içerik paylaşmaz ve eski içerikleri topluca yayınlamaz.

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
