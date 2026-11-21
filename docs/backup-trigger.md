# Yedek araştırma tetikleyicisi (Cloudflare Worker)

21 Kasım 2026: GitHub `schedule` olayları 20 Kasım'dan beri bu depoda çoğunlukla gelmedi;
`research.yml` seyrek koştu, hava/eczane story'leri bu yüzden düştü. `ops/cron-worker.mjs`
Seferihisar'daki yedeğin Isparta'ya ayrı, bağımsız karşılığıdır. Kod var diye dağıtılmış veya
çalışıyor sayılmaz; dağıtım ve token sahibin işidir.

## Ne yapar, ne yapmaz

- 15 dakikada bir (`12,27,42,57 4-20 * * *` UTC) GitHub Actions çalışma listesini okur.
  Yalnız 04:20–20:50 UTC (07:20–23:50 TR) arasında, yalnız `research.yml`'yi `main` üzerinde,
  hiçbir girdi göndermeden (`{"ref":"main"}`) başlatır.
- `isparta-production` kuyruğunu paylaşan bir iş (research, hava, eczane, resolve-uncertain)
  kuyrukta/çalışıyorsa başlatmaz: yeni bir çalışma bekleyen işi kuyruktan düşürebilirdi.
- Son 25 dakikada başlamış bir research varsa (sonucu ne olursa olsun) başlatmaz.
- Hava (04:35–05:30 UTC = 07:35–08:30 TR) ve eczane (13:35–14:30 UTC = 16:35–17:30 TR)
  pencerelerinde o pencereyi karşılayan başarılı bir research (T04/T05 veya T13/T14'te başlamış,
  07:35/16:35 TR sonrası bitmiş) yoksa 25 dakika kuralını beklemeden başlatır. Story işleri
  `workflow_run` ile olay türüne bakmadan tetiklendiği için başlatılan research de sayılır.
- Meta/Instagram/Cloudflare AI anahtarı almaz; yayın kapılarına, günlük sınırlara,
  `automation-state` dalına dokunmaz. Yayın kararlarını yine iş akışının kendi kapıları verir.

## Kurulum (sahip; PR birleştirildikten sonra)

1. GitHub'da **ispartaofficial** hesabıyla: Settings → Developer settings → Personal access
   tokens → Fine-grained tokens → Generate new token. Ad: `isparta-research-watch`;
   Resource owner: `ispartaofficial`; Repository access: *Only select repositories* →
   `ispartaofficial-news`; Repository permissions → **Actions: Read and write** (Metadata
   otomatik salt okunur). Başka izin verme. Süre: en fazla 1 yıl (takvime yenileme notu düş).
   Değeri kimseyle paylaşma, sohbete veya dosyaya yazma.
2. Isparta'nın Cloudflare hesabında: Workers & Pages → Create → Worker → "Hello World" ile
   `isparta-research-watch` adında oluştur → Deploy → Edit code → içeriği `main` dalındaki
   `ops/cron-worker.mjs` ile tamamen değiştir → Deploy. (Ücretsiz plan yeterlidir.)
3. Worker → Settings → Variables and Secrets → Add: tür **Secret**, ad `GITHUB_ACTIONS_TOKEN`,
   değer 1. adımdaki token. Bir tane daha: tür **Text**, ad `CRON_DISPATCH_ENABLED`, değer `true`.
   Deploy/Save.
4. Worker → Settings → Trigger Events → Add → Cron Triggers → `12,27,42,57 4-20 * * *` → Add.
5. İsteğe bağlı: Settings → Domains & Routes → `workers.dev` adresini kapat (Worker zaten
   yalnız zamanlanmış çalışır, adres bir şey tetiklemez).
6. Doğrulama: bir sonraki tetiklemede Worker'ın Logs/Observability bölümünde
   `{"status":"..."}` satırı görünür; başlatılan research Actions'ta `workflow_dispatch` olayıyla görünür.

Komut satırı tercih edilirse (`ops/` içinde): `npx wrangler login`, `npx wrangler deploy`,
`npx wrangler secret put GITHUB_ACTIONS_TOKEN`, etkinleştirmek için
`npx wrangler deploy --var CRON_DISPATCH_ENABLED:true`. `wrangler.jsonc` varsayılanı `false`dır.

**Durdurma:** `CRON_DISPATCH_ENABLED` değerini `false` yap veya cron tetikleyicisini sil;
gerekirse GitHub'da token'ı iptal et (Revoke).

Durum değerleri: `disabled`, `outside_window`, `production_busy`, `recent_run`, `dispatched`
(pencere telafisinde `window: weather|pharmacy`), `dispatch_failed`, `github_unreachable`,
`invalid_runs`, `check_failed` (yalnız aşama/hata türü; istek, token veya yanıt gövdesi yazılmaz).
