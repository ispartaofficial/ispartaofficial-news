# Devir sırasındaki salt okunur kanıt — 29 Ekim 2026

Bu kayıt canlı hesap ekranı gözlemi değildir. SQL status API iddiasıdır; prepared paylaşılmış sayılmaz. Tarihli sağlık her gelecekteki tur için garanti değildir.

```json
{
  "captured_at": "2026-10-29T06:50:42.331785+00:00",
  "state_sha": "3719eb0a024ae351afa2f0911a13c579c29e2be1",
  "counts": {
    "posts": [
      [
        "blocked_source",
        53
      ],
      [
        "expired",
        24
      ],
      [
        "prepared",
        1
      ],
      [
        "published",
        26
      ],
      [
        "superseded",
        105
      ]
    ],
    "weather_stories": [
      [
        "published",
        5
      ]
    ],
    "pharmacy_stories": [
      [
        "prepared",
        1
      ],
      [
        "published",
        5
      ]
    ]
  },
  "latest_daily": {
    "weather_stories": [
      [
        "2026-10-29",
        "published"
      ]
    ],
    "pharmacy_stories": [
      [
        "2026-10-28",
        "published"
      ]
    ]
  },
  "source_health": [
    [
      "failed",
      2
    ],
    [
      "ok",
      26
    ],
    [
      "partial",
      1
    ]
  ],
  "platform_ui_observed": false
}
```

## 29 Ekim 2026 akşam — merge sonrası salt okunur doğrulama

Kaynak: `automation-state` dalındaki `platform.sqlite` kayıtlarının bütün sütun karşılaştırması ve GitHub Actions iş sonuçları. Platform ekranı gözlenmedi. Yeşil iş yalnız kendi adımının kanıtıdır.

```json
{
  "pr22_restore": {
    "merge_commit": "f2e1b84ddace25e337085bdd4fdb51910e5dd5e1",
    "research_run": 40927613738,
    "run_jobs": {"research": "success", "deploy": "success", "publish": "success"},
    "state_before": "0c1761896b3b31d897b414313bd87277d77cc790",
    "state_after": ["df76f221af5746a587441831a801e06c26f4a529", "00f2b3fb7703ab0ce4b19775e0e07dc7dd6f50fa"],
    "pinned_snapshot": "8d4c43157a99f95705163b1d66a82776e9633c1f",
    "pinned_snapshot_sha256_matches_manifest": true,
    "restored_key": "64b0870d8d0714a1fd8c94a0",
    "restored_before": "absent",
    "restored_after_fingerprint_matches_original": true,
    "restored_image_sha256": "9b11c40dbb3936316cecc239f930d8fc14640eb3b466e2968c04fbe423d3f2e8",
    "restored_image_bytes_equal_snapshot": true,
    "owning_posts_fingerprints_match": 4,
    "frozen_vs_before": {"posts": 28, "weather_stories": 5, "pharmacy_stories": 6, "credential_capsules": 1, "all_sql_columns_unchanged": true},
    "frozen_vs_26_oct_snapshot": {"posts": 14, "weather_stories": 2, "pharmacy_stories": 2, "all_sql_columns_unchanged": true},
    "delivery_audits_changed_columns": ["checked_at"]
  },
  "pr24_pr23": {
    "merge_commits": {"pr24": "c33913a", "pr23": "51865e3"},
    "research_runs": {"40942151959": "success", "40942260293": "success"},
    "state_before": "72827f6356630b9e1e063856a40b04d6912d08fe",
    "state_after": "c23fc43",
    "frozen_vs_before": {"posts": 28, "weather_stories": 5, "pharmacy_stories": 6, "credential_capsules": 1, "all_sql_columns_unchanged": true},
    "restored_image_still_equal_snapshot": true,
    "bomba32_parsed_items": {"before": 4, "after": 12},
    "posts_prepared": {"before": 1, "after": 5},
    "posts_blocked_source": {"before": 57, "after": 53},
    "advertorial_hold_observed_live": false
  },
  "editorial_incident": {
    "published_post": "acc08d969406c1e6964b9dd2",
    "published_at": "2026-10-29T15:03:32+03:00",
    "source_section": "Reklam Manşet20",
    "removed_from_platform": false
  },
  "platform_ui_observed": false
}
```
