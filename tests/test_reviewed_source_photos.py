import hashlib
from pathlib import Path
import pytest
from news_engine.source_photos import cleaned_photo
from news_engine.reviewed_source_photos import REVIEWS, reviewed_article, reviewed_photo


@pytest.mark.parametrize('index,name',[(0,'official-visit-exif-zero.jpg'),(1,'thyme-article.jpg')])
def test_review_is_bound_to_actual_cleaned_pixels_and_every_article_field(index,name):
    row=REVIEWS[index];item={k:row[k] for k in ('source_id','url','title','published_at')};item['kind']='news'
    raw=Path('tests/fixtures/visual-followup',name).read_bytes();data=cleaned_photo(raw)
    assert reviewed_photo(data,item,row['image_url'],row['subject'])
    assert hashlib.sha256(data).hexdigest()==row['sha256']
    for field in ('source_id','url','title','published_at','kind'):
        other={**item,field:item[field]+'-changed'}
        assert not reviewed_article(other)
        assert not reviewed_photo(data,other,row['image_url'],row['subject'])
    assert not reviewed_photo(data+b'x',item,row['image_url'],row['subject'])
    assert not reviewed_photo(data,item,row['image_url']+'?changed=1',row['subject'])
    assert not reviewed_photo(data,item,row['image_url'],'traffic')
    other=REVIEWS[1-index]
    assert not reviewed_photo(data,{**item,'title':other['title']},row['image_url'],row['subject'])


def test_unknown_article_has_no_manual_exemption():
    assert not reviewed_article({})
    assert not reviewed_photo(b'unknown',{},'https://example.com/image.jpg','meeting')


@pytest.mark.parametrize('index,name',[(0,'official-visit-exif-zero.jpg'),(1,'thyme-article.jpg')])
@pytest.mark.parametrize('failure',['model_reject','checker_unavailable','identity_reject','wrong_pixels'])
def test_the_articles_own_picture_needs_only_its_live_identity(tmp_path,monkeypatch,index,name,failure):
    # Owner's rule, 12 Nov: a failed or missing model check no longer leaves the story to a scene.
    from contextlib import closing
    from unittest.mock import Mock
    from news_engine import source_photos,visual_match
    from news_engine.domain import parse_date
    from news_engine.store import Store
    row=REVIEWS[index];item={k:row[k] for k in ('source_id','url','title','published_at')}
    item.update(kind='news',category='news',id='a'*24,revision=1)
    at=parse_date('2026-10-27T18:30:00+03:00')
    source=dict(id='bomba32',url='https://www.bomba32.com/',kind='html',enabled=True,trusted=True,access='robots')
    raw=Path('tests/fixtures/visual-followup',name).read_bytes()
    if failure=='wrong_pixels':
        raw=Path('tests/fixtures/visual-followup','thyme-article.jpg' if index==0 else 'official-visit-exif-zero.jpg').read_bytes()
    fetcher=Mock();fetcher.get.return_value=('verified-source',item['url']);fetcher.image.return_value=(raw,row['image_url'])
    def candidates(*args):
        if failure=='identity_reject':raise ValueError('Article identity mismatch')
        return [row['image_url']]
    def model(*args):
        if failure=='checker_unavailable':raise visual_match.MatchUnavailable('Unavailable')
        raise visual_match.MatchRejected('Rejected')
    monkeypatch.setenv('SOURCE_PHOTOS_ENABLED','true')
    monkeypatch.setattr(source_photos,'candidate_urls',candidates)
    monkeypatch.setattr(source_photos,'validate_news_photo',model)
    monkeypatch.setattr(visual_match,'validate_headline_photo',model)
    # This test is about identity. Where the text reader is installed the visit
    # graphic loses its headline band, which test_headline_band covers.
    monkeypatch.setattr('news_engine.headline_band.without_band',lambda data:data)
    with closing(Store(tmp_path/'state.sqlite')) as store:
        reader=source_photos.SourcePhotos(store,at,tmp_path/'photos',[source],fetcher=fetcher)
        result=reader.image(item)
        if failure=='identity_reject':
            assert result is None
            assert store.rows('SELECT * FROM source_photos')==[]
        else:
            assert result and result[1].read_bytes()==cleaned_photo(raw)
            assert len(store.rows('SELECT * FROM source_photos'))==1
