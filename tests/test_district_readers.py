"""Regression cases from the reviewed district and campus HTML structures."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

import pytest

from isparta.district_readers import (campus_portal, club_directory, official_article,
                                      official_entries, turkish_day)
from isparta.readers import TZ
from isparta.research import assess, run
from isparta.scope_readers import listing_entries

CONFIG=json.loads((Path(__file__).parents[1]/'config/research-sources.json').read_text(encoding='utf8'))
SOURCES={s['id']:s for s in CONFIG['sources']}
AT=datetime(2026,10,22,9,tzinfo=TZ)


def portal(city='Gönen/ISPARTA'):
    return ('<div class="valilikFooter-adres">'+city+'</div>'+
            ''.join(f'<a class="news-card-withDate" href="/haber-uzun-baslik-{i}"><h6 class="card-title">21.10.2026</h6><p class="card-text">Gönen yol çalışması {i}</p></a>' for i in range(5))+
            '<a class="announce-text" href="/duyuru-baslik-123">İçme suyu duyurusu</a>'+
            '<a class="announce-text" href="https://gonen.gov.tr/baska-sehir">Başka şehir</a>')


def detail(title='Gönen yol çalışması 0',date='21.10.2026',city='Gönen/ISPARTA'):
    return ('<div class="valilikFooter-adres">'+city+'</div><h2 class="page-title">'+title+'</h2>'+
            '<div class="dateandtag"><div class="card-date">'+date+'</div></div>'+
            '<div class="icerik"><p>İlçemizde yol ve kaldırım yenileme çalışmaları sürüyor. Gönen sokaklarında belediye ekipleri çalışıyor.</p></div>')


def test_district_feed_reads_notices_alongside_long_news_feed():
    rows=official_entries(portal(),SOURCES['ispartagonen-kaymakamlik'],AT,4)
    assert len(rows)==4 and rows[1]['feed_kind']=='notice'
    assert rows[0]['title']=='Gönen yol çalışması 0'
    assert rows[0]['archive_date'].startswith('2026-10-21')
    assert all('gonen.gov.tr/baska' not in x['url'] for x in rows)


def test_balikesir_gonen_or_antalya_aksu_portal_cannot_be_substituted():
    with pytest.raises(ValueError,match='identity_changed'):
        official_entries(portal('Gönen/BALIKESİR'),SOURCES['ispartagonen-kaymakamlik'],AT,4)
    with pytest.raises(ValueError,match='identity_changed'):
        official_entries(portal('Aksu/ANTALYA'),SOURCES['aksu-kaymakamlik'],AT,4)


def test_senirkent_heading_wraps_link_not_other_way_round():
    raw='<footer>Senirkent/ISPARTA</footer><h3><a href="https://www.senirkent.bel.tr/haber/yollar-yenileniyor">Yollar yenileniyor</a></h3>'
    entries=official_entries(raw,SOURCES['senirkent-belediye'],AT,3)
    assert len(entries)==1 and entries[0]['title']=='Yollar yenileniyor'


def test_verified_contact_address_disambiguates_local_gonen_but_not_syndicated_report():
    source=SOURCES['ispartagonen-kaymakamlik']
    entry=official_entries(portal(),source,AT,4)[0]
    item=official_article(detail(),entry['url'],source,entry)
    assert item['published_time_known'] is False
    assert assess(item,AT,[])['eligible_for_drafting']
    item['description']='Balıkesir Gönen ilçesinde yol çalışmaları tamamlandı.'
    assert 'Isparta_locality_unconfirmed' in assess(item,AT,[])['holds']


def test_same_domain_detail_must_keep_source_contact_identity():
    source=SOURCES['ispartagonen-kaymakamlik'];entry=official_entries(portal(),source,AT,4)[0]
    with pytest.raises(ValueError,match='identity_changed'):
        official_article(detail(city='Gönen/BALIKESİR'),entry['url'],source,entry)


def test_old_government_article_stays_old_despite_current_header():
    source=SOURCES['ispartagonen-kaymakamlik'];entry=official_entries(portal(),source,AT,4)[0]
    item=official_article('<header>22.10.2026</header>'+detail(date='20.10.2025'),entry['url'],source,entry)
    holds=assess(item,AT,[])['holds']
    assert 'news_older_than_48h' in holds and 'archive_and_article_dates_conflict' in holds


def test_undated_attachment_notice_is_not_todays_service_alert():
    source=SOURCES['ispartagonen-kaymakamlik'];entry=official_entries(portal(),source,AT,4)[1]
    item=official_article(detail(title=entry['title'],date=''),entry['url'],source,entry)
    holds=assess(item,AT,[])['holds']
    assert item['published_at'] is None
    assert 'official_notice_validity_requires_review' in holds and 'original_publication_date_missing' in holds


@pytest.mark.parametrize('source_id,markup',[
    ('keciborlu-belediye','<time pubdate datetime="2026-10-21">21 Ekim 2026</time>'),
    ('senirkent-belediye','<div class="article-meta"><span>Haberler</span><span>21 Ekim 2026</span><span>99 görüntülenme</span></div>')])
def test_municipal_original_date_fields_exclude_footer_and_modified(source_id,markup):
    source=SOURCES[source_id]
    identity='<title>Keçiborlu Belediyesi</title>' if source_id=='keciborlu-belediye' else '<footer>Senirkent/ISPARTA</footer>'
    heading='<h1 class="page-title">Yerel çalışma</h1>' if source_id=='keciborlu-belediye' else '<h2 class="detail-title">Yerel çalışma</h2>'
    container='entry-content' if source_id=='keciborlu-belediye' else 'article-body'
    raw=identity+heading+markup+f'<div class="{container}"><p>İlçemizde kamu hizmetleri için düzenleme ve yol çalışması sürüyor.</p></div><footer>22 Ekim 2026</footer>'
    item=official_article(raw,source['url']+'haber-test',source,dict(title='Yerel çalışma',feed_kind='news'))
    assert item['published_at']=='2026-10-21T00:00:00+03:00' and not item['published_time_known']


def campus(date='23 Ekim 2026 Cuma',clock='10.00',venue='Isparta Belediyesi Kültür Merkezi',audience='Etkinlik halka açıktır.'):
    return ('<h1>Topluluk Buluşması</h1><div class="col-sm-4 bordered">Yayın Tarihi: 21.10.2026</div><div class="content">'+
            '<div>Topluluklarımız yeni dönemde birlikte kültür sanat programı düzenleyecek. '+audience+'</div>'+
            f'<div>Tarih: {date}</div><div>Saat: {clock}</div><div>Yer: {venue}</div></div>')


def test_portal_archive_upload_date_not_part_of_title_or_session_date():
    source=SOURCES['isubu-campus-portal']
    rows=listing_entries('<a itemprop="url" href="/etkinlik/1/topluluk-bulusmasi">Topluluk Buluşması<br><span></span> 21.10.2026</a>',source,AT,4)
    assert rows[0]['title']=='Topluluk Buluşması'
    item=campus_portal(campus(),rows[0]['url'],source,rows[0])
    assert item['start']=='2026-10-23T10:00:00+03:00'
    assert item['published_at']=='2026-10-21T00:00:00+03:00'
    assert assess(item,AT,[])['eligible_for_drafting']
    assert item['publication_ready'] is False


@pytest.mark.parametrize('changes,reason',[
    ({'date':'20 Ekim 2026 Salı'},'event_already_started'),
    ({'date':'23 Ekim'},'explicit_start_time_missing'),
    ({'clock':'10.00–12.00'},'explicit_start_time_missing'),
    ({'venue':'Antalya Kültür Merkezi'},'Isparta_venue_unconfirmed'),
    ({'audience':'Katılım koşulları daha sonra açıklanacak.'},'participation_conditions_unknown')])
def test_campus_details_not_invented_or_retimed(changes,reason):
    source=SOURCES['isubu-campus-portal']
    item=campus_portal(campus(**changes),source['url'],source,{'title':'Topluluk Buluşması'})
    assert reason in assess(item,AT,[])['holds']


def test_conflicting_explicit_campus_dates_are_held():
    source=SOURCES['isubu-campus-portal']
    raw=campus().replace('</div></div>','</div><div>Tarih: 24 Ekim 2026</div></div>')
    item=campus_portal(raw,source['url'],source,{'title':'Topluluk Buluşması'})
    assert 'conflicting_labelled_session_details' in item['parser_holds']


@pytest.mark.parametrize('claim,free', [('Ücretsiz servis hizmeti sağlanacak.',False),
    ('Katılım ücretsizdir.',True),('Katılım ücretsiz değildir.',False)])
def test_free_shuttle_is_not_free_event_admission(claim,free):
    source=SOURCES['isubu-campus-portal']
    item=campus_portal(campus(audience='Etkinlik halka açıktır. '+claim),source['url'],source,{'title':'Topluluk Buluşması'})
    assert (item['fee']=='Ücretsiz') is free


def test_club_directory_exports_organisations_only_without_student_names():
    source=CONFIG['discovery_sources'][0]
    raw='<div class="content"><table><tr><th>NO</th><th>TOPLULUK ADI</th></tr><tr><td>1</td><td>Tiyatro Topluluğu</td><td>Özel Danışman Adı</td><td>Öğrenci Adı</td></tr></table></div>'
    rows=club_directory(raw,source)
    assert len(rows)==1 and rows[0]['event_reader_verified'] is False
    assert 'Öğrenci Adı' not in json.dumps(rows,ensure_ascii=False)
    assert 'Özel Danışman Adı' not in json.dumps(rows,ensure_ascii=False)


def test_expanded_registry_keeps_discovery_separate_and_all_failures_visible(tmp_path):
    path=tmp_path/'sources.json';path.write_text(json.dumps(CONFIG),encoding='utf8')
    class Offline:
        def get(self,url):raise ValueError('offline')
    report=run(path,at=AT,fetcher=Offline())
    assert len(report['source_health'])==31 and len(report['discovery_health'])==1
    assert len(report['items'])==0 and len(report['discovered_clubs'])==0
    assert all(s['status']=='failed' for s in report['source_health'])
    assert report['discovery_health'][0]['status']=='failed'
    assert report['publishing_enabled'] is False


def test_unreviewed_source_budget_not_silently_accepted(tmp_path):
    cfg=deepcopy(CONFIG);cfg['sources']=[dict(SOURCES['aksu-kaymakamlik'],id=f'item-{i}') for i in range(41)]
    path=tmp_path/'too-many.json';path.write_text(json.dumps(cfg),encoding='utf8')
    with pytest.raises(ValueError,match='registry'):run(path,at=AT)
