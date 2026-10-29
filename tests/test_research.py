"""Regressions from actual reviewed source structures; no network in CI."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import socket

import pytest

from isparta.fetch import FetchError, Fetcher, decode, safe_url
from isparta.readers import TZ, article, date_conflict, isubu, news_links, sdu
from isparta.research import assess, deduplicate, local_news, local_venue, run

CONFIG = json.loads((Path(__file__).parents[1]/'config/research-sources.json').read_text(encoding='utf8'))
AT = datetime(2026, 10, 21, 18, tzinfo=TZ)
SOURCES = {s['id']:s for s in CONFIG['sources']}


def story(**values):
    item = {'id':'test', 'kind':'news', 'source_id':'bomba32', 'title':'Isparta kaldırım çalışması',
            'description':'Isparta Cumhuriyet Caddesi üzerinde kaldırım yenileme çalışmaları yapılıyor.',
            'published_at':'2026-10-21T15:56:00+03:00', 'parser_holds':[]}
    item.update(values)
    return item


def event(**values):
    item = story(kind='event', source_id='isubu-events', title='Öğrenci tanışma toplantısı',
                 start='2026-10-22T16:00:00+03:00', end='2026-10-22T18:00:00+03:00',
                 time_known=True, location='Kampüs Konukevi Yemek Salonu (Doğu Yerleşkesi)',
                 audience={'kind':'restricted','evidence':'Tüm öğrencilere açıktır.'}, date_conflict=False)
    item.update(values)
    return item


def check(item):
    return assess(item, AT, CONFIG['venues'])


def test_article_original_date_beats_modified_and_current_header():
    raw = '''<meta name="datePublished" content="2026-03-03T13:36:41+03:00">
    <meta name="dateModified" content="2026-10-21T17:00:00+03:00">
    <h1>Isparta'da okul ziyareti</h1><div class="detay"><p>Isparta öğrencileri
    yerel yönetimleri tanımak için belediyeye ziyarette bulundu.</p></div>
    <div class="header-date">21 Ekim 2026</div>'''
    item = article(raw, 'https://www.kanal32.com.tr/haber-ornek-6914.html',
                   dict(SOURCES['kanal32'],date_selector='meta[name=datePublished]'))
    assert 'news_older_than_48h' in check(item)['holds']
    assert item['published_at'].startswith('2026-03-03')


@pytest.mark.parametrize('date,expected', [
    (AT-timedelta(hours=48),True), (AT-timedelta(hours=48,seconds=1),False),
    (AT+timedelta(seconds=1),False)])
def test_news_age_boundary(date,expected):
    assert check(story(published_at=date.isoformat()))['eligible_for_drafting'] is expected


def test_missing_original_date_never_filled_from_discovery():
    assert 'original_publication_date_missing' in check(story(published_at=None))['holds']


def test_event_announcement_cannot_bypass_session_validity_as_fresh_news():
    assert 'event_or_notice_validity_requires_review' in check(story(title='Isparta kermes duyurusu'))['holds']


@pytest.mark.parametrize('title', ['Isparta fırtına uyarısı', 'Isparta elektrik kesintisi', 'Isparta son başvuru'])
def test_service_notice_needs_separate_expiry(title):
    assert not check(story(title=title))['eligible_for_drafting']


@pytest.mark.parametrize('value,expected', [('Balıkesir Gönen belediyesi',False),
    ('Antalya Aksu ilçesi',False),('Isparta Gönen ilçesi',True),('Yalvaç meydanı',True),
    ('Keçiborlu yol çalışması',True),('Ispartalı sporcu',True)])
def test_district_scope_not_ambiguous_names(value, expected):
    assert local_news(value) is expected


def test_university_organizer_does_not_make_antalya_venue_local():
    assert not local_venue('Antalya Orkun Ozan Sanat Galerisi','sdu-calendar',CONFIG['venues'])
    assert not check(event(location='Antalya Kemer'))['eligible_for_drafting']


@pytest.mark.parametrize('changes,reason', [
    ({'start':None},'explicit_start_time_missing'),
    ({'time_known':False},'explicit_start_time_missing'),
    ({'start':'2026-10-21T10:00:00+03:00'},'event_already_started'),
    ({'end':'2026-10-21T10:00:00+03:00'},'event_end_before_start'),
    ({'date_conflict':True},'calendar_and_description_dates_conflict'),
    ({'audience':{'kind':'unknown'}},'participation_conditions_unknown'),
    ({'description':'Etkinlik iptal edilmiştir; yeni tarih ayrıca duyurulacak.'},'cancelled_or_postponed_requires_review')])
def test_event_holds(changes,reason):
    item=check(event(**changes))
    assert reason in item['holds'] and item['publication_ready'] is False


def test_matching_future_student_event_keeps_restriction():
    item=check(event())
    assert item['eligible_for_drafting']
    assert item['audience']['kind']=='restricted'
    assert item['publication_ready'] is False


@pytest.mark.parametrize('description,start,end,expected', [
    ('30 Eylül günü','30.10.2026',None,True),
    ('13 Ekim 2026 Salı','15.10.2026','22.10.2026',True),
    ('1 Ekim 09.00-12.00','01.10.2026','01.11.2026',True),
    ('9 – 13 Kasım 2026','09.11.2026','13.11.2026',False),
    ('9 – 13 Kasım 2025','09.11.2026','13.11.2026',True)])
def test_conflicting_prose_dates(description,start,end,expected):
    from isparta.readers import dotted
    assert date_conflict(description,dotted(start),dotted(end) if end else None) is expected


def isubu_card(title='Toplantı',date='22.10.2026 16:00 - 22.10.2026 18:00',desc='Tüm öğrencilerimize açıktır.'):
    return f'''<div class="card card-custom gutter-b"><div class="card-body">
    <div class="symbol"><img src="/poster-placeholder.png"></div><div class="flex-grow-0">{title}</div>
    <div class="d-flex flex-wrap my-2"><a>{date}</a><a>Keçiborlu MYO</a><a>Öğrenci Topluluğu</a></div>
    <span class="font-size-h7">{desc}</span></div></div>'''


def upcoming(cards):
    return '<div class="card card-stretch"><span class="card-label">Yaklaşan etkinlikler</span>'+cards+'</div>'


def test_isubu_distinct_items_and_reused_poster_not_accepted():
    rows=isubu(upcoming(isubu_card()+isubu_card('İkinci etkinlik')),SOURCES['isubu-events'])
    assert len({r['id'] for r in rows})==2
    assert all(r['image_candidate'] is None for r in rows)
    assert all(r['image_status']=='reused_placeholder_rejected' for r in rows)
    assert all(r['audience']['kind']=='restricted' for r in rows)
    assert all(r['fee']=='Ücret açıklanmamış' for r in rows)


def test_isubu_past_and_popular_sections_not_read_as_upcoming():
    rows=isubu(isubu_card('Geçmişte düzenlendi')+upcoming(isubu_card('Gelecek buluşma')),SOURCES['isubu-events'])
    assert [r['title'] for r in rows]==['Gelecek buluşma']


def test_isubu_changed_structure_fails_visible():
    with pytest.raises(ValueError):isubu('<div>Yeni takvim biçimi</div>',SOURCES['isubu-events'])


def test_sdu_upload_day_does_not_supply_event_hour():
    raw='''<div class="modal-body"><table><tr><th>Etkinlik Adı</th><td>Tiyatro</td></tr>
    <tr><th>Etkinlik Tarihi</th><td>26.10.2026</td></tr><tr><th>Açıklama</th>
    <td>Halka açık tiyatro etkinliği.\nYer: İİBF A Salonu</td></tr></table></div>'''
    item=sdu(raw,SOURCES['sdu-calendar'])[0]
    assert item['time_known'] is False
    assert 'explicit_start_time_missing' in check(item)['holds']
    assert item['location']=='İİBF A Salonu'


def test_sdu_explicit_same_day_session_is_not_confused_with_midnight():
    raw='''<div class="modal-body"><table><tr><th>Etkinlik Adı</th><td>Tiyatro</td></tr>
    <tr><th>Etkinlik Tarihi</th><td>26.10.2026</td></tr><tr><th>Açıklama</th>
    <td>Halka açık tiyatro etkinliği.\nSaat: 19.30–21.00\nYer: İİBF A Salonu</td></tr></table></div>'''
    item=sdu(raw,SOURCES['sdu-calendar'])[0]
    assert item['start']=='2026-10-26T19:30:00+03:00'
    assert item['end']=='2026-10-26T21:00:00+03:00'
    assert check(item)['eligible_for_drafting']


def test_duplicate_news_and_separate_event_sessions():
    a,b=check(story()),check(story(id='other',source_id='haber32'))
    deduplicate([a,b]);assert b['duplicate_of']==a['id'] and not b['eligible_for_drafting']
    a,b=check(event()),check(event(id='next',start='2026-10-23T16:00:00+03:00',end='2026-10-23T18:00:00+03:00'))
    deduplicate([a,b]);assert 'duplicate_of' not in b


def bomba32_page(slug, title, *, section=None, crumbs=()):
    # Structure of the reviewed Bomba32 page that published a paid company
    # promotion under "Reklam Manşet20" on 29 Oct 2026.
    url=f'https://www.bomba32.com/{slug}'
    ld=('<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','headline':title,
        'articleSection':section})+'</script>') if section else ''
    trail=''.join(f'<li class="breadcrumb-item"><a href="{href}">{label}</a></li>' for href,label in crumbs)
    raw=f'''<meta name="datePublished" content="2026-10-21T15:00:00+03:00">{ld}
    <nav aria-label="breadcrumb"><ol class="breadcrumb"><li><a href="https://www.bomba32.com">HABERLER</a></li>{trail}</ol></nav>
    <h1 itemprop="headline">{title}</h1><div class="article-text"><p>Isparta merkezde
    yeni yaşam alanları ve çalışmalar hakkında ayrıntılı açıklama yapıldı.</p></div>'''
    return article(raw,url,SOURCES['bomba32'])


@pytest.mark.parametrize('section,crumbs,held',[
    ('Reklam Manşet20',[('/reklam-manset20','REKLAM MANŞET20')],True),
    (None,[('/basin-bultenleri','Basın Bülteni')],True),
    ('Ekonomi',[('/ekonomi','EKONOMİ')],False),
    # A real story about advertising: only the self-link carries that word.
    ('Gündem',[('/gundem','GÜNDEM'),('/isparta-reklam-panolari-kaldirildi','Isparta reklam panoları kaldırıldı')],False)])
def test_publisher_paid_section_is_held_not_drafted(section,crumbs,held):
    item=check(bomba32_page('isparta-reklam-panolari-kaldirildi','Isparta reklam panoları kaldırıldı',
                            section=section,crumbs=crumbs))
    assert ('advertorial_section' in item['holds']) is held
    assert item['eligible_for_drafting'] is not held


def test_listing_cannot_supply_external_article_or_tracking_duplicates():
    source=dict(SOURCES['bomba32'],link_selector='a[href]')
    raw='''<a href="https://evil.example/news-a-long-story-slug">x</a>
    <a href="/isparta-test-haber-uzun-baslik?utm_source=a">a</a>
    <a href="/isparta-test-haber-uzun-baslik?utm_source=b">b</a>'''
    assert news_links(raw,source)==['https://www.bomba32.com/isparta-test-haber-uzun-baslik']


def test_partial_source_failure_is_not_healthy(tmp_path):
    cfg=deepcopy(CONFIG);cfg['sources']=[SOURCES['bomba32']]
    path=tmp_path/'config.json';path.write_text(json.dumps(cfg),encoding='utf8')
    class Fake:
        def get(self,url):
            if url==SOURCES['bomba32']['url']:
                return '<div class="last-minutes-box"><a href="/isparta-test-haber-uzun-baslik">a</a></div>',url
            raise FetchError('robots_disallowed')
    report=run(path,at=AT,fetcher=Fake())
    assert report['source_health'][0]['status']=='partial'
    assert report['source_health'][0]['parsed_items']==0
    assert report['publishing_enabled'] is False


@pytest.mark.parametrize('max_details,expected',[(None,12),(50,12),(4,4)])
def test_busy_news_listing_reads_a_bounded_wider_window(tmp_path,max_details,expected):
    source=dict(SOURCES['bomba32'])
    if max_details is not None:source['max_details']=max_details
    cfg=deepcopy(CONFIG);cfg['sources']=[source]
    path=tmp_path/'config.json';path.write_text(json.dumps(cfg),encoding='utf8')
    links=''.join(f'<a href="/isparta-test-haber-uzun-baslik-{n:02d}">x</a>' for n in range(15))
    requested=[]
    class Fake:
        def get(self,url):
            if url==source['url']:
                return f'<div class="last-minutes-box">{links}</div>',url
            if url.startswith('https://www.bomba32.com/'):requested.append(url)
            raise FetchError('robots_disallowed')
    run(path,at=AT,fetcher=Fake())
    assert len(requested)==expected
    assert requested==[f'https://www.bomba32.com/isparta-test-haber-uzun-baslik-{n:02d}' for n in range(expected)]


@pytest.mark.parametrize('url', ['http://example.com/','https://evil.example/',
    'https://user:pass@example.com/','https://example.com:8443/'])
def test_network_allowlist(url):
    with pytest.raises(FetchError):safe_url(url,{'example.com'})


def test_private_dns_rejected(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(0,0,0,'',('127.0.0.1',443))])
    with pytest.raises(FetchError,match='non_public'):safe_url('https://example.com/',{'example.com'})


def test_redirect_rechecks_robots_before_fetch(monkeypatch):
    from urllib.robotparser import RobotFileParser
    f=Fetcher([{'url':'https://example.com/','research_enabled':True}])
    robot=RobotFileParser();robot.parse(['User-agent: *','Disallow: /private'])
    f.robots['example.com']=robot
    monkeypatch.setattr('isparta.fetch.safe_url',lambda url,hosts:url)
    calls=[]
    def request(url,delay=1):
        calls.append(url);return None,'https://example.com/private'
    monkeypatch.setattr(f,'_request',request)
    with pytest.raises(FetchError,match='robots_disallowed'):f.get('https://example.com/public')
    assert calls==['https://example.com/public']


def test_turkish_charset_and_invalid_charset():
    value='Isparta öğrenci etkinliği'
    assert decode(value.encode('utf8'),'text/html')==value
    with pytest.raises(FetchError):decode(b'x','text/html;charset=not-an-encoding')


def test_research_exports_evidence_excerpt_not_full_article(tmp_path):
    cfg=deepcopy(CONFIG);cfg['sources']=[SOURCES['bomba32']]
    path=tmp_path/'config.json';path.write_text(json.dumps(cfg),encoding='utf8')
    body='Isparta merkezinde kaldırım düzenlemesi sürüyor. ' * 30
    class Fake:
        def get(self,url):
            if url==SOURCES['bomba32']['url']:
                return '<div class="last-minutes-box"><a href="/isparta-test-haber-uzun-baslik">a</a></div>',url
            return ('<meta name="datePublished" content="2026-10-21T15:00:00+03:00">'
                    '<h1 itemprop="headline">Isparta kaldırımları yenileniyor</h1>'
                    '<div class="article-text"><p>'+body+'</p></div>'),url
    report=run(path,at=AT,fetcher=Fake())
    item=report['items'][0]
    assert 'description' not in item
    assert len(item['source_excerpt'])==600 and item['excerpt_is_complete'] is False
    assert item['publication_ready'] is False


def test_unknown_fee_never_becomes_free():
    rows=isubu(upcoming(isubu_card(desc='Tüm öğrenciler davetlidir. Katılım ücretsiz değildir.')),SOURCES['isubu-events'])
    assert rows[0]['fee']=='Ücret açıklanmamış'


def test_same_stable_identity_with_conflicting_payload_is_held(tmp_path):
    cfg=deepcopy(CONFIG);cfg['sources']=[SOURCES['isubu-events']]
    path=tmp_path/'config.json';path.write_text(json.dumps(cfg),encoding='utf8')
    class Fake:
        def get(self,url):
            return upcoming(isubu_card()+isubu_card(desc='Tüm öğrencilere farklı katılım koşulu uygulanır.')),url
    report=run(path,at=AT,fetcher=Fake())
    assert len(report['items'])==1
    assert 'conflicting_source_identity' in report['items'][0]['holds']
