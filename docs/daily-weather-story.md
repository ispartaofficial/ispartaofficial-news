# Isparta günlük hava durumu story — 24 Ekim 2026

Kullanıcı Isparta için her sabah Türkiye saati 08:00 hedefli hava durumu story ve örnek kart istedi. Bu özellik mevcut Isparta Instagram hesabını ve aynı şifreli bağlantı kapsülünü kullanır. Seferihisar logosu, salyangozu, anahtarı, veritabanı veya yayın kayıtları taşınmaz.

## Veri ve kart

Veri MGM’nin Antalya Bölge günlük tahmin bültenindeki yalnız **Isparta** satırıdır. İlçe veya başka ilin satırı yedek sayılmaz. Bültenin açık başlangıç/bitiş aralığı o gün 08:00’ı kapsamalıdır. Kaynak tarihi ve geçerliliği doğrulanmadan kart hazırlanmış sayılmaz. Eksik en düşük veya en yüksek sıcaklık uydurulmaz; ikisi de eksikse paylaşım engellenir. Eski günün tahmini bugünün kartına çevrilmez.

Kart Isparta’nın mevcut gül logosunu, açık zeminini ve küçük fuşya/mürdüm vurgularını kullanır. Tahmin yazıları ve sıcaklıklar programla yerleştirilir; stok tasarım varlıkları depoda tutulur. Günlük yeni görsel üretimi veya bu sohbetle bağlantı gerekmez. Önizleme “paylaşılmadı” olarak işaretlenir. Stok sahne isparta/assets/weather-background-v1.png içindedir; sürüm değiştirilmeden üzerine yazılmaz. Karttaki büyük sayı anlık ölçüm diye sunulmaz: en yüksek değer varsa “Gündüz en yüksek”, yalnız en düşük değer varsa “Gece en düşük” etiketi kullanılır. Kaynakta bulunmayan gece sıcaklığı gösterilmez. Tam hava açıklaması okunur satırlara sığmazsa hava kartı engellenir; diğer haber dışa aktarımları devam eder.

## Bulut zamanlaması

Normal araştırma 06:00–08:59 arasında güncel tahmini yeniler ve kartı Pages’e dağıtır. 07:35 hedefli erken hava işi, yalnız güncel ve dağıtılmış bir kart varsa 08:00’a en fazla 25 dakika bekler. 08:00, 08:17, 08:32 ve 08:47 aynı günlük yola güvenli yedek tetikleyicilerdir. Güvenilir main araştırmasının 07–08 yerel saatinde başlatılmış başarılı tamamlanması da bu yolu tetikleyebilir. GitHub kuyruk gecikmesi nedeniyle tam dakika garantisi yoktur.

Yayın sırasında kaynak kontrolü en fazla 90 dakika eski olmalı; doğru gün ve açık geçerlilik korunmalıdır. Canlı manifest ve gerçek 1080×1920 JPEG’nin SHA-256 değerleri karşılaştırılır. 09:00 ve sonrasında geç telafi yayını yoktur. Zamanı geçmiş veya eski tahmin paylaşılmaz.

## Kalıcı yayın ve izinler

Her yerel günün hava story’si weather_stories tablosunda ayrı tek iddia tutar; haberlerdeki iki gönderi ve eşleşen story sayacını, nöbetçi eczane tablosunu veya Facebook’u kullanmaz. Aynı isparta-production kilidi bütün üretim yazımlarını sıralar. Doğru Isparta hesap kimliği kontrol edilir. İlk Meta yazımından önce kalıcı iddia uzakta saklanır; belirsiz veya başlamış iddia otomatik sıfırlanmaz ve tekrar gönderilmez. Önceki gerçek yayınlar ve medya kayıtları korunur.

isparta.production weather girişi mevcut şifreli anahtar çözme/yenileme yolunu kullanır. Yeni Meta izni veya yeni kalıcı anahtar oluşturulmaz. Sonraki doğal yedek veya araştırma işinde yalnız GET ile kayıtlı story’nin aktif listede varlığı denetlenebilir; bu kontrol yeni paylaşım yapmaz.

Manual “Run workflow” yalnız kaynak ve kart önizlemesidir. Meta anahtarına, üretim veritabanına veya kalıcı durum dalına erişmez; yayın işini tetikleyemez. Hazırlanan örnek, gerçek 08:00 teslimi olarak sunulmaz. İlk doğal teslim zamanı geldiğinde API yanıtı, kalıcı kimlik ve mümkünse doğrudan platform ekranı ayrı kanıtlarla değerlendirilir.
