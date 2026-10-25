"""Reviewed natural source images; bounded alternatives never bypass vision."""
import io
import json
from contextlib import closing
from unittest.mock import Mock

import pytest
from PIL import Image

from isparta.runtime import sources_for_engine
from news_engine.domain import parse_date
from news_engine.source_photo_data import approved_image_url, validate_record
from news_engine.source_photos import SourcePhotos, candidate_urls, cleaned_photo
from news_engine.store import Store
from news_engine.visual_match import MatchRejected, MatchUnavailable

AT=parse_date('2026-10-25T15:30:00+03:00')
CDN='https://haber32comtr.teimg.com/haber32-com-tr/uploads/2026/10/'


def jpeg(size=(1024,768),color='#345678'):
    out=io.BytesIO();Image.new('RGB',size,color).save(out,'JPEG')
    return out.getvalue()


def context():
    source=sources_for_engine({'sources':[{'id':'haber32','name':'Haber32',
        'url':'https://www.haber32.com.tr/','research_enabled':True,'reader':'article',
        'title_selector':'h1','body_selector':'.article-text','date_selector':'meta[name=datePublished]'}]})[0]
    title='Isparta kooperatifinin genel kurul toplantısı yapıldı'
    url='https://www.haber32.com.tr/isparta-kooperatif-genel-kurul'
    item={'kind':'news','title':title,'description':'Isparta kooperatifinin genel kurulunda faaliyetler ve projeler görüşüldü.',
          'source_id':'haber32','source_name':'Haber32','url':url,'sources':[url],
          'category':'news','published_at':'2026-10-25T14:23:00+03:00'}
    html=f'''<meta name="datePublished" content="{item['published_at']}">
      <meta property="og:image" content="{CDN}collage.jpg">
      <div class="news-section"><div class="inner"><h1>{title}</h1>
      <img src="{CDN}collage.jpg" alt="{title}"><div class="article-text">
      <p>{item['description']}</p><div class="related"><a href="/unrelated-exam">
      <img src="{CDN}unrelated.jpg" alt="Başka sınav haberi"></a></div>
      <p><img src="{CDN}outdoors.jpg" alt="Toplantı sonrası alan incelemesi"></p>
      <p><img src="{CDN}meeting.jpg" alt="Genel kurul toplantısı"></p>
      <p><img src="{CDN}third.jpg" alt="Üçüncü kaynak fotoğrafı"></p>
      </div></div></div>'''
    return source,item,html


def test_exact_haber32_scope_prefers_two_direct_originals_over_collage_and_related_news():
    source,item,html=context()
    assert candidate_urls(html,item['url'],item,source)==[CDN+'outdoors.jpg',CDN+'meeting.jpg']
    with pytest.raises(ValueError,match='identity mismatch'):
        candidate_urls(html,item['url'],{**item,'published_at':'2026-10-24T14:23:00+03:00'},source)
    with pytest.raises(ValueError,match='identity mismatch'):
        candidate_urls(html,item['url'],{**item,'title':'Başka haberin genel kurul toplantısı'},source)


def test_exact_article_body_can_be_a_sibling_of_hero_without_accepting_second_article():
    source,item,html=context()
    html=html.replace('<div class="article-text">','</div></div><div class="article-text">')
    html=html.replace('</div></div></div>','</div>')
    assert candidate_urls(html,item['url'],item,source)==[CDN+'outdoors.jpg',CDN+'meeting.jpg']
    for name in ('outdoors.jpg','meeting.jpg','third.jpg'):
        html=html.replace(name,'reklam-'+name)
    html+=f'<div class="article-text"><p><img src="{CDN}different-article.jpg"></p></div>'
    assert candidate_urls(html,item['url'],item,source)==[CDN+'collage.jpg']


def test_inline_archival_or_advertising_photos_do_not_gain_preference():
    source,item,html=context()
    html=html.replace('Toplantı sonrası alan incelemesi','Arşiv fotoğrafı')
    assert candidate_urls(html,item['url'],item,source)==[CDN+'meeting.jpg',CDN+'third.jpg']
    html=html.replace('meeting.jpg','reklam-banner.jpg')
    assert candidate_urls(html,item['url'],item,source)==[CDN+'third.jpg']


