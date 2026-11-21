"""A full cache of old published photographs must not stop every new draft (17-22 Nov)."""
import io
import json
from contextlib import closing
from datetime import timedelta

import pytest
from PIL import Image

from isparta.runtime import sources_for_engine
from news_engine.domain import parse_date
from news_engine.source_photos import SourcePhotos, cleaned_photo, photo_subject
from news_engine.store import Store
from news_engine.visual_gate import fingerprint

AT = parse_date('2026-11-22T10:00:00+03:00')
CDN = 'https://haber32comtr.teimg.com/haber32-com-tr/uploads/2026/11/'


def source():
    return sources_for_engine({'sources': [{'id': 'haber32', 'name': 'Haber32',
        'url': 'https://www.haber32.com.tr/', 'research_enabled': True, 'reader': 'article',
        'title_selector': 'h1', 'body_selector': '.article-text', 'date_selector': 'meta[name=datePublished]'}]})[0]


def photo(n):
    out = io.BytesIO()
    Image.new('RGB', (1024, 768), ((37 * n) % 256, (91 * n) % 256, (53 * n + 17) % 256)).save(out, 'JPEG')
    return cleaned_photo(out.getvalue())


def article(store, n):
    url = f'https://www.haber32.com.tr/isparta-belediyesi-calisma-{n}'
    store.upsert({'kind': 'news', 'title': f'Isparta Belediyesi yeni çalışmayı tamamladı {n}',
                  'description': 'Isparta Belediyesi ekipleri mahallede yürüttüğü çalışmayı tamamladı.',
                  'source_id': 'haber32', 'source_name': 'Haber32', 'url': url, 'sources': [url],
                  'category': 'news', 'published_at': (AT - timedelta(days=5)).isoformat()}, AT.isoformat())
    return next(i for i in store.items() if i['url'] == url)


def card(store, item, photos, status, published=None, n=0):
    """A news card bound to a freshly cached photograph of its own article."""
    image = photo(n)
    photos.results.pop(item['id'], None)
    key, _ = photos.bind(item, f'{CDN}photo-{n}.jpg', image, photo_subject(item))
    post = {'id': item['id'][:12] + 'c' * 12, 'item_id': item['id'], 'revision': item['revision'], 'kind': 'news',
            'due_at': AT.isoformat(), 'title': item['title'], 'source_photo_keys': {'0': key},
            'visual_review': {'images': {'0': fingerprint(image)}}}
    if published:
        post['published_at'] = published.isoformat()
    store.queue(post)
    with store.db:
        store.db.execute('UPDATE posts SET status=?,payload=? WHERE id=?', (status, json.dumps(post), post['id']))
    return key, image


@pytest.fixture
def full(tmp_path, monkeypatch):
    monkeypatch.setenv('SOURCE_PHOTOS_ENABLED', 'true')
    monkeypatch.setattr('news_engine.source_photos.MAX_CACHED_IMAGES', 4)
    store = Store(tmp_path / 'state.sqlite')
    photos = SourcePhotos(store, AT, tmp_path / 'photos', [source()])
    with closing(store):
        yield store, photos


def cached(store):
    return {row['id'] for row in store.rows('SELECT id FROM source_photos')}


def test_oldest_published_photo_gives_way_to_a_new_draft(full):
    store, photos = full
    oldest, _ = card(store, article(store, 1), photos, 'published', AT - timedelta(days=6), n=1)
    older, _ = card(store, article(store, 2), photos, 'published', AT - timedelta(days=3), n=2)
    recent, _ = card(store, article(store, 3), photos, 'published', AT - timedelta(hours=5), n=3)
    flight, _ = card(store, article(store, 4), photos, 'uncertain', AT - timedelta(days=9), n=4)
    assert len(cached(store)) == 4
    draft = article(store, 5)
    result = photos.bind(draft, CDN + 'photo-5.jpg', photo(5), photo_subject(draft))
    assert result
    # Exactly one slot is freed, from the card published longest ago.
    assert cached(store) == {older, recent, flight, result[0]}
    assert photos.stats['evicted'] == 1 and photos.stats['deferred'] == 0
    # Published claims keep their bindings and reviewed fingerprints.
    assert all(p['source_photo_keys'] for p in store.posts())


def test_recent_in_flight_and_draft_photos_are_never_evicted(full):
    store, photos = full
    card(store, article(store, 1), photos, 'published', AT - timedelta(hours=30), n=1)
    card(store, article(store, 2), photos, 'publishing', AT - timedelta(days=8), n=2)
    card(store, article(store, 3), photos, 'uncertain', AT - timedelta(days=8), n=3)
    card(store, article(store, 4), photos, 'prepared', n=4)
    before = cached(store)
    a = article(store, 5)
    assert photos.bind(a, CDN + 'photo-5.jpg', photo(5), photo_subject(a)) is None
    assert cached(store) == before
    assert photos.stats['deferred'] == 1 and photos.stats['evicted'] == 0


