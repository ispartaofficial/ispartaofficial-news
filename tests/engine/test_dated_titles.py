"""News titles tied to one named day stop at the end of that day."""
from datetime import timedelta

import pytest

from news_engine.schedule import prepare
from news_engine.timeliness import publication_reason


def day_news(at, title, **changes):
    return {'kind': 'news', 'title': title, 'category': 'news',
            'description': 'Isparta’da yapılan açıklamada vatandaşlara bilgi verildi.',
            'url': 'https://www.isparta.bel.tr/haber/1', 'sources': ['https://www.isparta.bel.tr/haber/1'],
            'source_id': 'isparta-belediye', 'source_name': 'Belediye',
            'published_at': (at - timedelta(hours=1)).isoformat(), **changes}


@pytest.mark.parametrize('title', [
    "Isparta'da Atatürk anısına 10 Ekim'de sirenler çalacak",
    'Yeni Parti Isparta’dan 10 Ekim anma mesajı',
    'İL BAŞKANINDAN 10 EKİM MESAJI',
    '10 Ekimde pazar yeri taşınacak',
])
def test_title_tied_to_one_day_expires_when_the_day_is_over(at, title):
    item = day_news(at, title)
    assert publication_reason(item, at) is None
    assert publication_reason(item, at.replace(hour=23, minute=59)) is None
    next_day = at.replace(hour=0, minute=1) + timedelta(days=1)
    assert publication_reason(item, next_day) == 'expired_dated_news'


@pytest.mark.parametrize('title', [
    "10 Ekim'de düzenlenen törende ödüller verildi",
    'Isparta’da sirenler çalacak',
    'Pazar yeri 10 Ekim ve 12 Ekim günlerinde taşınacak',
    '40 Ekim mesajı',
])
def test_past_tense_undated_or_several_day_titles_keep_the_48_hour_limit(at, title):
    item = day_news(at, title)
    assert publication_reason(item, at + timedelta(hours=30)) is None


def test_named_day_across_the_new_year_uses_the_nearest_year(at):
    published = at.replace(month=12, day=31, hour=9)
    item = day_news(at, "1 Ocak'ta yeni yıl konseri verilecek", published_at=published.isoformat())
    assert publication_reason(item, published.replace(year=2027, month=1, day=1, hour=10)) is None
    assert publication_reason(item, published.replace(year=2027, month=1, day=2, hour=0, minute=30)) == 'expired_dated_news'


def test_prepared_post_of_a_passed_day_expires(store, at):
    item = day_news(at, 'Yeni Parti Isparta’dan 10 Ekim anma mesajı')
    key, _ = store.upsert(item, at.isoformat())
    prepare(store, at)
    news = [post for post in store.posts() if post['item_id'] == key and post['kind'] == 'news']
    assert news and news[0]['status'] == 'prepared'
    prepare(store, at.replace(hour=8) + timedelta(days=1))
    assert {post['status'] for post in store.posts() if post['item_id'] == key} == {'expired'}
