"""Archive linkage, real ticket sessions and poster-only notice regressions."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

import pytest

from isparta.readers import TZ
from isparta.research import assess, run
from isparta.scope_readers import (archive_article, campus_notice, correlate_campus, culture_items,
    culture_year_link, listing_entries, public_transport, ticket_sessions)

CONFIG=json.loads((Path(__file__).parents[1]/'config/research-sources.json').read_text(encoding='utf8'))
SOURCES={s['id']:s for s in CONFIG['sources']}
AT=datetime(2026,10,21,21,tzinfo=TZ)


def test_all_thirteen_sources_unique_with_local_news_and_events():
    assert len(SOURCES)==13
    assert all(s['research_enabled'] for s in SOURCES.values())
    assert {'bomba32','haber32','kanal32','ajans32','isparta-belediye','sdu-calendar','bubilet-isparta'} <= SOURCES.keys()


def test_belediye_date_is_bound_to_same_archive_anchor():
    source=SOURCES['isparta-belediye']
    raw='''<a class="news-card-horizontal" href="/isparta-kaldirim-yenileniyor">
    <span class="cardDate">14.10.2026</span><h5 class="card-title">Isparta kaldırımları yenileniyor</h5></a>
    <div class="header-date">21.10.2026</div>'''
    entry=listing_entries(raw,source,AT,4)[0]
    detail='''<h2 class="page-title">Isparta kaldırımları yenileniyor</h2>
    <div class="icerik"><p>Isparta merkezinde kaldırımlar yenileniyor; belediye ekipleri çalışmayı sürdürüyor.</p></div>'''
    item=archive_article(detail,entry['url'],source,entry)
    assert item['published_at'].startswith('2026-10-14')
    assert item['publication_date_origin']=='same_anchor_archive'
    assert 'news_older_than_48h' in assess(item,AT,CONFIG['venues'])['holds']


@pytest.mark.parametrize('change,reason',[
    ({'title':'Farklı haber'},'archive_title_does_not_match_article'),
    ({'archive_date_conflict':True},'archive_and_article_dates_conflict')])
def test_mismatched_archive_never_approves_article(change,reason):
    entry={'title':'Isparta haber','archive_date':'2026-10-21T00:00:00+03:00','archive_date_conflict':False}
    entry.update(change)
    item=archive_article('<h2 class="page-title">Isparta haber</h2><div class="icerik"><p>Isparta merkezinde yeni kaldırım düzenlemesi yapılıyor.</p></div>',
                         'https://www.isparta.bel.tr/isparta-haber',SOURCES['isparta-belediye'],entry)
    assert reason in item['parser_holds']


def test_missing_archive_date_not_taken_from_picture_filename():
    entry={'title':'Isparta haber','archive_date':None}
    item=archive_article('<h2 class="page-title">Isparta haber</h2><div class="icerik"><img src="/21-10-2026.jpg"><p>Isparta merkezinde yeni kaldırım düzenlemesi yapılıyor.</p></div>',
                         'https://www.isparta.bel.tr/isparta-haber',SOURCES['isparta-belediye'],entry)
    assert item['published_at'] is None


@pytest.mark.parametrize('source_id,heading,content,dateblock',[
    ('sdu-sks','<h2 class="page-title">Konser</h2>','<div class="main__body"><p><img src="https://taslak.sdu.edu.tr/poster.jpg"></p></div>',
     '<div class="main__icerik-bilgi"><div class="col-sm-4">Yayın Tarihi: 20/10/2026</div></div>'),
    ('isubu-sks','<h1>Konser</h1>','<div class="content"><p>Geçmiş etkinlik üniversite öğrencilerinin katılımıyla gerçekleştirildi.</p></div>',
     '<div class="announcement-header"><div class="item"><span>Yayın Tarihi: 08.05.2026 10:16</span></div></div>')])
def test_notice_upload_date_never_becomes_session(source_id,heading,content,dateblock):
    item=campus_notice(heading+content+dateblock,'https://example.org/notice',SOURCES[source_id],{'title':'Konser'})
    assert item['published_at'] and item['start'] is None and item['time_known'] is False
    assert not assess(item,AT,CONFIG['venues'])['eligible_for_drafting']


def test_culture_archive_year_link_not_national_homepage_ticker():
    raw='''<a href="https://pgm.ktb.gov.tr/TR-123/ilan.html">Bakanlık ilanı</a>
    <div class="inner_mid_left"><div class="art_loop"><div class="search_item">
    <a href="/TR-446962/2026-yili.html">2026 Yılı</a><p>23.01.2026</p></div></div></div>'''
    assert culture_year_link(raw,SOURCES['isparta-kultur'],AT).endswith('/TR-446962/2026-yili.html')
    assert culture_year_link(raw,SOURCES['isparta-kultur'],AT.replace(year=2027)) is None


def test_past_culture_program_has_distinct_actual_sessions():
    raw='''<div class="inner_mid_left"><div class="in_sec_1"><h2 id="pageTitle">Müzeler Haftası</h2>
    <article class="art_loop"><p>18.05.2026</p><p>Öğrencilerle müze içi eğitim etkinlikleri yapılacak.</p>
    <p>Yer: Yalvaç Müzesi</p><p>Saat: 11.00</p><p>Yeni serginin açılışı için program düzenlenecek.</p>
    <p>Yer: Yalvaç Müzesi</p><p>Saat: 16.00</p></article></div></div>'''
    rows=culture_items(raw,'https://isparta.ktb.gov.tr/TR-455548/muzeler-haftasi.html',SOURCES['isparta-kultur'],{'title':'Müzeler Haftası'})
    assert len({r['id'] for r in rows})==2
    assert rows[0]['start']=='2026-05-18T11:00:00+03:00'
    assert all('event_already_started' in assess(r,AT,CONFIG['venues'])['holds'] for r in rows)


def ticket_html(*,rules='<ul><li>13 yaş altı alınmamaktadır. Öğrenci bileti alanlar kimlik göstermelidir.</li></ul>',status='EventScheduled',availability='InStock',two_sessions=False):
    schema={'@type':'Event','name':'Isparta Sahne Gösterisi','description':'Isparta sahnesinde seyirciler için yeni bir tiyatro gösterisi.',
            'startDate':'2026-11-07T17:30:00+00:00','endDate':'2026-11-07T19:00:00+00:00',
            'eventStatus':'https://schema.org/'+status,
            'location':{'name':'Isparta Kültür Merkezi','address':{'addressLocality':'Isparta'}},
            'offers':{'price':900,'priceCurrency':'TRY','availability':'https://schema.org/'+availability,
                      'url':'https://www.bubilet.com.tr/isparta/etkinlik/ornek/seans/123'},
            'image':['https://cdn.bubilet.com.tr/event.png']}
    if two_sessions:
        second=deepcopy(schema);second['startDate']='2026-11-08T17:30:00+00:00';second['endDate']='2026-11-08T19:00:00+00:00'
        second['offers']['url']='https://www.bubilet.com.tr/isparta/etkinlik/ornek/seans/124'
        parent=deepcopy(schema);parent['subEvent']=[schema,second];schema=parent
    event={'event':{'eventName':'Isparta Sahne Gösterisi','slug':'ornek','thingsToKnow':'$1',
                    'summary':'<p>Isparta sahnesinde seyirciler için yeni bir tiyatro gösterisi.</p>'}}
    transport='1:T'+format(len(rules.encode('utf8')),'x')+','+rules+'2:'+json.dumps(event,ensure_ascii=False)+'\n'
    return ('<h1>Isparta Sahne Gösterisi</h1><div id="organizator-section"><a href="/organizator/gercek"><h4>Gerçek Organizasyon</h4></a></div>'
            '<script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False)+'</script>'
            '<script>self.__next_f.push('+json.dumps([1,transport],ensure_ascii=False)+')</script>')


def tickets(raw):
    return ticket_sessions(raw,'https://www.bubilet.com.tr/isparta/etkinlik/ornek',SOURCES['bubilet-isparta'])


def test_ticket_utc_session_organizer_age_and_price_kept_separate():
    item=tickets(ticket_html())[0]
    assert item['start']=='2026-11-07T20:30:00+03:00'
    assert item['organizer']=='Gerçek Organizasyon' and item['ticket_platform']=='Bubilet'
    assert item['audience']['minimum_age']==13 and item['audience']['kind']=='ticketed'
    assert item['price']==900 and item['fee']!='Ücretsiz'
    assert assess(item,AT,CONFIG['venues'])['eligible_for_drafting']
    assert item['publication_ready'] is False


def test_ticket_two_sessions_do_not_collapse_to_one_event():
    rows=tickets(ticket_html(two_sessions=True))
    assert len({i['id'] for i in rows})==2
    assert rows[0]['start']!=rows[1]['start']


@pytest.mark.parametrize('changes,reason',[
    ({'status':'EventCancelled'},'ticket_session_not_scheduled'),
    ({'availability':'SoldOut'},'ticket_availability_unconfirmed_or_sold_out'),
    ({'rules':''},'ticket_participation_conditions_unconfirmed')])
def test_ticket_conditions_and_cancelled_sessions_held(changes,reason):
    item=tickets(ticket_html(**changes))[0]
    assert reason in assess(item,AT,CONFIG['venues'])['holds']


def test_platform_schema_not_used_as_actual_organizer():
    raw=ticket_html().replace('<div id="organizator-section"><a href="/organizator/gercek"><h4>Gerçek Organizasyon</h4></a></div>','')
    item=tickets(raw)[0]
    assert item['organizer'] is None
    assert 'actual_organizer_unconfirmed' in item['parser_holds']


def test_unrelated_legal_age_text_not_taken_as_event_rules():
    raw=ticket_html().replace('thingsToKnow','unrelatedLegalText')
    assert 'ticket_participation_conditions_unconfirmed' in tickets(raw)[0]['parser_holds']


def test_public_transport_decodes_unicode_byte_lengths_without_running_js():
    raw=ticket_html()
    texts,records=public_transport(__import__('bs4').BeautifulSoup(raw,'html.parser'))
    assert 'Öğrenci' in texts['1'] and records
    _,empty=public_transport(__import__('bs4').BeautifulSoup('<script>fetch("https://evil.example/")</script>','html.parser'))
    assert empty==[]


def test_rotating_ticket_discovery_reaches_cards_beyond_first_four():
    raw=''.join(f'<a href="/isparta/etkinlik/show-{i}"><h3>Etkinlik {i}</h3></a>' for i in range(20))
    first=listing_entries(raw,SOURCES['bubilet-isparta'],AT,8)
    second=listing_entries(raw,SOURCES['bubilet-isparta'],AT.replace(hour=23),8)
    assert first[:4]==second[:4] and first[4:]!=second[4:]


def test_all_thirteen_allowed_and_unreachable_source_reported_failed(tmp_path):
    config=tmp_path/'config.json';config.write_text(json.dumps(CONFIG),encoding='utf8')
    class Offline:
        def get(self,url):raise ValueError('offline fixture')
    report=run(config,at=AT,fetcher=Offline())
    assert len(report['source_health'])==13
    assert all(s['status']=='failed' for s in report['source_health'])


@pytest.mark.parametrize('publication,linked', [('2026-10-20T00:00:00+03:00',True),
    ('2025-10-20T00:00:00+03:00',False),('2026-10-28T00:00:00+03:00',False),(None,False)])
def test_recurring_campus_title_requires_recent_prior_announcement(publication,linked):
    notice={'id':'notice','source_id':'sdu-sks','title':'Temel Eğitim Programı',
            'published_at':publication,'url':'https://sksdb.sdu.edu.tr/tr/haber/notice.html',
            'parser_holds':['campus_session_details_require_corroboration']}
    calendar={'id':'calendar','source_id':'sdu-calendar','title':'Temel Eğitim Programı',
              'start':'2026-10-26T13:00:00+03:00'}
    correlate_campus([notice,calendar])
    assert ('corroborating_sources' in calendar) is linked


def test_reviewed_timeout_retry_only_once_per_host_run(monkeypatch):
    import requests
    from isparta.fetch import Fetcher
    f=Fetcher([dict(SOURCES['sdu-sks'],timeout_retries=1,read_timeout_seconds=35)])
    calls=[]
    def read(url):
        calls.append(url)
        if len(calls) in (1,3):raise requests.Timeout()
        return 'ok',url
    monkeypatch.setattr(f,'_get_once',read)
    monkeypatch.setattr('isparta.fetch.time.sleep',lambda delay:None)
    url=SOURCES['sdu-sks']['url']
    assert f.get(url)==('ok',url)
    with pytest.raises(requests.Timeout):f.get(url)
    assert len(calls)==3


@pytest.mark.parametrize('error', ['http','tls','robots'])
def test_timeout_allowance_never_retries_access_denials(monkeypatch,error):
    import requests
    from isparta.fetch import Fetcher,FetchError
    f=Fetcher([dict(SOURCES['sdu-sks'],timeout_retries=1)])
    calls=[]
    exc={'http':requests.HTTPError(),'tls':requests.exceptions.SSLError(),'robots':FetchError('robots_disallowed')}[error]
    def read(url):calls.append(url);raise exc
    monkeypatch.setattr(f,'_get_once',read)
    with pytest.raises(type(exc)):f.get(SOURCES['sdu-sks']['url'])
    assert len(calls)==1 and f.timeout_retries['sksdb.sdu.edu.tr']==1


def test_timeout_limits_are_bounded():
    from isparta.fetch import Fetcher
    f=Fetcher([dict(SOURCES['sdu-sks'],timeout_retries=500,connect_timeout_seconds=500,read_timeout_seconds=500)])
    assert f.timeouts['sksdb.sdu.edu.tr']==(15,45)
    assert f.timeout_retries['sksdb.sdu.edu.tr']==1
