# IspartaOfficial — Claude Code devir belgesi

Tarih: 29 Ekim 2026 (Europe/Istanbul). Ana depo: https://github.com/ispartaofficial/ispartaofficial-news
Devam dalı: **`codex/restore-frozen-visuals`**. Açık PR: https://github.com/ispartaofficial/ispartaofficial-news/pull/22
Karşı proje: https://github.com/ntekintr/seferihisarofficial-news (kendi HANDOFF.md dosyası var).

## Mevcut durum ve amaç

Isparta merkez ve tüm ilçeler için yerel haber, üniversite yaşamı, konser/festival/tiyatro ve hizmet duyuruları. Kullanıcı mevcut hesabın yaklaşık 35 bin takipçili ve dört yıllık olduğunu belirtti; bu bir güncel ölçüm değildir. `@ispartaofficial` gül logosu, mürdüm/füşya/açık zemin korunur. Eczane yalnız merkez ve merkez mahalleleri; kırmızı E işareti. Hava kartı Isparta kimlikli, Seferihisar salyangozu taşınmaz.

İncelenen main: `86c2304e1d04b0518d8998b1d1159163cb040aa2` (PR #21). PR #21 birleşmiş/kapalıdır; devam yeri değildir. PR #22 başlangıç remote head'i `a955e03ef13419922f751d6bc6519d8534810691`; eski CI 40733948487 test/native başarılıydı. Bu devir PR #22'ye henüz gönderilmemiş capacity/prune düzeltmelerini ekler; eski yeşil CI yeni head için kanıt değildir. **PR #22 devrin parçası olarak merge edilmeyecek.**

`config/runtime.json`: publishing/meta/weather/source_photos/illustration_generation/pharmacy açık; Facebook, learning ve source_discovery_activation kapalı. GitHub environment değişkenleri ayrıca kapıdır; config tek başına güncel izin kanıtı değildir. README, engine-port.md ve live-readiness.md içindeki “kapalı”, “2 gönderi” gibi eski tarihli kurulum ifadeleri güncel config/politika ile çelişir. Bunları canlı ayar olarak kullanma.

29 Ekim salt okunur Actions gözlemi: research 40826410541 başarılı, main hâlâ yukarıdaki SHA. Hava job'ları başarılı görünse de `outside_window`/`already_published` başarı dönebilir; bu devirde 29 Ekim gerçek teslimi ayrıca doğrulanmadı.

## Isparta mimarisi, bağlantılar ve kaynaklar

Seferihisar `7a862a9b98bf4c63120d550b30406ba961397d7d` motoru PR #6 ile `news_engine/` altında bağımsız uyarlandı; köken `docs/engine-provenance.json`. `isparta/research.py`, readers/district_readers/scope_readers/fetch kaynak okuyucuları; `isparta/runtime.py` tam kaynak → ortak motor/markalı çıktı; `isparta/production.py` yayın/hava/eczane/check giriş noktasıdır. Kamuya açık 600 karakterlik rapor alıntısını tam makale kanıtı yerine tekrar içeri alma.

29 tanımlı içerik okuyucusu: Bomba32/Haber32/Kanal32/Ajans32; belediye/valilik/kültür; SDÜ ve ISUBÜ kanalları; 12 ilçe kaymakamlığı; üç ilçe belediyesi; Bubilet. ISUBÜ topluluk dizini ayrı keşif kanalıdır. Yapılandırılmış okuyucu sayısı her tur sağlıklı kaynak sayısı değildir. Ayrıntılar `config/research-sources.json`, `docs/source-coverage.md`.

Bağımsız Instagram Login ve bağımsız Cloudflare hesabı. Facebook sayfası/teslimi kurulmadı. `isparta/credentials.py` mevcut anahtarı resmî yenileme yoluyla yeniler; ilk gözlemden sonra 26 saat, başarıdan sonra yedi gün, geçici hatada ertesi gün. `cryptography`, HKDF-SHA256/AES-GCM kapsülü `credential_capsules` içinde tutar. Ana environment secret kapsül şifreleme köküdür; bunu düşünmeden değiştirmek kapsülü okunamaz yapar. Araştırma şifreli BLOB'u çözemeden korur. Sırları diğer şehre kopyalama.

`research.yml` cron `20,50 4-20 * * *` UTC (07:20–23:50 TR), prepare/persist/Pages ve yetkili main publish. `weather-story.yml`: 08:00 hedefi; `pharmacy-story.yml`: 17:00 hedefi; `connection.yml`: GET kontrolü; `ci.yml`: test + gerçek OCR/model. Üretim concurrency `isparta-production`. Kaynak hazırlık işi Instagram secret almaz. Kapsül korunmadan SQLite değiştirilmez.

## Son tamamlanan ve açık işler

PR #17–21: görselsiz yeni yayın kapısı, kaynak resim hakkının doğru sayılması, tekrar beklemesi, dokuz stok sahne, EXIF 0/1 desteği (2–8 reddi korunur), tam seans afişi ve iki Bomba32 kaynağına kesin kimlik/hash bağlı editör incelemesi. Başarısız kekik stok ve genel yan panel OCR gevşetmesi üretime alınmadı.

Açık PR #22: tek kayıp görsel `64b0870d8d0714a1fd8c94a0` pinned 26 Ekim state `8d4c43157a99f95705163b1d66a82776e9633c1f` içinden geri alınacak. Eski 14 IG iddiası/2 hava/2 eczane ve 28 Ekim kontrolündeki daha yeni donmuş satırlar kıyas tabanlarıdır; bugünkü toplam diye sunma. Dört owning post manifestte sabit. Fotoğrafın web arşivinde eksik olması Instagram'daki eski gönderinin silindiği anlamına gelmez.

Devir öncesi yerel commitler: `8f69a81` ilk onarım (remote dört UI commitiyle eşdeğer dosyalar), `e7ff9e9` cache sınırı, `3778e7f` frozen-first prune. Remote/yerel commit kimlikleri farklıdır; içerik ağacı/hash karşılaştır, kör cherry-pick veya force-push yapma. Bu devir kod farklarını mevcut remote dalda yeni commitlerle saklar.

Önceki başlangıç suite 718 passed/9 skipped; son iki arşiv/bütçe dosyası 18 passed. Son pending kodun tam Linux/native CI ve canlı onarım kanıtı ayrıca gereklidir. Isparta yazımı connector'da 403 verdiği için yetkili GitHub tarayıcı oturumu kullanıldı; yeni erişim anahtarı oluşturulmadı.

## Öncelikli kalanlar

1. PR #22 final diff ve yeni CI; özellikle fixed archive/owner checks, kapasite ve frozen-first prune. Kullanıcı onayıyla merge edildikten sonra tek normal dağıtımı doğrula.
2. Kayıp tarihsel JPEG'in gerçekten aynı byte'larla geri geldiğini, tüm eski SQL alanlarının ve credential_capsules BLOB'larının değişmediğini doğrula. Hazır kart ve teslimi ayır.
3. Son görsel bekleyenleri normal durum verisinden sınıflandır. 28 Ekim “Geleceğim Meslekte” kaydı source_binding ve olası saat tutarsızlığıyla bekliyordu; eski bulguyu bugünkü sonuç sayma, afiş/saat uydurma.
4. Eski README/kurulum notlarını güncel hale getir; bu devir işlevsel ayar değiştirmez. Öğrenme/Facebook/yeni kaynak aktivasyonu şu an eksik bağlantıdır, yeni özellik işine ayrıca karar verilir.

## Devir talimatı ve güvenlik sınırı

29 Ekim 2026: kullanıcı projeyi Claude Code'a devretti. Bu devir yeni özellik geliştirme veya canlıya birleştirme değildir. Çalışan özellikleri koru, projeyi sıfırdan kurma, gereksiz bağımlılık ekleme. Kullanıcının son talimatı gereği riskli canlı değişikliklerden önce onay al. Eski sohbetin sınırsız yetki ifadelerini yeni riskli işlemlere genel izin sayma.

Başlangıçta `AGENTS.md`, bu belge ve aşağıdaki ilgili alt sistem belgelerini oku. Kod, config ve tarihli kanıt; eski README varsayımlarından daha günceldir. Sırlar, tam özel loglar, ham oturumlar ve tokenlar bu dosyada yoktur. Ortam değişkeni adları değer değildir. Yeni sağlayıcı/ücret/kota/izin/token üretme; robots veya TLS engelini aşma.

## Kullanıcı tarafından kesinleştirilen ürün kuralları

- Aynı motoru kullanan iki ayrı hesap/depo vardır. Şehirler arasında logo, sır, veritabanı veya yayın kimliği kopyalanmaz. Bu bir monorepo ya da otomatik senkronize ortak paket değildir.
- Her hesapta günde en fazla 3 haber gönderisi + bunların ilk eşleşen 3 story'si. Hava ve nöbetçi eczane story'leri bu sayıya EK ve ayrı günlük iddialardır.
- Aynı gün 20:00–22:59'da aslen yayımlanan ve ilk kez o akşam bulunan yeni haber için en fazla 4. gönderi + eşleşen story mümkündür. İlk revizyon, tazelik ve diğer kapılar korunur; 23:30 sonrası telafi/ertesi güne toplu yayın yoktur. Sayı kaliteyi geçmeyen içeriği doldurma hedefi değildir.
- Hava 08:00, eczane 17:00 Türkiye saati hedeflidir; aynı saat içindeki sınırlı yedekler ve günlük tek iddia vardır. GitHub cron gecikebilir, dakikası dakikasına veya bir ay kesintisiz garanti yoktur.
- Gerçek makale/etkinliğe ait fotoğraf veya afiş önceliklidir. Yoksa denetlenmiş ilgili gerçekçi sahne/stok kullanılır. Alakasız şehir, trafik, salon fotoğrafı eklenmez. Model benzerliği gerçek kişi/yer/olay kimliğini kanıtlamaz. Gerçek olaya dair uydurma fotoğraf üretme.
- 26 Ekim görsel öncelikli kuralı eski bilgi kartı yedeği notlarını günceller: yeni haber gönderisinin doğrulanmış kapağı yoksa `awaiting_content_visual` olarak bekler. Her gelecekteki habere görsel bulunacağı garantisi yoktur.
- Logo ve marka şeritleri sabit. Kaynak adı/adresi açıklamada; kart üzerinde kaynak satırı yok. Otomatik AI notu eklenmez. Yaklaşık 5 ilgili küçük harfli hashtag; keşfet garantisi verilmez.
- “Detaylar açıklamada.” ilk kartta içerik altındadır, bunun için ikinci boş slayt yok. Başlık, gövde, tarih, mekân, ücret ayrı alanlardır; tekrar başlık, kaynak hesabının “biz” dili, bozuk emoji kutuları ve kesilmiş metin engellenir.
- Canan Tutal ile Hatha Yoga, yeni Seferihisar gönderi/story/seçkilerinden çıkarılmıştır. Geçmiş yayınlar yeniden yazılmaz.
- Haber yaşı asıl kaynak zamanından en fazla 48 saat; last_seen haberi gençleştirmez. Etkinlik yükleme tarihi etkinlik günü değildir. Geçmiş/iptal/çelişkili tarih, bilinmeyen son-gün saati ve doğrulanmamış uyarı geçerliliği bekler. Ücret/organizatör/yer tahmin edilmez.

## Mimari ve veri akışı

Kaynak tanımları → sınırlı robots/TLS uyumlu okuma → tarih/konum/kaynak doğrulama → SQLite içerik kimliği ve revizyon → editoryal seçim → gerçek kaynak fotoğrafı/uygun sahne → OCR ve konu/kırpma kontrolü → Pillow kart ve açıklama → JPEG özetiyle bağlı `visual_review` → güvenli Pages dağıtımı → yayın anında tekrar doğrulama → kalıcı Meta iddiası → API teslimi ve GET gözlemi.

`store.py` kalıcı kayıtları, `schedule.py` ve `publication_policy.py` seçim/zamanı, `timeliness.py` geçerliliği, `editorial_voice.py`/`text_quality.py` metni, `render.py`/`card_layout.py` yerleşimi, `source_photos.py` kaynak resmini, `illustrations.py`/`editorial_stock.py` üretim ve stoku, `visual_match.py`/`image_safety.py` resim kontrolünü, `visual_gate.py` gerçek dosya/manifest bağını yönetir. `security.py` kamuya çıkabilecek şema/veriyi sınırlar; bu kontrolü gevşetme.

`automation-state` dalındaki `platform.sqlite` kalıcı durumdur; Actions cache/artifact kalıcı veritabanı yerine geçmez. `state_git.py` doğrulanmış geri yükleme/kalıcılaştırmayı yapar. Aynı depo üretim işleri ortak concurrency kilidini kullanır; bütün SQLite yazıldığı için kilidi düşünmeden ayırma. Veri dalını kaynak kod dalına merge etme veya eski SQLite ile canlıyı ezme.

`posts` durumları prepared/blocked_source/expired/superseded ile published/publishing/uncertain ayrılır. Başlamış ve belirsiz iddia bütçeyi tüketir; otomatik tekrar gönderilmez. `facebook_deliveries`, `weather_stories`, `pharmacy_stories` ayrı teslim tablolarıdır. Aynı kimlik veya revizyon dışındaki kart içerik/görsel tekrarı da kontrol edilir.

Hazır kart ≠ yeşil workflow ≠ Meta'nın kalıcı API teslim kaydı ≠ doğrudan Instagram/Facebook ekranında görülmüş içerik. Her raporda hangi kanıtın mevcut olduğunu söyle. Eski bütün donmuş SQL satırlarını TÜM sütunlarla karşılaştır; yalnız ilk birkaç kayıt yeterli değildir. Meta kimlikleri, caption, payload ve medya yollarını koru. Eski URL'nin 200 dönmesi doğru piksellerin kaldığını kanıtlamaz; JPEG hash karşılaştır.

## Teknolojiler ve servisler

Python >=3.11 (bulut 3.12), SQLite, Requests, BeautifulSoup, Pillow, pytest, PyYAML; statik HTML/CSS/JS Pages paneli. OCR Tesseract (tur/eng), konu kontrolü pinned CLIP/Transformers 4.57.1, CPU Torch 2.14.1 ve model cache. Bağımlılıkların kesin sürüm ve kurulum komutlarını `pyproject.toml`/CI'dan al. Bu devir bağımlılık eklemez.

Cloudflare Workers AI Flux `@cf/black-forest-labs/flux-1-schnell` görsel üretimi; günlük/tur sınırı 20/2 korunur. Dokuz hash/tarif bağlı markasız stok sahne depoda paketlenmiştir; bilgisayar veya sohbet açık olmadan kullanılabilir. Geçersiz kekik stok resmi çıkarılmıştır. Her stok gerçek olay fotoğrafı değildir. Kaynak/başlık/tarih/seans bağı, JPEG temizleme, OCR ve görsel konu kapıları korunur. Başarısız iki deneme veya kota dolması “üretilmiş” değildir.

GitHub Actions, Pages, repository/environment Secrets ve Meta Graph API kullanılır. Cloudflare/Meta anahtar DEĞERLERİ bu dosyaya veya açık loga yazılmaz. GitHub commit kimliği, PR numarası ve kamuya açık repo URL'si sır değildir.

## Bilinen hata zinciri ve son düzeltmeler

1. Uyumsuz fotoğraflar (toplantıya trafik, sele kuru yol, kesintiye salon): kategori yerine kaynak kimliği + konu + gerçek kırpma/manifest kontrolü getirildi.
2. Eski etkinlik/uyarı ve tekrar kart: ham zaman, geçerlilik, revizyon, donmuş kart ve günlük iddia korumaları getirildi.
3. Aynı reddedilen resimlerin her turu tüketmesi: kaynak/revizyon/zamanla sınırlı bekleme, dosya hakkının yalnız gerçek dosyalara harcanması ve eksik kapak önceliği getirildi. Genel kota artırılmadı.
4. Afiş OCR/model reddi: genel eşikler düşürülmedi. Yalnız tam kimlik/piksel bağıyla incelenmiş istisna veya uygun genel konu sahnesi var. Başlık/tarih/URL/piksel değişince eski onay kullanılamaz.
5. Tarihsel resim önbelleği budanmıştı. Donmuş anahtar koruması gelecekteki silmeyi önler; zaten kaybolanı tek başına geri getirmez. `historical_visuals.py` pinned Git state snapshot SHA + SQLite SHA256 + tam satır fingerprint + değişmemiş owning post + gözlenen mevcut cache koşuluyla yalnız listelenen satırları geri getirir. Bütün veritabanını geri sarmaz; yeni/başka sahip varsa atlar; ikinci çağrı no-op.
6. Onarım 80 hazır resim/12 MiB sınırını aşabiliyordu. Yer varsa yalnız kullanılmayan/expired/superseded taslak önbelleği temizlenir; aktif taslak/yayın korunur. Yer yetmezse onarım atlanır, normal restore bozulmaz.
7. Normal prune yeni taslakları önce sayıp eski korunan resimleri sona bırakınca toplam sınır tekrar aşılabiliyordu. Son düzeltme önce donmuş resimlerin bütçesini ayırır, taslakları kalan alana alır. Adet ve bayt regresyonları önce kırıldı, düzeltmeden sonra geçti. Limit yükseltilmedi.

## Test ve güvenli devam prosedürü

İzole sanal ortamda repo kökünden `python -m pip install -e ".[test]"`, ardından `python -m pytest -q`. Görsel native testler ayrıca CI'daki Torch/Tesseract/model kurulumunu ve `RUN_VISUAL_NATIVE=true` ister; yerelde skipped olan native testi geçti sayma. Windows/Linux font farkı nedeniyle yeni yerel render hash'i eski Linux hash'iyle zorunlu aynı değildir; canlı önce/sonra pikselleri ayrı kıyaslanır.

İlk görev: mevcut branch/PR diff ve CI'ı incele; yeni kod yazmadan eksik kanıtı belirle. Canlı değişiklik onayı olmadan PR merge etme veya workflow_dispatch ile yayın başlatma. PR testleri sahte sosyal API kullanır; gerçek paylaşım kanıtı değildir. Üretim onayı sonrası normal research → persist → deploy zincirini ve eski donmuş SQL + dosyaları doğrula. Başarılı job yalnız kendi adımının kanıtıdır.

Manuel deneme/tekrar paylaşım, toplu eski içerik, yeni ücretli hizmet, yeni Meta izni, token üretimi ve güvenlik kontrolünü aşma bu devrin kapsamında değildir. Devam eden PR'ı kapatıp yeniden yazma; eski branch'leri gereksiz silme/force-push yapma. Kaynaklar geçici 403/503, TLS, robots veya API izin engeli verebilir; aynı sonuçsuz denemeleri döngüye alma.

## Başlangıçtan devre kadar birleşen PR indeksi

Bu liste GitHub merge kayıtlarından alınmıştır; her satır canlı teslim kanıtı değildir.

| PR | Çalışma | Merge (UTC) |
|---|---|---|
| [#1](https://github.com/ispartaofficial/ispartaofficial-news/pull/1) | Isparta için üniversite önceliği ve gül kimlikli kart şablonu | 2026-10-21T15:07:23Z |
| [#2](https://github.com/ispartaofficial/ispartaofficial-news/pull/2) | Isparta yerel haber ve üniversite kaynaklarını bulutta araştır | 2026-10-21T17:33:12Z |
| [#3](https://github.com/ispartaofficial/ispartaofficial-news/pull/3) | Isparta kaynak kapsamını 13 doğrulanmış okuyucuya tamamla | 2026-10-21T18:05:11Z |
| [#4](https://github.com/ispartaofficial/ispartaofficial-news/pull/4) | Isparta kaynak zaman aşımını ve eski duyuru eşleşmesini sınırla | 2026-10-21T18:15:00Z |
| [#5](https://github.com/ispartaofficial/ispartaofficial-news/pull/5) | Isparta ilçe ve üniversite kaynaklarını 29 okuyucuya genişlet | 2026-10-21T23:26:07Z |
| [#6](https://github.com/ispartaofficial/ispartaofficial-news/pull/6) | Mevcut üretim motorunu Isparta için bağımsız olarak uyarla | 2026-10-22T08:28:27Z |
| [#7](https://github.com/ispartaofficial/ispartaofficial-news/pull/7) | Isparta kaynak görsellerini üretim hizmetinden bağımsız denetle | 2026-10-22T12:49:07Z |
| [#8](https://github.com/ispartaofficial/ispartaofficial-news/pull/8) | Isparta için Instagram Login kimliğini ve yalnız GET kontrolünü hazırla | 2026-10-22T14:37:14Z |
| [#9](https://github.com/ispartaofficial/ispartaofficial-news/pull/9) | Isparta merkez için 17:00 nöbetçi eczane story hazırlığını ekle | 2026-10-22T17:47:36Z |
| [#10](https://github.com/ispartaofficial/ispartaofficial-news/pull/10) | Isparta görsel üretimini bağımsız ve isteğe bağlı bağla | 2026-10-22T23:20:11Z |
| [#11](https://github.com/ispartaofficial/ispartaofficial-news/pull/11) | Çocuk tiyatrosu kartlarında konu ve görsel eşleşmesini düzelt | 2026-10-23T13:37:38Z |
| [#12](https://github.com/ispartaofficial/ispartaofficial-news/pull/12) | Complete independent Isparta publishing and durable token renewal | 2026-10-24T07:26:28Z |
| [#13](https://github.com/ispartaofficial/ispartaofficial-news/pull/13) | Add one daily Isparta weather story at 08:00 | 2026-10-24T12:50:18Z |
| [#14](https://github.com/ispartaofficial/ispartaofficial-news/pull/14) | Prefer verified Isparta source images and allow three daily news pairs | 2026-10-24T19:03:08Z |
| [#15](https://github.com/ispartaofficial/ispartaofficial-news/pull/15) | Publish a fourth fresh Isparta evening news pair without next-day deferral | 2026-10-25T07:34:47Z |
| [#16](https://github.com/ispartaofficial/ispartaofficial-news/pull/16) | Use verified Isparta source photos and event genres | 2026-10-25T17:30:36Z |
| [#17](https://github.com/ispartaofficial/ispartaofficial-news/pull/17) | Require a relevant cover image before new Isparta posts | 2026-10-25T23:36:51Z |
| [#18](https://github.com/ispartaofficial/ispartaofficial-news/pull/18) | Keep image slots for real files and bind exact session posters | 2026-10-26T00:05:21Z |
| [#19](https://github.com/ispartaofficial/ispartaofficial-news/pull/19) | Keep rejected source pictures from starving later artwork | 2026-10-26T04:38:38Z |
| [#20](https://github.com/ispartaofficial/ispartaofficial-news/pull/20) | Recover pending covers with verified posters and reusable reviewed scenes | 2026-10-26T18:11:38Z |
| [#21](https://github.com/ispartaofficial/ispartaofficial-news/pull/21) | Complete visual recovery and preserve frozen publication images | 2026-10-28T11:16:49Z |

## Yerel çalışma ve kanıtların korunması

Önceki çalışma kökü `Documents/Codex/2026-10-11/referenced-chatgpt-conversation-this-is-an/`; checkout'lar `work/visual-first-20261026-seferihisar` ve `work/visual-first-20261026-isparta`. Bu yerel yollar yeni makinede bulunmayabilir. Önce doğru repo/remote/branch ve `git status` kontrolü yap.

Tarihli önceki deliller `outputs/visual-backlog-2026-10-26/` altında şehir-baseline, şehir-closure-1028 ve closure-20261029 klasörlerindedir. Tam SQLite/BLOB/ham logları GitHub'a topluca ekleme. Bu devir yalnız güvenli kod/test/belgeyi aktarır. Baz snapshot'ların kalıcı Git commit kimlikleri historical_visuals manifestindedir; yerel dosya yoksa ilgili committen salt okunur yeniden çıkarılabilir.

`work/verify_backlog_release_20261026.py` ana dal/durum/Pages ve bütün eski SQL alanları ile etkilenen JPEG hash kıyasını yapar. `work/verify_operational_publication_state.py` ve `work/verify_operational_release.py` önceki yardımcılar; repo kökü/şema varsayımları var, kör çalıştırma. Bunlar repo dışı yardımcıdır; bu dosya bunların temiz clone'da mevcut olduğunu vaat etmez. Gerekirse aynı dar salt okunur kıyası repo kodunu kullanarak yeniden yap.

Başlangıç komutları (hesap yetkisini normal güvenli yöntemle sağla, tokenı komut satırına yazma):

```sh
git fetch origin main automation-state
git status --short
git log -5 --oneline
python -m pip install -e ".[test]"
python -m pytest -q
```

Devir branch'i ve ana dal farklıdır. Önce devir branch'ini incele; canlıya geçiş için kullanıcı onayı, yeni head CI ve normal dağıtım kanıtı gerekir. Bu belge eski sohbet içindeki tüm sözlü başarı iddialarını otomatik doğrulanmış saymaz.

## Devir anındaki ek kanıt

[HANDOFF-EVIDENCE.md](HANDOFF-EVIDENCE.md), bu devir sırasında alınmış salt okunur durum/dağıtım sonucudur. Seferihisar arşiv JPEG ve SQL kıyası geçti; Isparta PR #22 henüz canlı değildir.

### Devir sırasında yeniden çalıştırılan yerel test

29 Ekim: bu dalın mevcut kodunda `python -m pytest -q`: **726 passed, 9 skipped (93.76 s)**. Atlanan native/opsiyonel kontroller başarılı sayılmadı. Son yükleme head’inin GitHub CI sonucu ayrıca görülmelidir; devir sırasında canlı merge yapılmadı.
