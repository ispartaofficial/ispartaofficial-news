# Bağımsız işletim izlemesi ve günlük yedek

30 Ekim 2026. Seferihisar üretimindeki `ops_watch.py` ve `backup_history.py`
(`32d169e`) Isparta'ya uyarlandı; köken `engine-provenance.json` içindedir.
Seferihisar deposu, anahtarı veya veritabanı kullanılmaz.

## İzleme (`operations-watch.yml`)

Saatte bir, ayrıca araştırma, hava, eczane veya yedek işi başarısız bittiğinde
çalışır. Herkese açık `data.json` panelini ve GitHub Actions geçmişini okur;
paylaşım yapmaz, durum dalına yazmaz. Sorun kümesi değiştiğinde tek bir GitHub
issue'su açar veya günceller ve `ispartaofficial` hesabına atar; sorunlar
geçince kapatır. Kullanıcının kendi issue'larına dokunmaz.

| Kod | Ne zaman |
|---|---|
| `research_stale` | Saat 10:00–24:00 arasında son tamamlanmış araştırma 3 saatten eski; gece 11 saatten eski. |
| `research_failed` | Ana daldaki son iki tamamlanmış araştırma turu başarısız (yayın işi bu turun içindedir). |
| `source_coverage_drop` | Kaynakların en az %40'ı `failed` veya `partial`. `empty` hata sayılmaz. |
| `weather_missing` | 09:20'den sonra üretilmiş panelde bugünün hava story'si yayımlanmış değil. |
| `pharmacy_missing` | 18:20'den sonra üretilmiş panelde bugünün eczane story'si yayımlanmış değil. |
| `unresolved_delivery` | Sonucu belirsiz Instagram/Facebook teslimi var. Gönderilmediği kesin olan iddia (`not_sent`) sayılmaz; aşağıya bakın. |
| `delivery_audit_failed` | Son 24 saatte yayın sonrası okuma kontrolü başarısız. |
| `backup_missing` | Son iki günde başarılı yedek işi yok. |
| `source_silent` | Daha önce kayıt vermiş bir kaynak şu an `empty`/`failed` ve en yeni kendi kaydı (`first_seen`) 72 saatten eski. Issue kaynak kimliğini, durumunu ve son yeni kayıt tarihini listeler. |
| `panel_unreachable` / `invalid_panel` | Panel okunamadı veya doğrulanamadı. |

