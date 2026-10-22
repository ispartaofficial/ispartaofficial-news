# Bağımsız Isparta Instagram bağlantısı

22 Ekim 2026. Isparta'nın bağlı Facebook sayfası olmadığı için Instagram Login
yolu hazırlanmıştır. Bu, Seferihisar uygulamasını veya anahtarını kullanmaz.
Yeni `news_engine/meta_identity.py`, bu kuruluma ait uyarlamadır; hazır bir
Seferihisar hesabı bağlantısı değildir.

## Kimlik ve API adresi

Resmî Meta belgeleri:
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/get-started
- https://developers.facebook.com/documentation/instagram-platform/content-publishing

`instagram_login`, yalnız `graph.instagram.com`; eski `facebook_login`, yalnız
`graph.facebook.com` kullanır. İstek başka sunucuya yönlendirilmez; geçersiz mod
ve hata cevabı başka akışa otomatik dönüş sebebi değildir. Araştırma işi hiçbir
Meta anahtarı almaz. Varsayılan yayın kapısı kapalıdır.

Instagram Login kimliği `GET /me?fields=user_id,username,account_type` ile okunur.
`user_id` gerçek Instagram profesyonel hesap kimliği, `id` uygulamaya özel
kimliktir; birbirinin yerine geçmez. Kullanıcı adı tam `ispartaofficial`,
`user_id` bağımsız yapılandırmadaki değer ve hesap türü belgelenen Business veya
Media_Creator olmalıdır. Eksik/yanlış/çoklu kimlik reddedilir. Tokenin başka şehre
ait olması kullanıcının mevcut Isparta yayınlarını yönetme yetkisi değildir.

## Yalnız okuma testi

`connection.yml` manuel ve başlangıçta kapalıdır. Yalnız doğru depo/ana dalda,
`META_CONNECTION_CHECK_ENABLED=true` olduğunda, bağımsız `instagram-production`
ortamındaki mevcut Isparta anahtarıyla çalışabilir. Bu sürüm değişkeni oluşturmaz,
izin vermez veya anahtar üretmez. Otomatik/sürekli kontrol döngüsü eklenmemiştir.

Test en fazla iki Instagram GET isteğiyle hesap ve yayın kotası kullanımını
okur. Kimlik yanlışsa ikinci isteğe geçmez. Caption, anahtar, hesap kimliği veya
ham hata gövdesi raporlanmaz. Facebook kapalıdır; Instagram Login seçiliyken
yanlışlıkla Facebook sayfa anahtarı Instagram sunucusuna gönderilmez. SQLite,
Pages veya medya nesnesi yazılmaz. `connected`, o andaki GET sonucudur;
`publication_permission_verified=false`, `publication_attempted=false` ve
`expiry=not_checked` kalır. Süresiz bağlantı veya gerçek story teslimi çıkarılmaz.

## Yayın kapısı

İki bağımsız JSON değeri `publishing_enabled` ve `meta_connected` gerçek boolean
true olmadan Instagram adaptörü bile açılmaz. Sonrasında depo/ana dal, seçilmiş
kimlik doğrulama yolu, önceki API testleri, doğru kullanıcı, dağıtılmış gerçek
JPEG ve mevcut kalıcı iddia/günlük tavan kapıları korunur. Başarılı GET testi bu
değerleri veya diğer GitHub yayın değişkenlerini kendiliğinden değiştirmez.
Başlamış/yayımlanmış/belirsiz kayıt sıfırlanmaz, deneme veya tekrar paylaşım yoktur.

## Bu tarihteki durum ve kalan iş

IspartaOfficial Haber oluşturma formu kullanıcı tarafından onaylandı; Meta
hesap sahibinden resmî pencerede yeniden Facebook şifresi doğrulaması istedi.
Kullanıcı bilgisayar başında değil. Şifre sohbette istenmedi ve asistan tarafından
alınmadı veya girilmedi; bu adım bekletilir. Henüz oluşturulmuş Isparta uygulama
kimliği veya yeni izin/anahtar yok.
Yeni kapsam/anahtar için ayrıca somut işlem anı onayı ve doğru Isparta hesabı
gerekir. Şifre, erişim anahtarı veya doğrulama kodu sohbete yazılmaz.

Yerel/sahte HTTP testleri API host'unu, app-scoped kimliğin kabul edilmemesini,
yanlış kullanıcı/hatalı yanıt/yönlendirmeyi, gizli hata metninin çıkmamasını ve
yanlış bağlantıda veritabanına/medyaya hiç geçilmemesini kapsar. Bunlar gerçek
Meta erişimi değildir. İzin ve kimlik tamamlanınca önce GET kontrolü, sonra ayrı
yayın planı/ilk doğal teslim ve teslim GET gözlemi doğrulanmalıdır. Porttaki
`delivery_audit` bu yeni akışa henüz bağlanmamıştır; gerçek teslim kanıtı yoktur.
