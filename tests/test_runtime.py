"""Isparta full-source boundary + reused engine, real SQLite/JPEG, no Meta writes."""
from copy import deepcopy
from contextlib import closing
from datetime import timedelta
import json
from pathlib import Path
import sqlite3
from unittest.mock import Mock

import pytest
from PIL import Image

from isparta import runtime
from isparta.research import public_report
from news_engine.domain import digest, parse_date
from news_engine.security import validate_public, validate_state
from news_engine.store import Store
from news_engine.text_quality import TextRenderError

AT = parse_date('2026-10-22T07:20:00+03:00')


def setup(tmp_path):
    config={'sources':[{'id':'sdu-calendar','name':'Örnek resmî takvim','url':'https://example.org/',
                        'research_enabled':True,'reader':'sdu'}]}
    path=tmp_path/'sources.json';path.write_text(json.dumps(config),encoding='utf-8')
    row={'id':'a'*24,'kind':'event','source_id':'sdu-calendar','source_name':'Örnek resmî takvim',
         'url':'https://example.org/duyuru','title':'Isparta tiyatro buluşması',
         'description':'Tiyatro gösterimi herkese açıktır. Ücretsiz etkinlik için kayıt gerekmiyor.',
         'category':'theatre','start':'2026-10-24T20:00:00+03:00','end':'2026-10-24T22:00:00+03:00',
         'time_known':True,'location':'Isparta Kültür Merkezi','organizer':'Örnek organizatör',
         'audience':{'kind':'public','evidence':'Tiyatro gösterimi herkese açıktır.'},
         'fee':'Ücretsiz','holds':[],'eligible_for_drafting':True,'publication_ready':False,
         'image_status':'not_reviewed','checked_at':AT.isoformat()}
    collection={'checked_at':AT.isoformat(),'items':[row],
                'source_health':[{'id':'sdu-calendar','status':'parsed','parsed_items':1,'errors':[]}],
                'summary':{'publication_ready':0},'publishing_enabled':False}
    return path,collection


def test_source_to_persistent_queue_caption_and_actual_jpegs(tmp_path, monkeypatch):
    monkeypatch.delenv('ILLUSTRATIONS_ENABLED',raising=False)
    path,collection=setup(tmp_path)
    db=tmp_path/'state/platform.sqlite';public=tmp_path/'public'
    first=runtime.run(db,public,path,at=AT,collection=collection)
    assert first['engine']['accepted_items']==1
    assert first['engine']['rendered_parents']>=1
    assert first['publishing_enabled'] is False and 'description' not in first['items'][0]
    assert 'description' in collection['items'][0]  # Public redaction doesn't mutate evidence.
    manifest=json.loads((public/'data.json').read_text(encoding='utf-8'))
    assert manifest['brand']['version']=='isparta-rose-v1'
    with closing(Store(db)) as store:
        parent=next(p for p in store.posts() if p['kind']=='announcement')
        before=deepcopy(parent)
        assert 'Kaynak: Örnek resmî takvim\nhttps://example.org/duyuru' in parent['caption']
        assert 'Katılım: Tiyatro gösterimi herkese açıktır.' in parent['caption']
        assert parent['caption'].endswith('#isparta #tiyatro #tiyatrooyunu #etkinlik #ispartaofficial')
        assert len(parent['slides'])==1
        entry=next(p for p in manifest['posts'] if p['id']==parent['id'])
        assert len(entry['assets']['feed'])==len(entry['assets']['story'])==1
        for fmt,size in [('feed',(1080,1350)),('story',(1080,1920))]:
            with Image.open(public/entry['assets'][fmt][0]) as im:assert im.size==size
        before_count=len(store.posts())
    runtime.run(db,public,path,at=AT,collection=collection)
    store=Store(db)
    try:
        assert len(store.posts())==before_count
        parent=next(p for p in store.posts() if p['id']==before['id'])
        assert parent['revision']==before['revision']
        assert store.rows('SELECT COUNT(*) AS n FROM facebook_deliveries')==[{'n':0}]
        assert not any(p.get('media_id') for p in store.posts())
    finally:store.close()
    validate_state(db);validate_public(public)