@pytest.mark.parametrize('url',[
    'https://haber32comtr.teimg.com/another-publisher/uploads/a.jpg',
    'https://haber32comtr.teimg.com/haber32-com-tr/uploads/../../another/a.jpg',
    'https://haber32comtr.teimg.com/haber32-com-tr/uploads/a.jpg?redirect=1',
    'https://haber32comtr.teimg.com.evil.example/haber32-com-tr/uploads/a.jpg',
    'https://bomba32com.teimg.com/bomba32-com/uploads/a.jpg',
])
def test_haber32_delivery_origin_is_not_a_wildcard_or_cross_publisher_permission(url):
    assert not approved_image_url('haber32','https://www.haber32.com.tr/article',url)


def test_natural_standard_four_by_three_photo_keeps_full_frame():
    raw=jpeg((2048,1536))
    clean=cleaned_photo(raw)
    with Image.open(io.BytesIO(clean)) as image:
        assert image.width/image.height==4/3
        assert image.getexif()=={} and image.format=='JPEG'


@pytest.mark.parametrize('size',[(639,480),(480,640),(640,1200),(800,800),(4096,3072)])
def test_small_portrait_square_or_oversized_news_photos_remain_rejected(size):
    with pytest.raises(ValueError,match='Unsupported source photo dimensions'):
        cleaned_photo(jpeg(size))


def setup(tmp_path,monkeypatch,*,failure=None):
    monkeypatch.setenv('SOURCE_PHOTOS_ENABLED','true')
    source,item,html=context();store=Store(tmp_path/'state.sqlite')
    key,_=store.upsert(item,AT.isoformat());item=store.items()[0]
    fetcher=Mock();fetcher.get.return_value=(html,item['url'])
    first,second=jpeg(color='#ab1000'),jpeg(color='#0020ab')
    fetcher.image.side_effect=[(first,CDN+'outdoors.jpg'),(second,CDN+'meeting.jpg')]
    checks=[]
    def check(data,expected):
        checks.append((data,expected))
        if failure=='unavailable':raise MatchUnavailable('private checker text')
        if failure=='all_rejected' or len(checks)==1:raise MatchRejected('private diagnostic must not escape')
    monkeypatch.setattr('news_engine.source_photos.validate_news_photo',check)
    photos=SourcePhotos(store,AT,tmp_path/'photos',[source],fetcher=fetcher)
    return store,item,photos,fetcher,checks


def test_second_original_must_pass_same_model_within_existing_two_read_budget(tmp_path,monkeypatch):
    store,item,photos,fetcher,checks=setup(tmp_path,monkeypatch)
    with closing(store):
        # A prior claim and all of its SQL columns stay untouched.
        frozen={'id':'f'*24,'kind':'news','revision':1,'due_at':AT.isoformat(),
                'title':'Donmuş önceki haber','published_at':AT.isoformat()}
        store.queue(frozen)
        with store.db:store.db.execute("UPDATE posts SET status='published' WHERE id=?",(frozen['id'],))
        before=store.rows("SELECT * FROM posts WHERE status='published'")
        result=photos.image(item)
        assert result and photos.reads==2 and fetcher.get.call_count==1 and fetcher.image.call_count==2
        assert [expected for _,expected in checks]==['meeting','meeting']
        row=store.rows('SELECT * FROM source_photos')[0]
        value=validate_record(row['id'],row['item_id'],row['revision'],row['payload'],row['image'])
        assert value['image_url']==CDN+'meeting.jpg'
        assert photos.stats['downloaded']==1 and photos.stats['rejected']==1
        assert photos.stats['rejection_stages']=={'visual_subject':1}
        assert store.rows("SELECT * FROM posts WHERE status='published'")==before
        assert photos.image({**item,'id':'e'*24}) is None
        assert fetcher.image.call_count==2 and photos.stats['deferred']==1
        assert 'private' not in json.dumps(photos.stats)


@pytest.mark.parametrize('failure,reads,counter',[('unavailable',1,'unavailable'),('all_rejected',2,'rejected')])
def test_missing_model_or_both_mismatches_never_save_a_picture(tmp_path,monkeypatch,failure,reads,counter):
    store,item,photos,fetcher,checks=setup(tmp_path,monkeypatch,failure=failure)
    with closing(store):
        assert photos.image(item) is None
        assert fetcher.image.call_count==reads and len(checks)==reads
        assert photos.stats[counter]==reads
        assert store.rows('SELECT * FROM source_photos')==[]
        assert photos.stats['rejection_stages']=={'visual_subject':reads}
