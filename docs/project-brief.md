# IspartaOfficial

26 Ekim 2026: [görsel öncelikli yayın sözleşmesi](visual-first-publication.md).
Yeni gönderide önce doğrulanmış kaynak fotoğrafı/afişi, yoksa konuya uygun
gerçekçi görsel kullanılır; doğrulanmış kapak görseli olmayan yeni yayın bekler.
Uyumsuz kaynak görselleri aynı içerik/revizyon için kısa kalıcı beklemeye alınır;
iki dosyalık hak sonraki turlarda aynı reddedilen resimlerle tüketilmez. Görsel
bekleme sonucu işletim kaydında hata yerine normal bekleme olarak kalır.

24 Ekim akşam politikası: temel günlük üç haber gönderisi ve üç eşleşen
haber story'si sürer. 25 Ekim 2026'dan başlayarak 20:00–22:59'da aslen
yayımlanmış ve o akşam ilk kez keşfedilmiş ilk revizyon yeni haber için
günlük toplam en fazla dört haber çifti olabilir. Yeni 20:00/22:00
pencereleri de aynı başlangıç tarihine bağlıdır; 24 Ekim'e ek hak açılmaz.
23:30 sonrası telafi yoktur. [Sınırlar](news-publication-policy.md).

24 Ekim 2026 güncel kullanıcı kuralı: [günlük üç haber gönderisi ve üç haber
story'si](news-publication-policy.md); hava ve eczane story'leri buna ektir.
Kaynakla eşleşen gerçek görsel önceliklidir. Aşağıdaki tarihli aktarım notları
kurulum geçmişidir; anlık bağlantı ve teslim sonucu ayrıca doğrulanır.

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
site başlığı eski haberi tazelemez. Saatte iki kez planlanan bulut görevi araştırma raporu, kalıcı kuyruk ve
markaya uygun kart oluşturur. Bu hazırlık Meta teslimi değildir. Alan adı, robots, sertifika, yanıt boyutu ve sayfa
sayısı sınırlandırılır. Bir kaynak kısmen okunursa rapor `partial` gösterir.

Üniversite takviminde şehir dışı mekân, geçmiş başlangıç, eksik saat, tarih/saat
çelişkisi veya bilinmeyen katılım koşulu taslak uygunluğunu engeller. Sınırlı
öğrenci/üye etkinliği herkese açık diye sunulmaz; ücret bilinmiyorsa ücretsiz
denmez. Aynı afişin ilgisiz birden fazla ISUBÜ etkinliğinde görünmesi durumunda
afiş reddedilir. Diğer kaynak fotoğrafları da yalnız inceleme adayıdır.

Araştırma turundaki benzer haberler gruplanır. Mevcut üretim çekirdeğinin kalıcı
tekilleştirmesi, metin/tarih ve görsel/manifest kapıları ayrıca aktarılmıştır.
Görsel üretim hizmeti ve Meta bağlantısı henüz etkin değildir. Kaynak resimleri
ayrı kapıyla ve yerel OCR/konu modeliyle denetlenir; `docs/source-images.md`
kurulum ile gerçek resim onayının ayrı kanıtlar olduğunu açıklar.
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

22 Ekim 2026: mevcut üretim çekirdeği `news_engine/` altında Isparta'ya
uyarlanmıştır. `docs/engine-port.md` kapsamı ve etkin olmayan bağlantıları
açıklar. Kaynak resimleri için OCR/konu modeli bulutta kurulmuştur; son doğrulanan
turda gerçek bir kaynak resmi onaylanmamıştır. Bağımsız Meta bağlantısı ve görsel
üretim hizmeti kapalıdır; Facebook sayfası yoktur. Instagram Login kodu ve yalnız
GET testi `docs/meta-connection.md` içinde açıklanır; Meta'nın hesap sahibinden
istediği şifre doğrulaması beklemektedir. Ölçüm ve kaynak etkinleştirme henüz
bağlı değildir. Araştırma, kalıcı hazırlık,
bulut dağıtımı ve gerçek sosyal teslim ayrı kanıtlardır. Başka şehrin anahtarı,
logosu, veritabanı veya teslim kayıtları taşınmaz.

## 22 Ekim: günlük nöbetçi eczane story

Kullanıcı Isparta merkez ve merkez mahalleleri için her gün 17:00 hedefiyle
nöbetçi eczane adı, adresi ve varsa işletme telefonunu istedi. Kaynak Isparta
Eczacı Odasıdır; ilçeler filtrelenir. Orijinal logo, açık gri/beyaz 3D fon ve
kırmızı E tabelası kullanılır. İlk pembe/mor atmosfer ve artı simgesi kullanıcı
tarafından reddedildi. [Akış ve sınırlar](daily-pharmacy-story.md). Meta ve
yayın kapıları kapalı kalır; hazırlanmış kart gerçek paylaşım değildir.

26 Ekim 2026: [görsel kuyruğunu kurtarma ve kalıcı stok](visual-backlog-recovery.md).
İki başarısız üretim, aynı seans sahnesinin gereksiz tekrarı ve Bubilet CDN robots 404 nedeni ayrı ele alınır.
Canlı sonuç için tarihli dağıtım/SQL kanıtı gerekir; eski kurulum notları güncel Meta durumu sayılmaz.


### 28 Ekim: eski görsel arşivinin sınırlı onarımı

Önceki temizleme kuralıyla silinen, yayımlanmış kartlara bağlı görsel satırları yalnız bu deponun 26 Ekim durum yedeğinden geri alınır. Sabit yedek ve satır özeti, değişmemiş sahip yayın satırları ve gözlenen mevcut durum birlikte eşleşmelidir. Yeni bir yayın aynı anahtarı kullanıyorsa veya kayıt başka türlü değiştiyse onarım atlanır. Yeni yayın, kota artışı veya eski durum veritabanına dönüş yapılmaz. Mevcut budama koruması bu kayıtları korur. Instagram üzerinde eski içeriğin doğrudan gözlemiyle web arşivinin doğrulanması ayrı kanıtlardır.

Onarım mevcut 80 görsel/12 MiB sınırını yükseltmez. Yer gerekiyorsa yalnız süresi geçmiş veya yerini yeni sürüm almış taslaklara bağlı kullanılmayan önbellek satırları temizlenir. Aktif taslak/yayın görseli temizlenmez; yeterli yer yoksa onarım atlanır, normal durum yüklemesi kesilmez.

29 Ekim: budama bütçesi önce dondurulmuş yayın görsellerine ayrılır; yeni taslaklar yalnız kalan alana sığar. Eski zaman damgalı korunan satırların en sonda sayılıp toplam sınırı aşması iki regresyonla (adet/bayt) yeniden üretildi ve düzeltildi. Silinen taslaklar bütçeyi tüketmez; sınırlar artırılmadı.
