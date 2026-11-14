"""14 Nov 2026: the owner asked for Davraz Haber (davrazhaber.com.tr) as a source.

It runs on the same news platform as Kanal32. Article photos are served from
the platform's shared CDN under Davraz Haber's own tenant folder (1054).
"""
import json
from pathlib import Path

import pytest

from isparta.readers import article, news_links
from isparta.runtime import PRESS, sources_for_engine
from news_engine.source_photo_data import approved_image_url, delivery_sources

CONFIG = json.loads((Path(__file__).parents[1] / 'config/research-sources.json').read_text(encoding='utf8'))
SOURCE = next(s for s in CONFIG['sources'] if s['id'] == 'davrazhaber')
PAGE = 'https://www.davrazhaber.com.tr/haber-davrazdaki-okula-898-metrekarelik-spor-salonu-7561.html'
PHOTO = ('https://cdn.haberyazilimiai.com/uploads/1054/images/haber/2026/11/14/'
         'davrazdaki-okula-898-metrekarelik-spor-salonu-200241-20261114.webp')

LISTING = '''<div class="col py-2"><a href="haber-davrazdaki-okula-898-metrekarelik-spor-salonu-7561.html" target="_blank">
<div class="card"><img class="lazy-load" data-src="{photo}"><h3>Davraz’daki Okula 898 Metrekarelik Spor Salonu</h3></div></a></div>
<a href="/isparta-haberleri"><img src="/logo.png"></a>
<a href="haber-zabundan-icme-suyu-aciklamasi-7485.html">Yazı bağlantısı, görselsiz</a>
<a href="https://www.davrazhaber.com.tr/haber-ispartada-mehmetcige-spor-merkezi-7487.html"><img src="/a.webp"></a>
<a href="https://baska.example/haber-ornek-1.html"><img src="/b.webp"></a>'''.format(photo=PHOTO)

ARTICLE = f'''<html><head>
<meta property="og:image" content="{PHOTO}">
<meta property="article:published_time" content="2026-11-14T20:00:08+03:00">
<meta property="article:section" content="Isparta">
</head><body><div class="haber-detay"><h1 class="px-5 py-3 mx-5">Davraz’daki Okula 898 Metrekarelik Spor Salonu</h1>
<div class="detay" property="articleBody"><p>Isparta Belediye Başkanı Şükrü Başdeğirmen, mahallelere ve okullara
yeni spor tesisleri kazandırmaya devam ediyor. Bu kapsamda İTO Şehit Mustafa Gözütok Ortaokulu'na kapalı
spor salonu inşa ediliyor.</p></div></div></body></html>'''


def test_the_isparta_listing_gives_its_article_pages_newest_first():
    assert news_links(LISTING, SOURCE, limit=8) == [
        'https://www.davrazhaber.com.tr/haber-davrazdaki-okula-898-metrekarelik-spor-salonu-7561.html',
        'https://www.davrazhaber.com.tr/haber-ispartada-mehmetcige-spor-merkezi-7487.html']


def test_an_article_keeps_its_own_headline_body_time_and_photo():
    row = article(ARTICLE, PAGE, SOURCE)
    assert row['title'] == 'Davraz’daki Okula 898 Metrekarelik Spor Salonu'
    assert row['description'].startswith('Isparta Belediye Başkanı Şükrü Başdeğirmen')
    assert row['published_at'] == '2026-11-14T20:00:08+03:00'
    assert row['image_candidate'] == PHOTO
    assert row['parser_holds'] == []


def test_each_article_must_prove_its_isparta_locality_like_other_press():
    assert 'davrazhaber' in PRESS
    engine = next(s for s in sources_for_engine(CONFIG) if s['id'] == 'davrazhaber')
    assert engine['reviewed_local_scope'] is False


def test_its_photo_cdn_is_reachable_only_under_its_own_tenant_folder():
    assert approved_image_url('davrazhaber', PAGE, PHOTO)
    assert approved_image_url('davrazhaber', PAGE,
                              'https://cdn.haberyazilimiai.com/uploads/1054/images/haber/ornek-120000-20261106.jpg')
    cdn = [s for s in delivery_sources({'davrazhaber': SOURCE}) if s['url'] == 'https://cdn.haberyazilimiai.com/']
    # The CDN publishes its own robots file, so no missing-robots exception applies.
    assert cdn == [{'enabled': True, 'url': 'https://cdn.haberyazilimiai.com/',
                    'allow_missing_robots': False, 'robots_absent_as_403': False}]


@pytest.mark.parametrize('source_id,page,image', [
    ('davrazhaber', PAGE, PHOTO.replace('/1054/', '/1055/')),           # another publisher on the platform
    ('davrazhaber', PAGE, PHOTO.replace('/images/haber/', '/images/site/')),  # site logo/ads folder
    ('davrazhaber', PAGE, PHOTO + '?w=300'),
    ('davrazhaber', PAGE, 'https://cdn.haberyazilimiai.com/uploads/1054/images/haber/../site/logo.jpg'),
    ('davrazhaber', 'https://www.kanal32.com.tr/haber-ornek-1.html', PHOTO),
    ('kanal32', PAGE, PHOTO),
])
def test_no_other_tenant_folder_or_publisher_is_granted(source_id, page, image):
    assert approved_image_url(source_id, page, image) is False
