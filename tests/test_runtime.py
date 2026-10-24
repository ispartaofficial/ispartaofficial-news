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
    (tmp_path/'config').mkdir()
    (tmp_path/'config/runtime.json').write_text('{"publishing_enabled":false,"meta_connected":false}')
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    api=Mock(side_effect=AssertionError('Unexpected Meta adapter'))
    monkeypatch.setattr('news_engine.instagram.Instagram',api)
    assert runtime.publish(tmp_path/'missing.sqlite',tmp_path/'missing-public')=={'status':'disabled'}
    api.assert_not_called()
    assert not (tmp_path/'missing.sqlite').exists()


def test_news_category_uses_headline_not_incidental_sports_or_traffic_detail():
    assert runtime.category({'kind':'news','title':"TOKİ Isparta'da arsa satışı yapacak!",
                             'source_id':'bomba32','description':'Bölgede spor tesisleri ve trafik düzenlemesi de yer alıyor.'})=='news'
    assert runtime.category({'kind':'news','title':'Isparta trafik düzenlemesi açıklandı',
                             'source_id':'bomba32','description':'Spor salonuna giden sokakta değişiklik var.'})=='transport'


@pytest.mark.parametrize('check_failure',[None,'model_unavailable','subject_rejected','ocr_unavailable','poster_date_mismatch'])
def test_source_only_photo_rebinds_existing_text_card_without_generation(tmp_path,monkeypatch,check_failure):
    import hashlib
    import io
    from news_engine.source_photos import SourcePhotos
    path,collection=setup(tmp_path);db=tmp_path/'state.sqlite';public=tmp_path/'public'
    monkeypatch.setenv('ILLUSTRATIONS_ENABLED','false')
    monkeypatch.setenv('SOURCE_PHOTOS_ENABLED','false')
    runtime.run(db,public,path,at=AT,collection=collection)
    old=json.loads((public/'data.json').read_text(encoding='utf-8'))
    old_review=old['posts'][0]['visual_review']
    pixels=io.BytesIO();Image.new('RGB',(1080,720),'#574028').save(pixels,'JPEG')
    config=json.loads(path.read_text(encoding='utf-8'))
    config['sources'][0]['url']='https://example.org/duyuru'
    path.write_text(json.dumps(config),encoding='utf-8')
    html='''<div class="modal-body"><img src="/tiyatro.jpg"><table>
        <tr><th>Etkinlik Adı</th><td>Isparta tiyatro buluşması</td></tr>
        <tr><th>Etkinlik Tarihi</th><td>24.10.2026</td></tr>
        <tr><th>Açıklama</th><td>Tiyatro gösterimi herkese açıktır.<br>
        Saat: 20:00–22:00<br>Yer: Isparta Kültür Merkezi</td></tr>
        </table></div>'''
    fetcher=Mock();fetcher.get.return_value=(html,'https://example.org/duyuru')
    fetcher.image.return_value=(pixels.getvalue(),'https://example.org/tiyatro.jpg')
    monkeypatch.setattr('news_engine.source_photos.Fetcher',lambda sources:fetcher)
    checked=[]
    def check_text(raw,item,**kwargs):
        from news_engine.image_safety import IllustrationCheckUnavailable
        checked.append('ocr')
        if check_failure=='ocr_unavailable':raise IllustrationCheckUnavailable()
        if check_failure=='poster_date_mismatch':raise ValueError('Poster date mismatch')
    def check_subject(raw,topic):
        from news_engine.visual_match import MatchUnavailable,MatchRejected
        checked.append(topic)
        if check_failure=='model_unavailable':raise MatchUnavailable()
        if check_failure=='subject_rejected':raise MatchRejected()
    monkeypatch.setattr('news_engine.event_image_text.validate',check_text)
    monkeypatch.setattr('news_engine.visual_match.validate_event_photo',check_subject)
    monkeypatch.setenv('SOURCE_PHOTOS_ENABLED','true')
    runtime.run(db,public,path,at=AT,collection=collection)
    manifest=json.loads((public/'data.json').read_text(encoding='utf-8'))
    entry=manifest['posts'][0];review=entry['visual_review']
    if check_failure:
        assert not review['images']
        assert review['edition']==old_review['edition']
        assert manifest['source_photos']['downloaded']==0
        assert manifest['source_photos']['unavailable' if check_failure.endswith('unavailable') else 'rejected']==1
        assert manifest['illustrations']['attempted']==0
        with closing(Store(db)) as store:
            assert store.rows('select count(*) as n from source_photos')==[{'n':0}]
        return
    assert checked==['ocr','theatre']
    assert review['images'] and review['edition']!=old_review['edition']
    for file,sha in review['assets'].items():
        assert hashlib.sha256((public/file).read_bytes()).hexdigest()==sha.replace(':','')
    assert manifest['source_photos']['downloaded']==1
    assert manifest['illustrations']['enabled'] is False and manifest['illustrations']['attempted']==0
    # A publisher has neither model nor generation setup. It must consume the
    # persisted, checked pixels/proof rather than substitute a text-only render.
    monkeypatch.setenv('SOURCE_PHOTOS_ENABLED','false')
    runtime.run(db,public,path,at=AT,collection=collection)
    later=json.loads((public/'data.json').read_text(encoding='utf-8'))
    assert later['posts'][0]['visual_review']==review
    assert later['posts'][0]['assets']==entry['assets']
    with closing(Store(db)) as store:
        assert all(p['status']=='prepared' for p in store.posts())
        assert store.rows('select count(*) as n from source_photos')==[{'n':1}]
    validate_state(db);validate_public(public)


def test_explicit_source_photo_off_stays_off_even_if_generation_enabled(tmp_path,monkeypatch):
    from news_engine.source_photos import SourcePhotos
    monkeypatch.setenv('SOURCE_PHOTOS_ENABLED','false')
    monkeypatch.setenv('ILLUSTRATIONS_ENABLED','true')
    with closing(Store(tmp_path/'state.sqlite')) as store:
        assert SourcePhotos(store,AT,tmp_path/'photos',[]).enabled is False


def test_ticket_price_currency_and_access_condition_survive_adapter(tmp_path):
    _,collection=setup(tmp_path);row=collection['items'][0]
    row.update(price=536,currency='TRY',fee='Kaynak seans fiyatı: 536 TL',
               price_basis='listed_session_price_subject_to_ticket_conditions',
               audience={'kind':'ticketed','evidence':'Etkinlik 18 yaş ve üzeri katılımcılara açıktır; bilet gereklidir.'})
    item=runtime.adapt(row)
    assert item['price']=='536' and item['currency']=='TRY'
    assert '18 yaş' in item['participation'] and 'bilet' in item['participation']
    assert 'Listelenen seans bileti: 536 TL' in runtime.caption(item,item['title'])
    from news_engine.schedule import slide_body
    assert 'Listelenen bilet: 536 TL' in slide_body(item)


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
