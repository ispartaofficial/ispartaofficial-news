# IspartaOfficial

21 Ekim 2026. Kullanıcıya ait yaklaşık 35 bin takipçili ve kullanıcının
belirttiğine göre yaklaşık dört yıldır aktif olan sayfa için bağımsız kurulum.
Profilde 35 B takipçi, 1.548 gönderi ve mevcut fuşya/gül kimliği görüldü.
Bu gözlem takipçilerin yaş dağılımını veya içerik tercihlerini ölçmez.

## İçerik yönü

Kapsam Isparta merkez ve bütün ilçeleridir. Yaklaşan konser, festival, tiyatro,
sinema, atölye ve üniversite topluluk etkinlikleri önceliklidir. Yerel haberler
ve önemli hizmet duyuruları kapsamda kalır. Sabit bir etkinlik oranı veya yeni
günlük yayın sayısı belirlenmedi; kaliteyi geçmeyen içerik boşluğu doldurmaz.

Kullanıcı yerel haberlerin de unutulmamasını ayrıca istedi. Isparta merkez ve
bütün ilçelerindeki önemli yerel gelişmeler düzenli içerik başlığıdır. Üniversite
ve kültür sanat önceliği, haber takibini kapatmaz. Doğrulanmış önemli bir kamu
duyurusu rutin etkinliğin önüne geçebilir; aynı haberin farklı sitelerdeki kopyaları
ayrı gönderiler sayılmaz. Haber yaşı asıl yayımlanma zamanına göre en fazla 48
saattir; yeniden keşfetmek veya sayfanın güncellenmesi haberi tazelemez.

Bomba32, Kanal32, Haber32 ve Ajans32 haber kaynağı adaylarıdır. 21 Ekim'de
dördünün liste sayfası normal robots/TLS kurallarıyla okunabildi. Bu sonuç,
makale tarihi/gövdesi/fotoğraf bağının doğrulandığı veya üretimde çalıştıkları
anlamına gelmez. Belediye, Valilik ve diğer resmî kurumlar özellikle hizmet ve
zamanlı uyarılar için birincil kaynak olarak değerlendirilir. İddia veya hassas
kişi/olay bilgisi tek bir yerel haber sayfası görüldü diye otomatik yayımlanmaz.

SDÜ ve ISUBÜ resmî takvimleri, SKS duyuruları ve öğrenci toplulukları ilk
araştırma grubudur. Belediye/kültür merkezleri ve resmî organizatörlerin ilanları
tamamlayıcıdır. Bilet sitesi tek başına organizatör sayılmaz. Üniversitede yapılan
her etkinlik herkese açık değildir; katılım koşulları doğrulanır ve kart/açıklamada
açıkça gösterilir. Üniversitenin geçmiş faaliyet raporu yeni etkinlik kaynağı değildir.

## Marka ve kart

Kullanıcı Instagram profilindeki mevcut logonun kullanılmasını onayladı. Orijinal
1080×1080 logo kamu profilinden alındı. Ana kimlik: gül simgesi, beyaz yazı,
fuşya ve koyu mürdüm. Logo değiştirilmez; kart ona göre hazırlanır.

Yeni yerleşim açık zemin, koyu başlık, fuşya kategori/tarih vurgusu kullanır.
Etkinlik ismi, tarih/saat, mekân, ücret ve katılım koşulu ayrı alanlardır.
Kaynak yalnız açıklamada; yaklaşık beş ilgili küçük harfli hashtag kullanılır.
“Detaylar açıklamada.” ilk kartın metni altındadır. Görsel önceliği, kaynakla
eşleşen afiş veya fotoğrafadır. Kontrolsüz, alakasız görsel boşluğu doldurmaz.

## Kaynak okuyucuları ve araştırma