def test_evicted_published_photo_still_cannot_be_reused_by_another_article(full):
    store, photos = full
    _, image = card(store, article(store, 1), photos, 'published', AT - timedelta(days=6), n=1)
    for n in (2, 3, 4):
        card(store, article(store, n), photos, 'published', AT - timedelta(days=4), n=n)
    a = article(store, 5)
    assert photos.bind(a, CDN + 'photo-5.jpg', photo(5), photo_subject(a))
    assert photos.stats['evicted'] == 1
    # The first card's row is gone; its reviewed fingerprint still owns the picture.
    a = article(store, 6)
    with pytest.raises(ValueError, match='reused'):
        photos.bind(a, CDN + 'photo-6.jpg', image, photo_subject(a))


def test_evicted_published_card_renders_without_its_photograph(full, tmp_path):
    from news_engine.render import render_post
    store, photos = full
    item = article(store, 1)
    key, _ = card(store, item, photos, 'published', AT - timedelta(days=6), n=1)
    for n in (2, 3, 4):
        card(store, article(store, n), photos, 'published', AT - timedelta(days=4), n=n)
    a = article(store, 5)
    assert photos.bind(a, CDN + 'photo-5.jpg', photo(5), photo_subject(a))
    post = next(p for p in store.posts() if p.get('item_id') == item['id'])
    assert key not in cached(store) and photos.for_post(post, {item['id']: item}) == {}
    post.update(slides=[{'title': item['title'], 'body': item['description']}], category='news',
                caption=item['title'], source_urls=[item['url']])
    assets = render_post(post, tmp_path / 'public', {})
    assert assets['feed'] and all((tmp_path / 'public' / path).exists() for path in assets['feed'])


def test_research_export_binds_a_new_draft_once_old_cards_fill_the_cache(tmp_path, monkeypatch):
    """End to end: the old card's pixels give way and the new draft clears the visual gate."""
    from unittest.mock import Mock
    from test_real_photo_first import LOCAL, add, jpeg, page
    from news_engine.pipeline import _export
    from news_engine.schedule import queue_item
    from news_engine.visual_policy import image_reason
    monkeypatch.setenv('SOURCE_PHOTOS_ENABLED', 'true')
    monkeypatch.setattr('news_engine.source_photos.validate_news_photo', lambda *args: None)
    monkeypatch.setattr('news_engine.source_photos.MAX_CACHED_IMAGES', 1)
    first_at, later = parse_date('2026-11-18T15:00:00+03:00'), parse_date('2026-11-21T15:00:00+03:00')
    pictures = {'https://paper.example/u/yol.jpg': jpeg('#a02020'), 'https://paper.example/u/park.jpg': jpeg('#2040a0')}
    fetcher = Mock()
    fetcher.image.side_effect = lambda url: (pictures[url], url)
    monkeypatch.setattr('news_engine.source_photos.Fetcher', lambda sources: fetcher)
    with closing(Store(tmp_path / 'state.sqlite')) as store:
        old = add(store, LOCAL, 'yol', 'Isparta çevre yolu hizmete açıldı', published_at='2026-11-18T14:30:00+03:00')
        queue_item(store, old, 'news', first_at, first_at)
        fetcher.get.side_effect = lambda url: (page(old, '<img src="https://paper.example/u/yol.jpg" alt="Açılış">'), url)
        _export(store, tmp_path / 'first', [LOCAL], first_at)
        card = next(p for p in store.posts() if p.get('item_id') == old['id'])
        assert card['source_photo_keys'] and image_reason(card) is None
        card['published_at'] = first_at.isoformat()
        with store.db:
            store.db.execute("UPDATE posts SET status='published',payload=? WHERE id=?",
                             (json.dumps({k: v for k, v in card.items() if k != 'status'}), card['id']))
        new = add(store, LOCAL, 'park', 'Isparta merkezde yeni park hizmete açıldı', published_at='2026-11-21T14:30:00+03:00')
        queue_item(store, new, 'news', later, later)
        fetcher.get.side_effect = lambda url: (page(new, '<img src="https://paper.example/u/park.jpg" alt="Park">'), url)
        assets = _export(store, tmp_path / 'second', [LOCAL], later)
        draft = next(p for p in store.posts() if p.get('item_id') == new['id'])
        assert draft['status'] == 'prepared' and draft['source_photo_keys'] and image_reason(draft) is None
        published = next(p for p in store.posts() if p['id'] == card['id'])
        assert published['status'] == 'published' and published['source_photo_keys'] == card['source_photo_keys']
        assert [r['id'] for r in store.rows('SELECT id FROM source_photos')] == [draft['source_photo_keys']['0']]
        # The old card is not redrawn as a text-only image it never was.
        assert card['id'] not in assets