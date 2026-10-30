"""Real-source layout regressions; synthetic text/images never imply delivery."""
import pytest

from isparta.runtime import sources_for_engine
from news_engine.source_photo_data import approved_image_url
from news_engine.source_photos import candidate, news_subject
from news_engine.visual_match import LABELS, MatchRejected, validate_match, validate_news_photo


def article_case(source_id='ajans32'):
    host = 'www.ajans32.com' if source_id == 'ajans32' else 'www.bomba32.com'
    url = f'https://{host}/isparta-kaynak-haberi'
    title = 'Isparta caddesinde yol yenileme çalışması başladı'
    source = {'id': source_id, 'name': source_id, 'url': f'https://{host}/',
              'reader': 'article', 'research_enabled': True,
              'title_selector': 'h1', 'body_selector': '.article-text',
              'date_selector': 'meta[name="datePublished"]'}
    source = sources_for_engine({'sources': [source]})[0]
    item = {'source_id': source_id, 'kind': 'news', 'url': url, 'title': title,
            'published_at': '2026-10-24T10:00:00+03:00'}
    image = ('https://cdn.ajans32.com/news/72523.jpg' if source_id == 'ajans32' else
             'https://bomba32com.teimg.com/crop/1280x720/bomba32-com/uploads/2026/10/road.jpg')
    metadata = f'<meta name="datePublished" content="{item["published_at"]}"><meta property="og:image" content="{image}">'
    body = f'<h1>{title}</h1><div class="article-text"><p>Isparta Belediyesi cadde yenileme çalışmasını bu sabah başlattı.</p></div>'
    hero = (f'<div class="article-image"><img srcset="https://cdn.ajans32.com/news_t/72523.jpg 702w, {image} 1280w" alt="{title}"></div>'
            if source_id == 'ajans32' else f'<a href="{image}"><img src="{image}" alt="{title}"></a>')
    wrapper = ('article-detail news-detail' if source_id == 'ajans32' else 'news-section')
    html = metadata + f'<div class="{wrapper}"><div class="inner">{body}{hero}</div></div>'
    return source, item, image, html


@pytest.mark.parametrize('source_id', ['ajans32', 'bomba32'])
def test_publisher_hero_outside_body_and_exact_cdn_origin(source_id):
    source, item, image, html = article_case(source_id)
    assert candidate(html, item['url'], item, source) == image
    assert news_subject(item) == 'roadworks'


@pytest.mark.parametrize('change', ['title', 'date', 'final_url', 'canonical', 'archive'])
def test_new_layout_does_not_skip_exact_article_identity(change):
    source, item, image, html = article_case()
    final = item['url']
    if change == 'title': html = html.replace(item['title'], 'Isparta başka bir haber')
    if change == 'date': html = html.replace(item['published_at'], '2026-10-23T10:00:00+03:00')
    if change == 'final_url': final += '-baska-haber'
    if change == 'canonical': html += '<link rel="canonical" href="/baska-haber">'
    if change == 'archive': html = html.replace(f'alt="{item["title"]}"', 'alt="Arşiv fotoğrafı"')
    with pytest.raises(ValueError): candidate(html, final, item, source)


@pytest.mark.parametrize('source_id,page,image', [
    ('bomba32', 'https://www.bomba32.com/haber', 'https://bomba32com.teimg.com/foreign/uploads/a.jpg'),
    ('bomba32', 'https://www.bomba32.com/haber', 'https://bomba32com.teimg.com/bomba32-com/uploads/../../foreign.jpg'),
    ('bomba32', 'https://evil.example/haber', 'https://bomba32com.teimg.com/bomba32-com/uploads/a.jpg'),
    ('ajans32', 'https://www.ajans32.com/haber', 'https://cdn.ajans32.com/ads/72523.jpg'),
    ('ajans32', 'https://www.ajans32.com/haber', 'https://cdn.ajans32.com/news/72523.jpg?redirect=1'),
    ('ajans32', 'https://www.ajans32.com/haber', 'https://cdn.evil.example/news/72523.jpg'),
    ('another-source', 'https://www.ajans32.com/haber', 'https://cdn.ajans32.com/news/72523.jpg'),
])
def test_cdn_does_not_expand_to_other_publishers_namespaces_or_query_urls(source_id,page,image):
    assert approved_image_url(source_id, page, image) is False


def test_bomba32_body_photo_precedes_its_headline_collage():
    # 30 Oct: the Ethem amca hero was a headline collage; the body had the real photos.
    source, item, image, html = article_case('bomba32')
    inline = 'https://bomba32com.teimg.com/bomba32-com/uploads/2026/10/whatsapp-image-2026-10-28.jpeg'
    related = 'https://bomba32com.teimg.com/crop/250x150/bomba32-com/uploads/2026/10/baska-haber.jpg'
    html = html.replace('bu sabah başlattı.</p>', 'bu sabah başlattı.</p>'
                        f'<div class="related"><a href="/baska-haber"><img src="{related}"></a></div>'
                        f'<p><img src="{inline}"></p>')
    assert candidate(html, item['url'], item, source) == inline
    assert candidate(article_case('bomba32')[3], item['url'], item, source) == image


