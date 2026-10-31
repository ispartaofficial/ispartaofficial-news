# Bağımsız Isparta görsel üretimi

23 Ekim 2026. Mevcut Cloudflare Workers AI üreticisi yalnız içerik hazırlama
adımına bağlandı. Yeni model, yeni servis veya kota artışı eklenmedi.

Üretim, depo değişkeni `ILLUSTRATIONS_ENABLED` tam olarak `true` olduğunda ve
yalnız Isparta için oluşturulmuş `CLOUDFLARE_ACCOUNT_ID` ile
`CLOUDFLARE_API_TOKEN` depo Secrets alanında bulunduğunda kullanılabilir.
Seferihisar anahtarı taşınmaz. Bu sürüm sır veya değişken oluşturmaz;
eksik yapılandırmada bilgi kartı devam eder. Gerçek bağlantı henüz doğrulanmadı.

Sırlar yalnız ana dalın mevcut araştırma işindeki içerik hazırlama adımına
verilir. Model kurulumu, durumun kaydedilmesi, rapor, Pages dağıtımı ve sosyal
yayın adımları Cloudflare anahtarı almaz. Araştırma hiçbir Meta anahtarı almaz.
Bu bağlantı Instagram yayın kapılarını açmaz.

Önce aynı kaynağa bağlı ve denetlenmiş fotoğraf/afiş değerlendirilir. Haber
olayları, gerçek kişiler veya gerçek mekânlar yeniden canlandırılmaz.

30 Ekim 2026 kullanıcı kararı: gözden geçirilmiş konu listesi dışındaki güncel
haberin kendi uygun fotoğrafı yoksa habere uygun genel bir sahne üretilir.
Aynı Workers AI hesabındaki `@cf/meta/llama-3.1-8b-instruct` metin modeli, başlık
ve en fazla 400 karakterlik özetten İngilizce bir sahne tarifi ve kısa açıklama
önerir. Bu çıktı güvenilmez veridir: kişi, yüz, el, kalabalık, yazı, tabela,
logo, şiddet, kaza, tanınabilir mekân, sayı ve başlıktaki özel adlar içeren ya
da biçimi bozuk tarif reddedilir; ölüm, yaralanma, suç, hastalık veya kişiye
odaklı haberde model sahne önermez. Kabul edilen tarifle Flux görseli üretilir,
OCR ile yazı denetlenir ve görsel, yerel CLIP modelinde kendi açıklamasına
yazı grafiği, portre, kalabalık ve şehir silüetinden daha iyi uymalıdır
(üç kart kırpması, en az 0,24 benzerlik ve 0,015 fark). Reddedilen tarif veya
görsel kapak olmaz ve aynı haber için yeniden denenmez. İlk canlı turda Cumhuriyet
Bayramı sahnesine Doğu Asya tarzı kâğıt fenerler girdi; bu yüzden tarif, çizim
isteği ve kontrol süslemelerin Türkiye'ye uygun olmasını ister, fener/pagoda/ejderha
içeren tarif reddedilir ve görsel kendi açıklamasına kırmızı kâğıt fenerlerden daha
iyi uymalıdır. Sahne sürümü v11'e yükseltildi; hazırlanmış eski sahneler yeniden üretilir. Tarif isteği aynı
üretim girişimine dahildir; tur/gün sınırları değişmez. Kartlara otomatik AI
notu eklenmez. Desteklenmeyen etkinliklere ve ileri tarihli duyurulara
alakasız görsel konmaz.

30 Ekim akşamı: Ethem amca ve Yiğit (matematik olimpiyatı) kartları aynı boş
oturma odasıyla yayımlandı; birinde pencereden yabancı bir şehir silüeti
görünüyordu. Kurallar insanı, öğrenciyi ve mekânı yasaklayınca kişi haberinde
geriye "boş iç mekân" kalıyordu; CLIP yalnız resmin kendi tarifine uyduğunu
ölçüyordu. Kullanıcı kararı: yapay zekâ görseli haberle en az %70–80 uyumlu
olmalı, alakasız görsel olmamalı. Sürüm v12:

