"""12 Nov: each new show on a ticket platform gets its own story, with its own poster.

Ezginin Günlüğü waited three days behind the news for a feed slot, and the
Biletinial theatre listing (13 shows) was not read at all.
"""
import io
import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import Image

from test_outage_stories import AT, SITE, api, news, outage, store  # noqa: F401
from isparta.runtime import TICKET_SOURCES, sources_for_engine
from news_engine.domain import digest
from news_engine.instagram import publish_automatic, publish_outage_story
from news_engine.publication_policy import EVENT_STORY_LIMIT, OUTAGE_STORY_LIMIT, event_story, story_only
from news_engine.schedule import prepare
from news_engine.source_photo_data import approved_image_url, same_event_artwork
from news_engine.source_photos import NoArticleImage, SourcePhotos, candidate_urls
from news_engine.visual_match import MatchRejected

SHOW = 'https://biletinial.com/tr-tr/tiyatro/perde-tuluat'
POSTER = 'https://b6s54eznn8xq.merlincdn.net/Uploads/Films/perde-tuluat-2026831933548f.jpg'
CONFIG = json.loads(Path('config/research-sources.json').read_text(encoding='utf-8'))
STAGE = next(s for s in sources_for_engine(CONFIG) if s['id'] == 'biletinial-isparta-sahne')


def show(store, at, name='Perde', days=10, url=SHOW, source='biletinial-isparta-sahne', hour=20):
    begin = (at + timedelta(days=days)).replace(hour=hour, minute=30)
    item = {'kind': 'event', 'identity': url + '#' + begin.isoformat(), 'title': name,
            'description': 'Biletli etkinlik.', 'url': url, 'sources': [url], 'source_id': source,
            'source_name': 'Biletinial', 'category': 'theatre', 'start': begin.isoformat(),
            'end': begin.isoformat(), 'status': 'scheduled', 'time_known': True,
            'location': 'Tulûat Sahne · Çünür · Isparta'}
    store.upsert(item, at.isoformat())
    prepare(store, at)
    return {p['id']: {'feed': [f"media/{p['id']}/feed-1.jpg"], 'story': [f"media/{p['id']}/story-1.jpg"]}
            for p in store.posts() if not p.get('publish_format')}


def test_the_theatre_listing_is_read_as_a_ticket_source():
    assert STAGE['url'] == 'https://biletinial.com/tr-tr/tiyatro/isparta' and STAGE['reader'] == 'listed_sessions'
    assert STAGE['event_category'] == 'theatre' and STAGE['id'] in TICKET_SOURCES
    assert STAGE['photo_identity_reader'] == 'isparta-source-images-v1'


@pytest.mark.parametrize('value,expected', [
    ({'kind': 'announcement', 'category': 'theatre', 'source_urls': [SHOW]}, True),
    ({'kind': 'announcement', 'category': 'concert', 'source_urls': ['https://www.bubilet.com.tr/isparta/etkinlik/a/seans/1']}, True),
    ({'kind': 'announcement', 'category': 'concert', 'source_urls': ['https://etkinlik.io/etkinlik/1/konser']}, True),
    ({'kind': 'announcement', 'category': 'education', 'source_urls': ['https://isparta.edu.tr/etkinlik/1']}, False),
    ({'kind': 'reminder_day', 'category': 'theatre', 'source_urls': [SHOW]}, False),
    ({'kind': 'news', 'category': 'culture', 'source_urls': ['https://biletinial.com.example.org/a']}, False),
])
def test_only_a_new_show_on_a_ticket_platform_is_an_event_story(value, expected):
    assert event_story(value) is expected and story_only(value) is expected


def test_a_new_show_goes_out_at_once_as_a_story_and_takes_no_feed_slot(store):
    assets = show(store, AT)
    adapter = api()
    parent = next(p for p in store.posts() if p['kind'] == 'announcement')
    assert parent['due_at'] == AT.isoformat()
    assert publish_automatic(store, AT, SITE, assets, adapter)['status'] == 'empty'
    assert publish_outage_story(store, AT, SITE, assets, adapter)['status'] == 'published'
    child = next(p for p in store.posts() if p['id'] == digest(parent['id'] + ':story:0'))
    assert child['status'] == 'published' and adapter.container.call_args.args[2] is True
    assert next(p for p in store.posts() if p['id'] == parent['id'])['status'] == 'prepared'
    # The same card is one story, however often the publisher runs.
    later = AT + timedelta(hours=2)
    assert publish_outage_story(store, later, SITE, assets, adapter)['status'] == 'empty'
    assert adapter.container.call_count == 1


