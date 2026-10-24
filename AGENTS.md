# IspartaOfficial çalışma kuralları

Önce `docs/project-brief.md` ve gerçek çalışma dosyalarını okuyun. Bu depo
Seferihisar üretiminden bağımsızdır. `news_engine/`, Seferihisar'ın mevcut üretim
motorundan uyarlanır; eşdeğer kuralları yeniden yazmayın. Kökeni ve kapsamı
`docs/engine-port.md` ile `docs/engine-provenance.json` içinde izlenir.
`research.yml` kaynak araştırması, kalıcı kuyruk ve kart hazırlığı yapar; canlı
çalışması Actions/Pages/durum dalı kanıtıyla ayrı doğrulanır. Meta bağlantısı bağımsız Isparta hesabıyla doğrulanmıştır.
23 Ekim kullanıcının yayına hazır etme talebiyle yayın kapıları açılabilir; gerçek teslim ayrıca doğrulanır. Kod veya başarılı hazırlık, gerçek teslim değildir.

- Kullanıcı Isparta merkez ve bütün ilçelerini, özellikle üniversite yaşamı,
  konser, festival ve tiyatro içeriklerini önceliklendirdi.
- Mevcut Instagram logosu referanstır. Seferihisar logosu, renkleri, anahtarları,
  yayın kayıtları veya veritabanı bu depoya taşınmaz.
- Etkinlik günü ile haberin yüklenme tarihi farklıdır. Geçmiş, iptal edilmiş,
  yılı/saatı belirsiz veya katılım koşulu açıklanmamış içerikleri uygun saymayın.
- Kamuya açık üniversite etkinliği ile yalnız öğrencilere/üyelere açık etkinliği
  ayırın. Ücret bilinmiyorsa ücretsiz demeyin.
- Kaynak araştırması, çalışan okuyucu, hazırlanmış kart, bulut dağıtımı ve gerçek
  yayın ayrı kanıtlardır. Önizlemeyi paylaşılmış içerik gibi sunmayın.
- Sırları/oturumları kopyalamayın. Robots/TLS korumasını aşmayın.
- Araştırma için `python -m isparta.research` kullanın. Kaynak sağlığı, ayrıştırma,
  taslak adayı ve yayın onayı farklıdır. Rapor `publication_ready=false` tutar.
- Araştırma çıktısında yalnız kısa kaynak alıntısı ve adresi bulunur. Taslak
  hazırlarken tam kaynağı tekrar doğrulayın; kesilmiş alıntıyı tam metin saymayın.
- `isparta.runtime` iç kaynak toplamasını ve mevcut motoru birleştirir. Tam kaynak
  metni yalnız bellekte doğrulanır; rapor ve açık durum dalı kısa alıntı taşır.
  Eski ya da yabancı veritabanını kullanmayın; Isparta kurulum kimliği zorunludur.
- `config/runtime.json` ve GitHub yayın değişkenleri birlikte kapı oluşturur.
  Kapalı kapıyı alternatif giriş noktasıyla aşmayın. Yeni Meta izni oluşturmayın.
  Mevcut Instagram Login anahtarı resmî uç noktadan yenilenir; yalnız şifreli
  kapsül kalıcı duruma girer. Asıl environment secret şifreleme anahtarıdır;
  kapsülü korumadan değiştirmeyin. `docs/live-readiness.md` açıklamasını okuyun.
- Tasarımda başlık, tarih/saat, mekân/ücret ve açıklama notu ayrı alanlardır.
  Kaynak görsel üzerinde değil açıklamadadır. Boş bir açıklama slaytı eklemeyin.

