"""Routine service lists with their own daily story, and contradictory dates,
are never news cards (Isparta, 22 Nov 2026)."""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from news_engine.domain import digest, parse_date
from news_engine.instagram import publish_one
from news_engine.operations import summary
from news_engine.quality import date_mismatch, news_editorial_reason, publication_copy_reason
from news_engine.schedule import prepare, queue_item


def adapter():
    api = Mock()
    api.enabled.return_value = True
    api.account = '1234'
    api.session.head.return_value = SimpleNamespace(status_code=200, headers={'Content-Type': 'image/jpeg'})
    api.container.return_value = 'container-1'
    api.call.return_value = {'id': 'media-1'}
    return api


def assets_for(store):
    return {p['id']: {'feed': [f"media/{p['id']}/feed-1.jpg"], 'story': [f"media/{p['id']}/story-1.jpg"]}
            for p in store.posts()}

AT = parse_date('2026-11-22T10:00:00+03:00')
# Shortened copy of the Haber32 article that went out on 22 Nov 2026.
HABER32 = {
    'kind': 'news', 'category': 'news', 'source_id': 'haber32', 'source_name': 'Haber32',
    'title': 'Isparta ve İlçelerde Nöbetçi Eczaneler (22 Kasım 2026)',
    'description': ('Isparta ili merkez ve ilçelerinde 12 Kasım 2026 Pazar günü nöbetçi olan eczaneler '
                    'listesi... DAVRAZ MAH. 104.CAD. NO:40A/Z05 ŞEHİR HASTANESİ KARŞISI İSKENDER '
                    'MAHALLESİ AKSU CADDESİ SERMET SAĞLIK OCAĞI KARŞISI NO:24/B'),
    'url': 'https://www.haber32.com.tr/isparta-ve-ilcelerde-nobetci-eczaneler-22-kasim-2026',
    'published_at': '2026-11-22T07:45:00+03:00',
}


def news(title, description='Isparta’da yapılan açıklamada vatandaşlara ayrıntılı bilgi verildi.',
         url='https://www.haber32.com.tr/haber-1', **changes):
    return {**HABER32, 'title': title, 'description': description, 'url': url,
            'sources': [url], **changes}


def test_the_published_haber32_list_is_held_for_the_pharmacy_story():
    assert news_editorial_reason({**HABER32, 'sources': [HABER32['url']]}) == 'dedicated_pharmacy_story'
    # Its own wrong date would also have held it.
    assert date_mismatch(HABER32)


@pytest.mark.parametrize('item', [
    news('ISPARTA NÖBETÇİ ECZANELER'),
    news("Isparta'da bugün hangi eczaneler nöbetçi?"),
    news('Isparta nobetci eczane listesi'),
    news('Isparta Nöbetçi Eczaneleri Nerede? İşte Adresler'),
    # Neither the title nor the body says it, the article address does.
    news("Isparta'da Bugün Açık Eczaneler",
         url='https://www.haber32.com.tr/isparta-nobetci-eczaneler-23-kasim-2026'),
    news("Isparta'da 23 Kasım'da açık eczaneler",
         'Isparta merkezde 23 Kasım 2026 Pazartesi günü nöbetçi olan eczaneler listesi haberimizde.'),
])
def test_pharmacy_lists_in_any_spelling_are_held(item):
    assert news_editorial_reason(item) == 'dedicated_pharmacy_story'


@pytest.mark.parametrize('item', [
    news("Isparta'da nöbetçi eczanede soygun",
         'Gece nöbetçi eczaneyi soyan şüpheli kısa sürede polis tarafından yakalandı.'),
    news('Nöbetçi eczanede silahlı saldırı', 'Merkezdeki bir eczanede yaşanan olayda bir kişi yaralandı.'),
    news("Eczacılar Odası'ndan nöbetçi eczaneler açıklaması",
         'Isparta Eczacı Odası Başkanı, nöbetçi eczaneler uygulamasına ilişkin açıklama yaptı.'),
    news('Eczacı Odası Trabzon’da Mesleğin Geleceğini Görüştü',
         'Toplantıda ilaç fiyat kararnamesi ve eczacı istihdamı gündeme geldi, görüşler paylaşıldı.'),
    news('Bayramda hastaneler ve eczaneler açık olacak',
         'Bayram boyunca acil servisler ve nöbetçi eczaneler kesintisiz hizmet verecek.'),
    news('Nöbetçi eczane ücretine zam', 'Gece hizmet bedeli yeni yılda yeniden belirlenecek, oda açıkladı.'),
])
def test_news_about_pharmacies_is_not_held(item):
    assert news_editorial_reason(item) is None


@pytest.mark.parametrize('title, reason', [
    ('Isparta Hava Durumu Raporu', 'dedicated_weather_story'),
    ("Isparta'da bugünkü hava durumu", 'dedicated_weather_story'),
    ('Meteorolojiden Isparta için kuvvetli kar yağışı uyarısı', None),
    ("Hava durumu uyarısı: Isparta'da sağanak bekleniyor", None),
    ('Isparta hava durumu: sarı kod verildi', None),
    ("Isparta'da hava soğudu", None),
])
def test_only_the_routine_weather_bulletin_is_held(title, reason):
    assert news_editorial_reason(news(title)) == reason