def test_a_university_event_still_waits_for_its_feed_slot(store):
    assets = show(store, AT, name='Kariyer Günü', url='https://isparta.edu.tr/etkinlik/kariyer', source='isubu-events')
    parent = next(p for p in store.posts() if p['kind'] == 'announcement')
    assert parent['due_at'] > AT.isoformat() and not story_only(parent)
    assert publish_outage_story(store, AT, SITE, assets, api())['status'] == 'empty'


def test_shows_and_power_cuts_have_their_own_daily_stories(store):
    adapter = api()
    at = AT
    for number, name in enumerate(('Kadın', 'Çizmeli Kedi', 'İçimizdeki Şeytan', 'Yarım Kalan Aşklar')):
        assets = show(store, at, name=name, url=f'{SHOW}-{number}', days=10 + number)
    for name in ('Eğirdir', 'Yalvaç'):
        assets = outage(store, at, name, hours=9)
    assert len([p for p in store.posts() if event_story(p)]) == EVENT_STORY_LIMIT + 1

    def seen(moment):
        # Each research run re-observes its sources; a story needs current evidence.
        with store.db:
            store.db.execute('UPDATE items SET last_seen=?', (moment.isoformat(),))
        prepare(store, moment)
    statuses = []
    for _ in range(EVENT_STORY_LIMIT + OUTAGE_STORY_LIMIT + 1):
        statuses.append(publish_outage_story(store, at, SITE, assets, adapter)['status'])
        at += timedelta(minutes=50)
        seen(at)
    published = [p for p in store.posts() if p.get('publish_format') == 'story' and p['status'] == 'published']
    assert statuses.count('published') == EVENT_STORY_LIMIT + OUTAGE_STORY_LIMIT and statuses[-1] == 'daily_limit'
    assert sum(event_story(p) for p in published) == EVENT_STORY_LIMIT
    assert sum(p['category'] == 'outage' for p in published) == OUTAGE_STORY_LIMIT
    # Tomorrow the show that was left over gets its story.
    tomorrow = (AT + timedelta(days=1)).replace(hour=9)
    seen(tomorrow)
    assert publish_outage_story(store, tomorrow, SITE, assets, adapter)['status'] == 'published'


def jpeg(size=(800, 1100), color='#553311'):
    raw = io.BytesIO()
    Image.new('RGB', size, color).save(raw, 'JPEG')
    return raw.getvalue()


def page(start='2026-11-14T20:30:00+03:00', image=POSTER, title='Perde'):
    event = {'@context': 'https://schema.org', '@type': 'Event', 'name': title, 'startDate': start, 'endDate': start,
             'eventStatus': 'https://schema.org/EventScheduled', 'description': 'Tek perdelik oyun.',
             'location': {'@type': 'Place', 'name': 'Tulûat Sahne',
                          'address': {'@type': 'PostalAddress', 'streetAddress': 'Çünür', 'addressRegion': 'Isparta'}},
             'offers': {'@type': 'Offer', 'price': 250, 'priceCurrency': 'TRY', 'availability': 'https://schema.org/InStock'}}
    if image:
        event['image'] = image
    return (f'<h1>{title}</h1><script type="application/ld+json">{json.dumps(event)}</script>'
            '<p>14 Kasım Cumartesi · 20:30 Tulûat Sahne</p>')


def session(start='2026-11-14T20:30:00+03:00'):
    return {'id': digest(SHOW + start), 'revision': 1, 'kind': 'event', 'category': 'theatre', 'title': 'Perde',
            'source_id': STAGE['id'], 'source_name': 'Biletinial', 'url': SHOW, 'sources': [SHOW], 'start': start,
            'end': start, 'status': 'scheduled', 'time_known': True, 'location': 'Tulûat Sahne · Çünür · Isparta',
            'description': 'Tek perdelik oyun.'}


