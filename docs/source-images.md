# Kaynağa bağlı görseller — 22 Ekim 2026

## 24 Ekim: aynı haberin gerçek görseline erişim

Kullanıcı Isparta gönderi ve haber story'lerinde mümkün olduğunca doğru, uygun
ve gerçek görsel istedi. Gerçek sayfa yapısında iki somut eksik doğrulandı:
Bomba32'nin ana fotoğrafı metin gövdesinin dışında ve yayınevinin TE CDN
alanında; Ajans32'nin ana görseli metin çocuğunun dışında, `src` yerine
`srcset` kullanıyor. İki yayınevinin yalnız tam kaynak alanı, tam CDN alanı ve
yayınevine özgü resim yolu eşleşmesi kabul edilir. CDN robots kuralları aynı
normal TLS/robots okuyucusuyla uygulanır; yönlendirme veya genel alt alan
izni yoktur. Yeni bir izin veya erişim anahtarı oluşturulmaz.

Kaynak resminin kimliği, genel schema.org tahminine bırakılmaz. Isparta'nın
gözden geçirilmiş makale okuyucusu aynı başlık ve asıl yayım tarihini yeniden
okur. SDÜ/ISUBÜ takvimleri de aynı başlık, başlangıç/bitiş, saat ve mekânla
eşleşen seansın kendi görselini seçer; ortak ISUBÜ yer tutucuları yine reddedilir.
Arşiv/temsili etiketler, farklı tarih veya farklı başlık kabul edilmez.

Cadde/yol yenilemesinin açıkça başladığı haber için ayrı `roadworks` konusu
eklendi; yalnız aynı haberin kaynak fotoğrafında kullanılabilir, üretilecek
bir olay görseli izni değildir. Yerel CLIP ve OCR eşikleri düşürülmedi. Yol
fotoğrafını bulmak, fotoğrafın son onayı değildir: 24 Ekim yerel kontrolde
Ajans32 Cumhuriyet Caddesi fotoğrafı doğru makaleye bağlanabildi ama CLIP
eşik altında kaldı ve kullanılmadı. Bomba32 drone haberi için geniş bir yeni
fotoğraf konusu etkinleştirilmedi. Görsel bulunamayan veya denetimi geçmeyen
haberde bilgi kartı kalır; tüm haberlerin resimle tamamlandığı iddia edilmez.
Bu yerel inceleme doğal bulut teslimi veya Instagram paylaşımı değildir.

Isparta'nın kaynak fotoğrafı/afiş hattı, yeni üretim hizmetinden bağımsızdır.
`SOURCE_PHOTOS_ENABLED=true`, yalnız mevcut güvenilir okuyuculardaki aynı
makale/etkinliğe bağlı görsel adaylarını değerlendirmeye açar.
`ILLUSTRATIONS_ENABLED=false` kalır; Cloudflare veya Meta anahtarı araştırma işine
verilmez. Yeni ücretli servis veya kota artışı yoktur.

Türkçe/İngilizce Tesseract ve sabit revizyon/hash ile denetlenen yerel CLIP CPU
modeli normal araştırma işine kurulur. Model kurulamazsa ya da OCR/konu/tarih
kontrolü başarısızsa resim onaylanmaz, mevcut logolu bilgi kartı korunur.
Model kontrolü kimlik/mekân kanıtı veya doğruluk garantisi değildir.

Mevcut üretim kuralları korunur: en fazla iki resim adayı okuması, robots/TLS ve
güvenilir sunucu sınırı, aynı kaynak adresi/başlık/tarih/mekân/seans bağı, belirsiz
veya başka haberde kullanılmış resmin reddi, afişin tam çerçevesi ve gerçek kart
kırpmaları. Tüm haber türlerinde resim bulunacağı iddia edilmez; geniş ve belirsiz
konularda bilgi kartı devam eder. Bilet platformunun dış CDN resmi sırf görünür
olduğu için güvenilir sayılmaz; mevcut sınırlar gevşetilmemiştir.

Görsel ilk kez bağlanırken önceden hazırlanmış metin kartının görsel incelemesi,
sürümlü dosya yolu ve JPEG özeti birlikte yenilenir. Modeli olmayan yayın işi,
kalıcı olarak doğrulanmış resim bağını kullanır. Başlamış/yayımlanmış/belirsiz
iddiaların eski pikselleri ve metni değiştirilmez. Kaynak yalnız açıklamadadır.

Canlı araştırmada ayrıca görülen TOKİ arsa haberi, gövdesindeki spor tesisleri
sözcüğü yüzünden spor kategorisine düşüyordu. Kategori artık açık başlık
ipuçlarından daraltılır; yan ayrıntı haberi spor veya ulaşım haberi yapamaz.

Testler; metin kartından resimli karta gerçek SQLite/JPEG/manifest geçişini,
üretim kapalıyken kaynak resmini denetlemeyi, sonradan modelsiz aynı resim/proof
bağını korumayı ve eksik model/OCR/yanlış afiş tarihi/yanlış konuda bilgi kartına
dönüşü kapsar. Test görselleri yapay fixture'dır. Gerçek bulut kurulum sonucu,
okunan resim sayısı ve başarılı gerçek resim bağı ayrıca tarihli raporla
doğrulanır; kod ve yeşil iş tek başına bir resmin onaylandığı anlamına gelmez.

Meta uygulaması bu aşamada yalnız oluşturma özetinde hazırlandı. Son düğme Meta
Platform Terms ve Developer Policies kabul ettiği için işlem anında kullanıcı
onayı beklenir. Sosyal yayın, yeni izin/anahtar ve Facebook bağlantısı açılmadı.
