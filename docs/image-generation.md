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

Önce aynı kaynağa bağlı ve denetlenmiş fotoğraf/afiş değerlendirilir. Üretici,
yalnız mevcut konu sınıflandırıcısının desteklediği etkinlik sahnelerinde
kullanılır. Haber olayları, gerçek kişiler veya gerçek mekânlar yeniden
canlandırılmaz. Desteklenmeyen veya belirsiz konuya alakasız fotoğraf konmaz.

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
