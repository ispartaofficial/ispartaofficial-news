# Isparta kaynak kapsamı

22 Ekim 2026. Kapsam bütün ilçelerden yerel haber ve kamu duyuruları ile üniversite/kültür sanat içerikleridir. Araştırma, haber yazımı ve sosyal yayın ayrı aşamalardır. Bu sürüm sosyal paylaşım yapmaz.

## İncelenmiş içerik okuyucuları: 29

| Grup | Kaynaklar |
|---|---|
| Yerel basın | Bomba32, Haber32, Kanal32, Ajans32 |
| İl kaynakları | Isparta Belediyesi, Isparta Valiliği, Isparta İl Kültür ve Turizm Müdürlüğü |
| Üniversite | SDÜ takvimi, SDÜ SKS duyuruları; ISUBÜ takvimi, SKS, Toplumsal Katkı ve resmî etkinlik duyuru arşivi |
| Biletli etkinlik | Bubilet Isparta |
| Kaymakamlık | Aksu, Atabey, Eğirdir, Gelendost, Gönen, Keçiborlu, Senirkent, Sütçüler, Şarkikaraağaç, Uluborlu, Yalvaç, Yenişarbademli |
| İlçe belediyesi | Isparta Gönen Belediyesi, Keçiborlu Belediyesi, Senirkent Belediyesi |

Yerel basın listelerinde her turda en yeni 12 haber bağlantısı okunur (genel üst sınır 12). 29 Ekim 2026 durum verisinde Bomba32 haberleri en yeni dört bağlantı içinde çoğunlukla 0–2 saat kalıyor, ardından `not_reobserved_current_run` ile bekliyordu. Aynı haberi başka incelenmiş kaynak o turda gösterirse ilk kayıt yeniden görülmüş sayılır; yalnız bu bekletme kalkar, içerik ve doğrulama bekletmeleri korunur.

İlçe portallarında hem haber hem duyuru bağlantıları sınırlı sayıda okunur. Uzun haber listesi duyuruları gizlemez. Duyuru yükleme tarihi, ihale/başvuru son tarihi veya hizmetin geçerlilik süresi sayılmaz. Belgenin içeriği henüz doğrulanmamışsa duyuru bekletilir. Eski resmî haberler, aynı site yeni tarihle açıldı diye güncellenmiş sayılmaz.

Aksu ve Gönen başka illerde de bulunduğundan resmî alan adı ile makalenin/liste sayfasının kurum kimliği birlikte kontrol edilir. Gönen Kaymakamlığı için `ispartagonen.gov.tr`, Isparta Gönen Belediyesi için e-Devlet'te kayıtlı `gonen.bel.tr` kullanılır. `gonen.gov.tr` Balıkesir kaynağıdır ve bu listeye alınmaz. Kurumun Isparta adresi, başka ildeki bir etkinliği veya ulusal duyuruyu kendiliğinden yerel yapmaz.

Üniversite arşivinde özgün yayım tarihi ve açıkça etiketlenmiş etkinlik günü/saat/mekân ayrı okunur. Tarih yılı veya saat aralığı belirsizse başlangıç uydurulmaz. Üniversite dışı şehirdeki programlar yerel etkinlik sayılmaz. Ücretsiz servis, etkinliğin ücretsiz olduğu anlamına gelmez. Afişteki yazı okunmadıysa okunmuş gibi kabul edilmez.

## Ayrı topluluk keşfi

ISUBÜ'nün resmî öğrenci toplulukları dizini düzenli araştırmaya eklenmiştir. Dizinin incelenen örneğinde 74 topluluk vardır. Yalnız topluluk adları ve resmî dizin adresi raporlanır; öğrenci başkanı/danışman kişi adları dışa aktarılmaz. Bu kayıtlar etkinlik veya haber değildir ve içerik havuzuna eklenmez. Topluluk sayısı zamanla değişebilir.

SDÜ topluluk dizini, SKS alan adındaki zaman aşımı nedeniyle doğrulanmış keşif kanalı sayılmaz. Topluluk Instagram hesapları veya diğer yerel Instagram sayfaları henüz ayrı bir Isparta Meta bağlantısıyla okunmamaktadır.

## Etkinleştirilmeyen kaynak adayları

- Aksu Belediyesi için Antalya'daki `aksu.bel.tr` kullanılmaz. Isparta kaynağı adayı `aksubelediyesi.bel.tr` güvenli otomatik okuma kontrolünde HTTP 404 verdi.
- Atabey, Sütçüler, Şarkikaraağaç, Uluborlu ve Yenişarbademli belediye adaylarının robots/sayfa okuma zinciri HTTP 404 ile tamamlanamadı. Bu, belediyenin sitesinin tarayıcıda hiç açılmadığı iddiası değildir; üretim okuyucusu için gerekli erişim doğrulanmadı.
- Gelendost belediye alan adı adayı DNS/URL doğrulamasını geçemedi; çalışan belediye kaynağı sayılmadı.
- Yalvaç Belediyesi adayında robots yönlendirmesi onaylanan alan dışına çıktı; güvenlik kontrolü korunarak okuyucu kapalı tutuldu.
- Eğirdir Belediyesi ana sayfası okunabildi; örnek haber ayrıntısında başlık ve özgün tarih alanları boştu. İlgisiz sayfa metni doğru haber gövdesiymiş gibi eklenmedi.

Kaynak adaylarının adres ve teknik sonuçları `config/source-candidates.json` içindedir. Bu listede bulunmak, kaynağın araştırmada etkin veya bulutta sağlıklı olduğu anlamına gelmez. Sertifika/robots güvenliği, erişim engelleri veya oturum gereksinimi aşılmaz.

## Çalışma ve kanıt

İçerik okuyucuları `config/research-sources.json` içinde, dizin keşfi aynı dosyanın `discovery_sources` bölümündedir. Rapor içerik sağlığını `source_health`, dizin sağlığını `discovery_health` altında ayrı tutar. `parsed`, kaynağın o turda kayıt verdiğini; `partial`, ayrıntıların bir kısmında hata olduğunu; `failed`, okuma/ayrıştırmanın tamamlanamadığını gösterir. Eksik alanları nedeniyle bekletilen içerikler ayrıca gerekçelendirilir.

Yayıncının kendi bölüm etiketi (JSON-LD `articleSection` veya breadcrumb) reklam, sponsorlu, tanıtım, ilan ya da basın bülteni ise makale `advertorial_section` ile bekletilir. 29 Ekim 2026'da Bomba32'nin "Reklam Manşet20" bölümündeki bir firma tanıtımı haber olarak yayımlanmıştı. Gövdedeki tanıtım dili tek başına ölçüt değildir; makalenin kendi başlığına giden breadcrumb bağlantısı bölüm sayılmaz.

Kod/yerel test başarısı ile GitHub bulut erişimi farklı kanıtlardır. Kesin güncel kaynak durumu ilgili Actions çalışmasının indirilebilir `research.json` dosyasından alınmalıdır. Özellikle SDÜ SKS yerelde okunabilse de önceki bulut çalışmalarında zaman aşımı vermiştir; sonraki turda gerçek okuma kanıtı olmadan sağlıklı sayılmaz.

Araştırma en fazla 40 içerik kaynağı ve dört ayrı keşif kanalı kabul eder. Her kaynağın ayrıntı sayısı ve toplam iş süresi sınırlıdır. Mevcut GitHub araştırması iki saatlik gündüz/akşam planında çalışır; başlangıç gecikebilir. Yayına hazır veya yayımlanmış kayıt sayısı bu aşamada daima sıfırdır.
