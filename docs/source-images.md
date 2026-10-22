# Kaynağa bağlı görseller — 22 Ekim 2026

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
