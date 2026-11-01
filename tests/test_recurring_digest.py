"""A digest and a queued story must survive what happens to their neighbours."""
from datetime import timedelta

import pytest

from news_engine.domain import digest
from news_engine.instagram import prepare_story_jobs, publish_outage_story
from news_engine.schedule import prepare
from test_outage_stories import AT, SITE, api, outage, store


def session(day, hour, name):
    url = 'https://example.org/concert'
    return {'kind':'event','identity':f'{url}-{name}','title':'Isparta konseri','description':'Kaynak konseri duyurdu.',
            'url':url,'sources':[url],'source_id':'example','source_name':'Yerel kaynak','category':'concert',
            'start':day.replace(hour=hour).isoformat(),'end':day.replace(hour=hour+2).isoformat(),
            'status':'scheduled','time_known':True,'location':'Isparta'}


@pytest.mark.parametrize('stale_first',[False,True])
def test_stale_session_on_the_same_url_cannot_block_a_digest(store,stale_first):
    day=AT+timedelta(days=2)
    current,stale=session(day,14,'current'),session(day,17,'stale')
    writes=[(current,AT),(stale,AT-timedelta(hours=8))]
    for item,seen in reversed(writes) if stale_first else writes:
        store.upsert(item,seen.isoformat())
    prepare(store,AT)
    weekly=next(p for p in store.posts() if p['kind']=='weekly')
    assert weekly['status']=='prepared' and len(weekly['event_ids'])==1
    prepare(store,AT+timedelta(minutes=8),refresh_digests=False)
    assert next(p for p in store.posts() if p['id']==weekly['id'])['status']=='prepared'


def test_digest_still_stops_when_its_own_event_goes_stale(store):
    store.upsert(session(AT+timedelta(days=2),14,'current'),AT.isoformat())
    prepare(store,AT)
    prepare(store,AT+timedelta(hours=2),refresh_digests=False)
    assert next(p for p in store.posts() if p['kind']=='weekly')['status']=='blocked_source'


def queued_outage(store):
    assets=outage(store,AT)
    prepare_story_jobs(store,assets)
    parent=next(p for p in store.posts() if not p.get('publish_format') and p['category']=='outage')
    return assets,parent['id'],digest(parent['id']+':story:0')


def status(store,key):
    return store.rows('SELECT status FROM posts WHERE id=?',(key,))[0]['status']


def test_briefly_blocked_parent_keeps_its_story(store):
    assets,parent,story=queued_outage(store)
    with store.db:
        store.db.execute("UPDATE posts SET status='blocked_source' WHERE id=?",(parent,))
    prepare_story_jobs(store,assets)
    assert status(store,story)!='superseded'


def test_story_lost_to_a_past_block_returns_with_its_prepared_parent(store):
    assets,parent,story=queued_outage(store)
    with store.db:
        store.db.execute("UPDATE posts SET status='superseded' WHERE id=?",(story,))
    assert publish_outage_story(store,AT,SITE,assets,api())['status']=='published'
    assert status(store,story)=='published'


@pytest.mark.parametrize('claimed',['published','blocked_source'])
def test_dropped_story_stays_dropped_unless_its_parent_is_waiting(store,claimed):
    assets,parent,story=queued_outage(store)
    with store.db:
        store.db.execute("UPDATE posts SET status='superseded' WHERE id=?",(story,))
        store.db.execute('UPDATE posts SET status=? WHERE id=?',(claimed,parent))
    prepare_story_jobs(store,assets)
    assert status(store,story)=='superseded'
