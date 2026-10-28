"""Two source-owned photographs visually reviewed on 27 Oct 2026.

This is an exact article/pixel review, never an automatic model approval.
Office visit and matching headline; thyme plant and matching headline were
inspected in the actual files. Normal source identity/date, robots, TLS,
reuse, expiry and publication gates remain mandatory. No inference from a
person's appearance, and no general threshold or source-wide exemption.
"""
import hashlib

REVIEWS = ({'source_id': 'bomba32', 'url': 'https://www.bomba32.com/huda-par-isparta-il-baskani-salih-demirden-yeni-muftuye-ziyaret', 'title': 'HÜDA PAR Isparta İl Başkanı Salih Demir’den Yeni Müftüye Ziyaret', 'published_at': '2026-10-26T20:37:00+03:00', 'image_url': 'https://bomba32com.teimg.com/crop/1280x720/bomba32-com/uploads/2026/10/iauiiu.jpg', 'subject': 'meeting', 'sha256': 'f44c340fc59aa07254609b1e6c3b30dbd6a505879bd1f650ad99d58e202e7669'}, {'source_id': 'bomba32', 'url': 'https://www.bomba32.com/sutculerin-endemik-kekigi-altin-degerinde', 'title': 'Sütçüler’in Endemik Kekiği Altın Değerinde', 'published_at': '2026-10-27T10:49:00+03:00', 'image_url': 'https://bomba32com.teimg.com/crop/1280x720/bomba32-com/uploads/2026/10/gp-18.jpg', 'subject': 'thyme_herbs', 'sha256': 'ab4f808178d8b50735d4606beaba45100eb75ef79641a2485281b1c072f66e93'})


def reviewed_article(item):
    return item.get('kind') == 'news' and any(all(item.get(k) == row[k]
        for k in ('source_id', 'url', 'title', 'published_at')) for row in REVIEWS)


def reviewed_photo(data, item, image_url, expected):
    if not reviewed_article(item):
        return False
    digest = hashlib.sha256(data).hexdigest()
    return any(row['subject'] == expected and row['image_url'] == image_url
        and row['sha256'] == digest and all(item.get(k) == row[k]
        for k in ('source_id', 'url', 'title', 'published_at')) for row in REVIEWS)