@pytest.mark.parametrize('hold',['event_ended','sensitive_claim_requires_review','participation_conditions_unknown'])
def test_new_source_hold_revokes_recent_preparation_without_rewriting_claim(tmp_path,hold):
    path,collection=setup(tmp_path);db=tmp_path/'state.sqlite';public=tmp_path/'public'
    runtime.run(db,public,path,at=AT,collection=collection)
    store=Store(db)
    old=store.posts()[0]
    with store.db:store.db.execute("UPDATE posts SET status='uncertain' WHERE id=?",(old['id'],))
    frozen=store.rows('SELECT * FROM posts WHERE id=?',(old['id'],))[0]
    store.close()
    collection['items'][0].update(holds=[hold],eligible_for_drafting=False)
    runtime.run(db,public,path,at=AT,collection=collection)
    store=Store(db)
    try:
        assert not any(p['status']=='prepared' for p in store.posts())
        assert store.rows('SELECT * FROM posts WHERE id=?',(old['id'],))[0]==frozen
    finally:store.close()


def test_removed_or_not_reobserved_event_does_not_keep_recent_approval(tmp_path):
    path,collection=setup(tmp_path);db=tmp_path/'state.sqlite';public=tmp_path/'public'
    runtime.run(db,public,path,at=AT,collection=collection)
    collection['items']=[]
    runtime.run(db,public,path,at=AT,collection=collection)
    store=Store(db)
    try:assert not any(p['status']=='prepared' for p in store.posts())
    finally:store.close()


def test_public_excerpt_is_rejected_as_full_source_and_foreign_database_refused(tmp_path):
    _,collection=setup(tmp_path)
    with pytest.raises(ValueError,match='Full source'):runtime.adapt(public_report(collection)['items'][0])
    foreign=tmp_path/'foreign.sqlite'
    with sqlite3.connect(foreign) as db:db.execute('CREATE TABLE posts(id TEXT)')
    before=foreign.read_bytes()
    with pytest.raises(ValueError,match='Foreign'):Store(foreign)
    assert foreign.read_bytes()==before


def test_unconfigured_publish_never_contacts_meta_or_opens_state(tmp_path,monkeypatch):
    api=Mock(side_effect=AssertionError('Unexpected Meta adapter'))
    monkeypatch.setattr('news_engine.instagram.Instagram',api)
    assert runtime.publish(tmp_path/'missing.sqlite',tmp_path/'missing-public')=={'status':'disabled'}
    api.assert_not_called()
    assert not (tmp_path/'missing.sqlite').exists()


def test_ticket_price_currency_and_access_condition_survive_adapter(tmp_path):
    _,collection=setup(tmp_path);row=collection['items'][0]
    row.update(price=536,currency='TRY',fee='Kaynak seans fiyatı: 536 TL',
               audience={'kind':'ticketed','evidence':'Etkinlik 18 yaş ve üzeri katılımcılara açıktır; bilet gereklidir.'})
    item=runtime.adapt(row)
    assert item['price']=='536' and item['currency']=='TRY'
    assert '18 yaş' in item['participation'] and 'bilet' in item['participation']


def test_access_rules_and_venue_do_not_invent_show_genre(tmp_path):
    _,collection=setup(tmp_path);row=collection['items'][0]
    row.update(title='Eser Yenenler ile İtiraf Et',
               description='Tiyatro salonuna girişte bilet gereklidir.',location='Isparta Tiyatro Salonu')
    assert runtime.category(row)=='event'


def test_all_conditional_age_limits_are_preserved_or_held(tmp_path):
    _,collection=setup(tmp_path);row=collection['items'][0]
    evidence='Çekim yapılmayan gösterilerde 16 yaş sınırı vardır. Çekim yapılan gösterilerde ise 18 yaş sınırı vardır.'
    row['audience']={'kind':'ticketed','evidence':evidence}
    assert runtime.adapt(row)['participation']==evidence
    row['audience']['evidence']=evidence*8
    assert 'participation_conditions_exceed_card_budget' in runtime.adapt(row)['verification_holds']


def test_obituary_cannot_enter_automatic_preparation(tmp_path):
    from isparta.research import assess
    from news_engine.editor import verify
    _,collection=setup(tmp_path);row=collection['items'][0]
    row.update(kind='news',title="Isparta'da bugün kaybettiklerimiz",published_at=AT.isoformat())
    assert 'sensitive_claim_requires_review' in assess(row,AT,[])['holds']