`config/research-sources.json` 29 içerik kaynağı için gözden geçirilmiş okuyucu tanımlar:
Bomba32, Haber32, Kanal32, Ajans32, Valilik, Belediye, Kültür Müdürlüğü,
SDÜ takvimi/SKS, ISUBÜ takvimi/SKS/Toplumsal Katkı ve duyuru arşivi, Bubilet
Isparta, 12 ilçe kaymakamlığı, Gönen, Keçiborlu ve Senirkent belediyeleri.
ISUBÜ topluluk dizini içerik kaynaklarından ayrı keşif kanalıdır. Topluluk adı
bulunması, o topluluğun etkinlik veya Instagram okuyucusunun çalıştığını kanıtlamaz.
Güncel kapsam ve kapalı adaylar `docs/source-coverage.md` içinde tutulur.
Yerel haberler asıl makale tarihini kullanır; güncelleme, liste sırası veya bugünkü
site başlığı eski haberi tazelemez. İki saatte bir planlanan bulut görevi yalnız
araştırma raporu oluşturur. Alan adı, robots, sertifika, yanıt boyutu ve sayfa
sayısı sınırlandırılır. Bir kaynak kısmen okunursa rapor `partial` gösterir.

Üniversite takviminde şehir dışı mekân, geçmiş başlangıç, eksik saat, tarih/saat
çelişkisi veya bilinmeyen katılım koşulu taslak uygunluğunu engeller. Sınırlı
öğrenci/üye etkinliği herkese açık diye sunulmaz; ücret bilinmiyorsa ücretsiz
denmez. Aynı afişin ilgisiz birden fazla ISUBÜ etkinliğinde görünmesi durumunda
afiş reddedilir. Diğer kaynak fotoğrafları da yalnız inceleme adayıdır.

Yalnız bu araştırma turundaki benzer haberler gruplanır. Kalıcı yayın geçmişiyle
tekilleştirme ve gerçekten görsel/içerik doğrulayan yayın hattı sonraki aşamadır.
`eligible_for_drafting` yayın onayı değildir. Rapor tam yazı kopyası yerine kısa
kaynak alıntısı, kaynak adresi ve kanıt özeti tutar. Kaynak okuyucusunun çalışması,
içeriğin güncel olduğu veya otomatik yayına onaylandığı anlamına gelmez.

Belediyede arşiv kartının tarihi yalnız aynı bağlantı ve aynı başlıktaki makaleye
bağlanır. Site başlığı veya fotoğraf dosya adı tarih sayılmaz. Kültür Müdürlüğü
için ulusal ana sayfa şeridi yerine açık bağlantıyla keşfedilen cari yılın yerel
duyuru arşivi kullanılır. Yıl klasörünün tarihi makale tarihi sayılmaz. Tam gün,
yıl, saat ve mekân içeren yerel programlar seanslara ayrılır; eksik bilgiler
bekletilir. Yeni yıl arşivi henüz yayımlanmamışsa durum açıkça raporlanır.

Ek üniversite sayfalarındaki duyuru yükleme tarihi etkinlik günü değildir. Afiş
içeriği okunmamışsa seans uydurulmaz. Başlığı tek bir resmî takvim kaydıyla tam
eşleşen duyuru o kayda ek kanıt olur; ikinci bir etkinlik/gönderi oluşturmaz.
Geçmiş faaliyet raporu yaklaşan etkinlik değildir.

Bubilet seanslarında tam yıl/saat, gerçek mekân adresi, yaş ve bilet koşulları
ayrılır. Sayfadaki gerçek organizatör bölümü kullanılır; platformun şemada
organizatör olarak yazılması yeterli sayılmaz. Kaynak seans fiyatı, her koltuk
ve katılımcıya uygulanacak fiyat garantisi değildir. İptal, tükenmiş bilet ve
eksik/çelişkili koşullar bekletilir. Afiş yalnız görsel inceleme adayıdır.
Bilet listesinde öndeki kartların yanında kalan kartlar dönüşümlü araştırılır;
haber siteleri ve resmî duyurular bu yüzden kapsamdan çıkarılmaz.

## Güncel sınır

Bu aşama tam motor aktarımı değildir. GitHub bağlayıcısında yazma erişimi
yokken, kullanıcıya ait Isparta tarayıcı oturumuyla kod ve PR işlemleri yapılabilir.
Meta/yeni hesap bağlantıları ve sosyal yayın dağıtımı yoktur. Logo ve kart
önizlemesi sosyal medya hesabında herhangi bir değişiklik yapmaz. Kaynak adayları
`config/source-candidates.json` içinde, araştırma için etkin okuyucular ayrı
`config/research-sources.json` içinde tutulur. Bulut görevinin dosyası, başarılı
canlı araştırma ve gerçek yayın ayrı kanıtlardır.