Isparta'ya özgü iki fark vardır. Araştırma 07:20–23:50 arasında çalışır ve
GitHub bazı turları atlar (25–30 Ekim'de 157 dakikaya varan boşluk); bu yüzden
gündüz eşiği 3 saattir, gece yalnız sabah turlarının hiç gelmemesi uyarı verir.
Panel yalnız araştırma dağıtımıyla yenilendiği için hava ve eczane, ancak pencere
kapandıktan sonra üretilmiş bir panelde değerlendirilir; eski panel ayrıca
`research_stale` ile yakalanır.

### Sessiz kaynak

Araştırma dışa aktarımı panele `quiet_sources` listesini yazar. `last_seen`
kullanılmaz; başka kaynak aynı kaydı yeniden bildirince de ilerler. `partial`
kaynak okuma yapıyordur, sayılmaz; süreli istek (`requested_until`) dışarıda
kalır. `config/research-sources.json` içinde seyrek kaynak `quiet_after_hours`,
aşılamayan bilinen engel `quiet_acknowledged` (gerekçe metni) alabilir;
onaylanan kaynak panelde görünür ama uyarı vermez. 30 Ekim verisiyle ilk liste
`bubilet-isparta` (okunamıyor/güncel değil, son yeni kayıt 22 Ekim).

`failed` tek başına yetmez: kaynak son 4 tamamlanmış turun her birinin
`runs.errors` kaydında da bulunmalıdır (Isparta'da bu kayıt `empty` ve
`partial` kaynakları da `source_not_current` koduyla içerir). 25–30 Ekim'deki 100
turda tekil hatalar en fazla 2 tur sürdü, kalıcı engeller 32–100 tur. Kural
olmadan uyarı her ağ kesintisinde açılıp kapanır ve her değişiklik issue'ya
yorum yazar. `bubilet-isparta` aynı gün `quiet_acknowledged` aldı: Seferihisar'da
aynı alan adı 27 Ekim'den beri bulut sunucularına HTTP 403 dönüyor; Isparta
okuyucusu aynı dönemden beri okunamıyor, proje kimliğiyle yerel okuma 200. Isparta
motoru bulut hata kodunu ayrıca saklamadığı için kod doğrudan görülmedi.
3 Kasım'dan beri `failed` kaynak `runs.errors` içinde liste okumasının kodunu
taşır (`source_http_403`, `source_timeout`, `source_reader_failed` gibi sabit
kimlikler; adres yok); `empty` kaynak `source_not_current` kalır. Gerekçe:
31 Ekim'de eklenen Etkinlik.io ve AEDAŞ okuyucuları bulutta hiç okunamadı,
yerelde ikisi de okunuyor (13 ve 14 kayıt); engel mi okuyucu hatası mı ayrılamıyordu.
Merge sonrası ilk tur (3 Kasım 19:55) Etkinlik.io için `source_http_403`, AEDAŞ için
`source_timeout` yazdı; ikisi de `quiet_acknowledged` aldı ve açık kaldı.

### Durum dalına yazma ve gönderilmemiş iddia

4 Kasım 2026, 12:30–14:20 TR: GitHub iki şehir deposunda da `automation-state`
yazmalarını reddetti; kira (`--force-with-lease`) başı değişmemişti, yani
eşzamanlı yazan yoktu. Tek denemeli yazma, `Isparta Yollarında Güvenlik Önlemi`
iddiasını Meta konteyneri oluşturulduktan sonra, `media_publish` çağrılmadan
`publishing` durumunda bıraktı. İddia o günün bir haber hakkını aldı ve
`unresolved_delivery` uyarısı kendiliğinden kapanamaz oldu.

- `state_git.persist` yazmayı 3, 10 ve 30 saniye arayla en çok dört kez dener.
  Her ret sonrası uzak baş okunur: bizim commit oradaysa önceki deneme yazılmış
  demektir ve tekrar edilmez; baş değişmişse eşzamanlı yazan vardır ve iş durur.
  `ls-remote` ve `fetch` okumaları da aynı aralıklarla tekrarlanır.
- `media_publish` öncesindeki bir kayıt yazılamazsa iddia `uncertain` ve
  `delivery_error: state_unsaved` olur, iş yine kırmızı biter; son
  `persist` adımı bu durumu saklar.
- Yayın işi her turda 25 saatten eski, `media_id` almamış konteynerli iddialar
  için Meta'dan yalnız `status_code` okur. Meta kullanılmamış konteyneri 24
  saatte `EXPIRED` yapar; bu yanıt gönderinin çıkmadığını kanıtlar ve iddia
  `delivery_error: container_expired` olur. `PUBLISHED`, `FINISHED` veya hata
  yanıtında hiçbir şey değişmez.
- Konteyneri olmayan, `state_unsaved` veya `container_expired` iddia panelde
  `not_sent` sayılır, `unresolved` sayılmaz. Hakkını korur, asla yeniden
  gönderilmez. Seferihisar'daki `never_sent` kuralı genişletilerek uyarlandı.

### Kart dağıtımını beklemek hata değildir

6 Kasım 2026, 17:08–20:58 TR: üç yayın turu `visual_review_stale`, 17:08 eczane
turu `media_not_deployed` ile kırmızı bitti ve her biri sahibine e-posta attı.
Hepsinde araştırma turu kartı yeniden üretmiş, Pages yeni kartı henüz
sunmuyordu; sonraki tur yayımladı (eczane 17:31). Bu yüzden:

- Yayın işi (`production publish`) yalnız `media_not_deployed`,
  `visual_review_missing` veya `visual_review_stale` bekliyorsa yeşil biter
  (`operations.alarming`). Aynı bekleme, arada temiz bir kontrol olmadan 2 saat
  sürerse iş yine kırmızı biter. Diğer bütün başarısız durumlar ilk turda
  kırmızıdır.
- Hava ve eczane işleri `media_not_deployed` için kırmızı bitmez; pencere
  içindeki sonraki tur yeniden dener. Gün kaçarsa `weather_missing` /
  `pharmacy_missing` uyarısı bir kez açılır.

## Yedek (`state-backup.yml`)

Her gün 03:43 TR'de ve bu dosyalar değiştiğinde çalışır. `automation-state`
dalının son commit'indeki `platform.sqlite` dosyasını salt okunur kopyalar,
bütünlük kontrolüyle zip arşivine yazar ve geçici bir dizinde geri yükleyerek
doğrular. Bir önceki günün yedeği de aynı şekilde geri yüklenir. Arşiv 7 gün
Actions artifact'i olarak tutulur. Canlı durum hiçbir zaman değiştirilmez; bu,
sağlayıcıdan bağımsız bir yedek değildir.

Testler: `tests/engine/test_operations_watch.py`. Yeşil iş, uyarının sahibine
telefonda ulaştığının kanıtı değildir; bildirim ayarı GitHub hesabındadır.
