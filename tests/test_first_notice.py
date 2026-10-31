import json
from datetime import timedelta

import pytest

from news_engine.domain import parse_date
from news_engine.schedule import prepare
from news_engine.store import Store

AT = parse_date('2026-11-01T10:00:00+03:00')


@pytest.fixture
def store(tmp_path):
    value = Store(tmp_path/'state.sqlite')
    yield value
    value.close()


def concert(**values):
    start = AT + timedelta(days=3)
    return {'kind': 'event', 'identity': 'https://example.org/#1', 'title': 'Ozbi Konseri',
            'description': 'Ozbi Isparta sahnesinde şarkılarını seslendirecek.', 'url': 'https://example.org/ozbi',
            'sources': ['https://example.org/ozbi'], 'source_id': 'biletinial-isparta', 'source_name': 'Biletinial',
            'category': 'concert', 'start': start.isoformat(), 'end': start.isoformat(), 'status': 'scheduled',
            'time_known': True, 'location': 'Isparta Holly Stone', 'price': '900.0', 'currency': 'TRY',
            'price_basis': 'listed_session_price_subject_to_ticket_conditions', **values}


def kinds(store):
    return {p['kind']: p['status'] for p in store.posts() if not p.get('publish_format')}


def test_a_lifted_hold_is_not_a_change_to_the_event(store):
    key, _ = store.upsert(concert(), AT.isoformat())
    store.upsert(concert(verification_holds=['not_reobserved_current_run']), AT.isoformat())
    store.upsert(concert(), AT.isoformat())
    assert next(i for i in store.items() if i['id'] == key)['revision'] == 1


def test_revised_event_nobody_was_told_about_stays_a_first_notice(store):
    store.upsert(concert(), AT.isoformat())
    store.upsert(concert(location='Isparta Holly Stone Salonu'), AT.isoformat())
    prepare(store, AT)
    assert kinds(store)['announcement'] == 'prepared' and 'update' not in kinds(store)


def test_earlier_update_draft_of_an_unannounced_event_is_withdrawn(store):
    key, _ = store.upsert(concert(), AT.isoformat())
    store.upsert(concert(location='Isparta Holly Stone Salonu'), AT.isoformat())
    store.queue({'id': 'a'*24, 'item_id': key, 'revision': 2, 'kind': 'update', 'due_at': AT.isoformat(),
                 'title': 'Etkinlik bilgisi güncellendi: Ozbi Konseri', 'slides': []})
    prepare(store, AT)
    assert kinds(store)['update'] == 'superseded'


def test_a_change_to_an_announced_event_is_still_an_update(store):
    key, _ = store.upsert(concert(), AT.isoformat())
    prepare(store, AT)
    post = next(p for p in store.posts() if p['kind'] == 'announcement')
    with store.db:
        store.db.execute("UPDATE posts SET status='published',payload=? WHERE id=?",
                         (json.dumps({**post, 'published_at': AT.isoformat()}), post['id']))
    store.upsert(concert(location='Isparta Holly Stone Salonu'), AT.isoformat())
    prepare(store, AT)
    assert kinds(store)['update'] == 'prepared'


def test_price_reads_as_a_whole_number_on_the_card(store):
    store.upsert(concert(), AT.isoformat())
    prepare(store, AT)
    post = next(p for p in store.posts() if p['kind'] == 'announcement')
    assert 'Listelenen bilet: 900 TL' in post['slides'][0]['body']
    assert 'Listelenen seans bileti: 900 TL' in post['caption']