def test_the_sessions_own_poster_is_bound_from_its_schema():
    assert approved_image_url(STAGE['id'], SHOW, POSTER)
    assert not approved_image_url(STAGE['id'], SHOW, POSTER.replace('/Uploads/Films/', '/Uploads/Other/'))
    assert not approved_image_url('haber32', 'https://www.haber32.com.tr/a', POSTER)
    assert candidate_urls(page(), SHOW, session(), STAGE) == [POSTER]
    with pytest.raises(NoArticleImage):
        candidate_urls(page(image=None), SHOW, session(), STAGE)
    for wrong in (page(start='2026-11-15T20:30:00+03:00'), page(image='https://other.example/poster.jpg')):
        with pytest.raises(ValueError) as refusal:
            candidate_urls(wrong, SHOW, session(), STAGE)
        assert not isinstance(refusal.value, NoArticleImage)


def photos(store, tmp_path, monkeypatch, html):
    monkeypatch.setenv('SOURCE_PHOTOS_ENABLED', 'true')
    fetcher = Mock()
    fetcher.get.return_value = (html, SHOW)
    fetcher.image.return_value = (jpeg(), POSTER)
    return SourcePhotos(store, AT, tmp_path / 'photos', [STAGE], fetcher=fetcher), fetcher


@pytest.mark.parametrize('failure', ['unreadable_title', 'no_ocr'])
def test_a_poster_the_checks_cannot_read_is_still_the_shows_image(store, tmp_path, monkeypatch, failure):
    from news_engine.image_safety import IllustrationCheckUnavailable
    error = MatchRejected('Source poster title unreadable') if failure == 'unreadable_title' else IllustrationCheckUnavailable()
    monkeypatch.setattr('news_engine.event_image_text.validate', Mock(side_effect=error))
    reader, _ = photos(store, tmp_path, monkeypatch, page())
    item = session()
    post = {'id': 'a' * 24, 'item_id': item['id'], 'revision': 1, 'status': 'prepared'}
    assert list(reader.for_post(post, {item['id']: item})) == [0] and not reader.awaits_original(post, {item['id']: item})
    assert json.loads(store.rows('SELECT payload FROM source_photos')[0]['payload'])['image_url'] == POSTER


def test_two_sessions_of_one_show_share_its_poster(store, tmp_path, monkeypatch):
    monkeypatch.setattr('news_engine.event_image_text.validate', lambda *args, **kwargs: True)
    first, second = session(), session('2026-11-27T20:30:00+03:00')
    reader, fetcher = photos(store, tmp_path, monkeypatch, page())
    assert reader.image(first)
    key = store.rows('SELECT id FROM source_photos')[0]['id']
    evidence = json.loads(store.rows('SELECT payload FROM source_photos')[0]['payload'])
    # The first session's story is out; its poster is frozen with that card.
    store.queue({'id': 'b' * 24, 'kind': 'announcement', 'revision': 1, 'due_at': AT.isoformat(), 'title': 'Perde',
                 'item_id': first['id'], 'source_photo_keys': {'0': key}})
    with store.db:
        store.db.execute("UPDATE posts SET status='published' WHERE id=?", ('b' * 24,))
    fetcher.get.return_value = (page(start=second['start']).replace('14 Kasım Cumartesi', '27 Kasım Cuma'), SHOW)
    assert reader.image(second) and len(store.rows('SELECT * FROM source_photos')) == 2
    assert same_event_artwork(evidence, second)
    assert not same_event_artwork(evidence, {**second, 'url': SHOW + '-baska', 'title': 'Perde'})


@pytest.mark.parametrize('case', ['unreadable_poster', 'unknown_session'])
def test_a_show_waits_without_a_scene_while_its_poster_may_exist(store, tmp_path, monkeypatch, case):
    import requests
    reader, fetcher = photos(store, tmp_path, monkeypatch, page() if case == 'unreadable_poster' else page(start='2026-11-15T20:30:00+03:00'))
    fetcher.image.side_effect = requests.HTTPError('403')
    item = session()
    post = {'id': 'a' * 24, 'item_id': item['id'], 'revision': 1, 'status': 'prepared'}
    assert reader.for_post(post, {item['id']: item}) == {} and reader.awaits_original(post, {item['id']: item})


def test_a_show_without_any_poster_may_get_a_scene(store, tmp_path, monkeypatch):
    reader, _ = photos(store, tmp_path, monkeypatch, page(image=None))
    item = session()
    post = {'id': 'a' * 24, 'item_id': item['id'], 'revision': 1, 'status': 'prepared'}
    assert reader.for_post(post, {item['id']: item}) == {} and not reader.awaits_original(post, {item['id']: item})