- Model önce habere özgü 2–4 somut nesne seçer (`objects`) ve sahne bu nesneleri
  göstermelidir. Oturma odası, kanepe, koltuk, yatak odası, perde, pencere, manzara
  ve balkon içeren tarif reddedilir. "Adı geçen kişi" artık sahneyi kendiliğinden
  kapatmaz; kişi gösterilmeden konusunun nesneleriyle anlatılır. Ölüm, yaralanma,
  suç ve hastalık haberinde sahne önerilmez.
- Aynı metin modeli ikinci bir çağrıda tarifin haberi ne kadar anlattığını 0–10
  puanlar; 7'nin altı reddedilir (`MIN_RELEVANCE`). Bu, kullanıcının %70 eşiğinin
  karşılığıdır, kesin bir ölçüm değildir.
- CLIP denetimine "boş oturma odası" ve "pencereden şehir" karşı etiketleri eklendi.
- Reddedilen tarif veya görsel kapak olmaz; haber ilgisiz görselle yayımlanmaz.
  Canlı modelin yeni biçime uyumu ilk turlarda `illustrations` istatistiklerinden
  (`scene_rejected`, `article_scene`) izlenir.

31 Ekim sabahı: dört kart görselsiz bekliyordu ve üçünün yolu kapalıydı. Sürüm v13:

- Model kurallardaki "insan yok, yazı yok" ifadesini tarife kopyalayınca bu,
  yasak kelimeyi içerdiği için ret sayılıyordu. Olumsuz cümlecik artık silinir;
  ne görsele gider ne ret nedeni olur. Sahne sınırı 420 karaktere çıktı.
- Reddedilen taslak bir kez, sıcaklığı değiştirilerek yeniden istenir; model
  haberi reddetmişse (`declined`) yeniden istenmez. Ret nedeni tekrarda da
  `scene_rejections`, puanlar `scene_scores` ile panele yazılır.
- Sürüm anahtarı değiştiği için 30 Ekim'de deneme hakkı biten iki haber bir kez
  yeni kurallarla denenir. Eski kayıtlara dokunulmaz.
- Güncellenen etkinlik önceki revizyonunun denetimden geçmiş görselini kullanır;
  OCR ve konu denetimi yeniden çalışır.
- `event` genel kategorisindeki kariyer, meslek, seminer ve sempozyum başlıkları
  `education` konusunu alır. Önceden bu etkinliklerin hiç görsel yolu yoktu.

Canlı modelin yeni kurallara yanıtı yerel olarak denenemedi (Workers AI anahtarı
yalnız GitHub'da); ilk gerçek sonuç paneldeki sayaçlardır.

31 Ekim öğlen, v13'ün ilk turları: üç haber denendi, ikisi `unsafe`, biri `no_score`
ile bitti. Sürüm v14:

- Puan yanıtı 20 belirteçle sınırlıydı ve yalnız kapalı JSON okunuyordu. Sınır 60
  oldu; puan JSON, düz metin veya kesilmiş yanıttan okunur. Açık bir puan yoksa
  yine `no_score` sayılır, %70 eşiği değişmedi.
- `unsafe` hangi kuralın çalıştığını söylemiyordu. Artık `unsafe_length`,
  `unsafe_description`, `unsafe_characters` ve `unsafe_word_<kelime>` yazılır.
  Kelime kapalı yasak listesinden gelir, modelin serbest metni panele çıkmaz.
- Sürüm anahtarı, deneme hakkı biten haberlere bir deneme daha verir.

Mevcut sınırlar korunur: tur başına en fazla iki, UTC günü başına en fazla
yirmi üretim girişimi; öğe ve revizyona bağlı kalıcı önbellek; OCR ile yazı/tarih
kontrolü ve gerçek kart kırpmalarında konu denetimi. Bu girişim sınırları servis
faturalandırmasının ücretsiz kalacağı garantisi değildir; ücretli yükseltme
yapılmadı. Hata veya kota doluluğu tekrarlayan üretim döngüsü başlatmaz.

Güncel çalışma sonucu `data.json` içindeki `illustrations.enabled`,
`configured`, `attempted`, `generated`, `reused` ve denetim sayaçlarıyla ayrıca
doğrulanır. Anahtarın kaydedilmesi, modelin kurulması veya yeşil workflow tek
başına uygun bir görselin üretildiğini ya da Instagram'da yayımlandığını kanıtlamaz.
`config/runtime.json` içindeki kurulum durum bilgisi de gerçek bağlantı kanıtı
elde edilmeden tamamlandı olarak değiştirilmez.