@pytest.mark.parametrize('title, description', [
    ('Isparta’da kan bağışı kampanyası (22 Kasım 2026)', 'Kampanya 12 Kasım 2026 tarihinde Kızılay çadırında yapıldı.'),
    ('Isparta’da kan bağışı kampanyası 22 Kasım 2026', 'Kampanya 22 Kasım 2025 tarihinde Kızılay çadırında yapıldı.'),
    ("22 Kasım'da kan bağışı kampanyası", 'Kampanya 21 Kasım Cumartesi günü Kızılay çadırında yapılacak.'),
    # 12 Nov 2026 was a Thursday, whatever the headline says.
    ('Isparta’da kan bağışı kampanyası', 'Kampanya 12 Kasım 2026 Pazar günü Kızılay çadırında yapıldı.'),
])
def test_contradictory_explicit_dates_are_held(title, description):
    item = news(title, description)
    assert date_mismatch(item)
    assert news_editorial_reason(item) == 'date_mismatch'


@pytest.mark.parametrize('title, description', [
    ("22 Kasım'da kan bağışı kampanyası", 'Kampanya 22 Kasım 2026 Pazar günü Kızılay çadırında yapılacak.'),
    ('Isparta’da kan bağışı kampanyası', 'Kampanya 12 Kasım 2026 Perşembe günü ve 20 Kasım’da yapıldı.'),
    ("22 Kasım'da kan bağışı kampanyası", 'Kampanya bugün Kızılay çadırında 22.11.2026 itibarıyla yapılacak.'),
    ('Pazar yeri 10 Kasım ve 12 Kasım günlerinde taşınacak', 'Esnaf 11 Kasım 2026 tarihinde bilgilendirildi.'),
    ("6 Mart Spor Salonu'nda Geri Sayım Sürüyor", 'Salonun açılışı 24 Kasım’da yapılacak, hazırlıklar sürüyor.'),
    ('Başkan’dan 10 Kasım mesajı', 'Atatürk’ü 10 Kasım 1938’de kaybettik; saygıyla anıyoruz dedi.'),
    ('Isparta’da Kış Lastiği Zorunluluğu 15 Kasım’da Başlıyor',
     'Uygulama 15 Kasım 2026 ile 1 Nisan 2027 arasında geçerli; kural 1 Nisan 2017’den beri uygulanıyor.'),
    ('Kampanya 18 Kasım 2026 pazar yerinde yapıldı', 'Etkinlik 18 Kasım 2026 günü pazar yerinde tamamlandı.'),
])
def test_consistent_or_unspecific_dates_are_not_held(title, description):
    assert not date_mismatch(news(title, description))


def test_research_never_queues_a_list_and_records_why(store):
    item = {**HABER32, 'sources': [HABER32['url']]}
    key, _ = store.upsert(item, AT.isoformat())
    prepare(store, AT)
    assert not [p for p in store.posts() if p.get('item_id') == key]
    held = store.rows('SELECT reason FROM withheld WHERE id=?', (digest(key + ':editorial'),))
    assert held == [{'reason': 'dedicated_pharmacy_story'}]
    holds = summary(store, AT)['editorial_holds']
    assert holds['dedicated_pharmacy_story'] == 1 and holds['date_mismatch'] == 0


def test_a_card_queued_before_the_gate_is_blocked_at_research_and_publication(store):
    listing = {**HABER32, 'sources': [HABER32['url']]}
    other = news('Isparta’da yeni otopark hizmete açıldı',
                 'Belediye, şehir merkezinde 173 araçlık yeni otoparkı hizmete açtı ve ücretsiz olacağını söyledi.',
                 url='https://www.haber32.com.tr/otopark-1')
    keys = {}
    for name, value in (('listing', listing), ('other', other)):
        keys[name], _ = store.upsert(value, AT.isoformat())
        # The queue as an older release left it: a ready card for each article.
        queue_item(store, {**value, 'id': keys[name], 'revision': 1}, 'news', AT, AT)
    card = next(p for p in store.posts() if p['item_id'] == keys['listing'])
    items = {i['id']: i for i in store.items()}
    assert publication_copy_reason(card, items) == 'editorial_review_required'
    api = adapter()
    result = publish_one(store, AT + timedelta(minutes=5), 'https://example.org/', assets_for(store), adapter=api)
    status = {p['item_id']: p['status'] for p in store.posts() if not p.get('publish_format')}
    assert status[keys['listing']] == 'blocked_source'
    assert result['status'] == 'published' and status[keys['other']] == 'published'
    published = [p for p in store.posts() if p['status'] == 'published']
    assert {p['item_id'] for p in published} == {keys['other']}