def portal_case(dated=True):
    config = {'id': 'keciborlu-belediye', 'name': 'Keçiborlu Belediyesi', 'url': 'https://www.keciborlu.bel.tr/',
              'research_enabled': True, 'reader': 'official_portal', 'district': 'Keçiborlu',
              'jurisdiction': 'Isparta', 'identity_selector': 'title', 'identity_pattern': 'Keçiborlu Belediyesi',
              'detail_path': '/(?:genel|duyurular|haberler)/[a-z0-9-]+/', 'title_selector': 'h1.page-title',
              'body_selector': '.entry-content', 'body_text_fallback': True,
              'date_selector': 'time[pubdate][datetime]', 'date_attribute': 'datetime', 'date_format': 'iso_date',
              'feeds': [{'kind': 'news', 'selector': '#haberlerdiv .haber a[href]', 'title_selector': 'h3'}]}
    source = sources_for_engine({'sources': [config]})[0]
    title = 'Öğrencilerden Belediyemize Ziyaret'
    url = 'https://www.keciborlu.bel.tr/genel/ogrencilerden-belediyemize-ziyaret/'
    photos = [f'https://www.keciborlu.bel.tr/wp-content/uploads/2026/10/ziyaret-{n}.jpeg' for n in (1, 2)]
    html = ('<title>Keçiborlu Belediyesi</title>' f'<h1 class="page-title">{title}</h1>'
            + ('<time pubdate datetime="2026-10-29"></time>' if dated else '')
            + '<div class="entry-content"><p>İlçemizdeki öğrenciler belediyemizi ziyaret ederek çalışmaları inceledi.</p>'
            + ''.join(f'<p><img src="{photo}"></p>' for photo in photos) + '</div>')
    item = {'source_id': 'keciborlu-belediye', 'kind': 'news', 'url': url, 'title': title,
            'published_at': '2026-10-29T00:00:00+03:00'}
    return source, item, photos, html


def test_district_portal_body_photo_is_bound_by_its_own_reviewed_reader():
    source, item, photos, html = portal_case()
    assert source['photo_inline_selector'] == 'img[src]'
    assert candidate(html, item['url'], item, source) == photos[0]
    with pytest.raises(ValueError):
        candidate(html.replace('Keçiborlu Belediyesi</title>', 'Başka Belediye</title>'), item['url'], item, source)
    with pytest.raises(ValueError):
        candidate(html, item['url'], {**item, 'published_at': '2026-10-28T00:00:00+03:00'}, source)


def test_portal_page_without_its_own_date_keeps_no_photo():
    # Isparta Belediyesi dates news only on its listing (and robots.txt blocks /kurumlar).
    source, item, photos, html = portal_case(dated=False)
    with pytest.raises(ValueError, match='identity'):
        candidate(html, item['url'], item, source)


def calendar_case():
    source = sources_for_engine({'sources': [{'id': 'sdu-calendar', 'name': 'Örnek takvim',
        'url': 'https://example.org/calendar', 'reader': 'sdu', 'research_enabled': True}]})[0]
    html = '''<div class="modal-body"><img src="/poster.jpg" alt="Etkinlik afişi"><table>
      <tr><th>Etkinlik Adı</th><td>Isparta açık konseri</td></tr>
      <tr><th>Etkinlik Tarihi</th><td>25.10.2026</td></tr>
      <tr><th>Açıklama</th><td>Etkinlik herkese açıktır.<br>Saat: 20:00–22:00<br>Yer: Isparta Kültür Merkezi</td></tr>
      </table></div>'''
    item = {'source_id': 'sdu-calendar', 'kind': 'event', 'url': source['url'],
            'title': 'Isparta açık konseri', 'start': '2026-10-25T20:00:00+03:00',
            'end': '2026-10-25T22:00:00+03:00', 'time_known': True,
            'location': 'Isparta Kültür Merkezi', 'status': 'scheduled'}
    return source, item, html


def test_reviewed_calendar_matches_exact_session_and_not_jsonld_or_page_title():
    source,item,html = calendar_case()
    assert candidate(html,item['url'],item,source) == 'https://example.org/poster.jpg'
    for field,value in [('start','2026-10-26T20:00:00+03:00'), ('location','Başka salon')]:
        with pytest.raises(ValueError): candidate(html,item['url'],{**item,field:value},source)
    with pytest.raises(ValueError):
        candidate(html.replace('Etkinlik afişi','Arşiv fotoğrafı'),item['url'],item,source)


def test_calendar_description_date_conflict_cannot_reuse_matching_session_image():
    source,item,html = calendar_case()
    html = html.replace('Etkinlik herkese açıktır.', 'Etkinlik herkese açıktır. 24 Ekim 2026 tarihinde.')
    with pytest.raises(ValueError): candidate(html,item['url'],item,source)


def test_roadworks_source_photo_subject_never_becomes_generated_scene_permission():
    with pytest.raises(MatchRejected,match='Unsupported visual subject'):
        validate_match(b'unused','roadworks')


def test_roadworks_photo_does_not_pass_a_competing_ordinary_traffic_scene(monkeypatch):
    import io
    from PIL import Image
    image = io.BytesIO()
    Image.new('RGB',(1080,720),'#706f6b').save(image,'JPEG')
    values = {label: .1 for label in LABELS}
    values.update(roadworks=.32,traffic=.34)
    monkeypatch.setattr('news_engine.visual_match.scores',lambda images:[values for _ in images])
    with pytest.raises(MatchRejected,match='Visual subject mismatch'):
        validate_news_photo(image.getvalue(),'roadworks')


@pytest.mark.parametrize('title', [
    'Isparta caddesinde yol yenileme çalışması yapılacak',
    'Isparta için yol yenileme uyarısı',
    'Isparta spor müsabakası yarın oynanacak',
])
def test_planned_or_warning_news_does_not_acquire_incident_photo_subject(title):
    assert news_subject({'kind':'news','title':title}) is None
