# Isparta üretim akışı — 23 Ekim 2026

Kullanıcı kalan işleri tamamlayıp sistemi hazır etmeyi onayladı. Mevcut bağımsız
Instagram Login hesabı `@ispartaofficial` / `17841403171726739` ve Cloudflare
IspartaOfficial hesabı kullanılır. Başka sayfanın kimliği, anahtarı veya durumu
aktarılmaz. Araştırmanın başarılı olması sosyal teslim kanıtı değildir.

## Yayın kapıları ve çalışma

`config/runtime.json` yayın/bağlantı kapılarına ek olarak GitHub'da
`INSTAGRAM_PUBLISH_ENABLED=true` ve `META_TESTS_COMPLETED=true` gerekir.
İkinci değişken miras alınmış ön kontrol kapısıdır; gerçek teslim iddiası değildir.
Yayın yalnız güvenilir main çalışmasında `instagram-production` ortamını kullanır.
Araştırma işine Instagram anahtarı verilmez. Ortak concurrency grubu araştırma,
eczane ve normal yayın durumunun çakışmasını önler.

Araştırma 07:20–23:50 arasında saatte iki kez planlanır. Mevcut motorun
08:30, 12:30 ve 18:30 başlayan birer saatlik pencerelerinde, günde en fazla iki
gönderi ve her birinin ilk eşleşen story'si yayımlanır. Bu üç pencere üç gönderi
demek değildir. GitHub başlangıcı geciktirebilir; pencere geçince eski kuyruk
topluca yayımlanmaz. Nöbetçi eczane listesi 17:00 hedefli ayrı günlük story'dir.
Kaynağın gerçek nöbet tarihi/aralığı, merkez filtresi ve dağıtılmış görsel kontrol
edilir. Başarısız veya belirsiz teslim otomatik tekrar gönderilmez.

Kullanıcının ilk canlı teslimi doğrulama talebi için araştırmanın elle başlatılmasında
`first_post_id` ile tek bir incelenmiş gerçek içerik seçilebilir. Bu yol yalnız
ilk parent kimliğine izin verir; başka bir yayın kaydı varsa yeni bir ilk gönderi
oluşturamaz. Günlük sınır, kaynak/tarih, görsel ve belirsiz teslim korumaları aynıdır.
Normal planlı işlerde bu alan boştur; takvim değiştirilmez.

## Bağlantı sürekliliği

Meta'nın resmî Instagram Login yenileme uç noktası kullanılır. İlk gözlemden
sonra 26 saat beklenir; böylece en az 24 saat anahtar yaşı koşulu korunur.
Başarılı yenilemeden sonra yedi günde bir yenilenir. Geçici hata en erken ertesi
gün yeniden denenir; bilinmeyen süre uydurulmaz. Yanıttaki `expires_in` gerçek
bitiş zamanına çevrilir. Kimlik doğrulaması veya süre kontrolü başarısızsa yayın
yapılmaz. Mevcut günün ilk yenilemesi, yaş koşulu dolmadan gerçekleşmiş sayılamaz.

Asıl `INSTAGRAM_ACCESS_TOKEN` GitHub environment Secrets içinde kalır. Bu yüksek
entropili değer HKDF-SHA256 ile hesap/depo/rota bağlamına bağlı AES-256-GCM
şifreleme anahtarı türetmek için de kullanılır. Yenilenen değer ve süresi birlikte
rastgele nonce ile şifrelenir; `automation-state` içindeki `credential_capsules`
tablosuna yalnız doğrulanabilir şifreli BLOB yazılır. Açık değer hiçbir zaman
SQLite'a, Pages'e, rapora veya loga girmez. Kapsül Pages dışa aktarımına dahil
değildir. Güncel kapsül kalıcı olarak saklanmadan yeni anahtarla yayın yapılmaz.

Araştırma kapsülü çözemeden olduğu gibi korur. Yayın, eczane ve GET kontrolü
aynı kapsülü kullanır. İlk secret API açısından süresi dolduktan sonra da yalnız
şifre çözme kökü olarak kalır; API'ye kapsülden çözülen güncel değer gönderilir.
Secret'ın değiştirilmesi, iptal edilmesi, hesabın izinlerinin kaldırılması veya
Meta'nın güvenlik kısıtlaması otomatik olarak çözülemez. Okunamayan kapsülde eski
anahtara sessiz dönüş yapılmaz; bağlantı durur ve kontrollü hata verir.

Resmî koşullar: https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/business-login

## Teslimin gözlenmesi

Gönderi/story için API'nin döndürdüğü kimlikler kalıcı kayıt edilir. Sonraki
normal çalışmada Instagram Login hostundan yalnız GET ile hesap kimliği,
gönderinin açıklaması/zamanı ve aktif story listesinde kayıtlı kimliğin üyeliği
kontrol edilir. En az üç dakika yayılma süresi tanınır. Bu kontrol tekrar yayın
yapmaz; bir API gözlemi platform ekranında görsel incelendiği iddiası değildir.

## Dış erişim sınırı

Kaynakların anlık sağlığı canlı Pages ve araştırma raporundadır. 23 Ekim 16:59
turunda 29 okuyucudan 27'si okundu; SDÜ SKS ve Yenişarbademli Kaymakamlığı
okunamadı. Önceki turda başarısız kaynakların çoğu normal planlı turda düzeldi.
Mevcut sınırlı bağlantı denemeleri korunur; robots/TLS kontrolü veya kuruma ait
erişim engeli aşılmaz. Bir kaynaktaki hata bütün diğer kaynakları durdurmaz,
fakat o kaynaktaki eski hazırlığa yeniden yayın onayı vermez.

Facebook bağlantısı, ölçüme dayalı öğrenme ve yeni kaynakları otomatik açma bu
etkinleştirmenin parçası değildir. Seferihisar'ın ayrı eczane kaynağı sorunu
Isparta'nın çalışan eczane okuyucusuyla karıştırılmaz.
