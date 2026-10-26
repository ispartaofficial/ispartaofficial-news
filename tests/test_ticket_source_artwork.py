"""The exact ticket session can reuse its provider's own promotional artwork."""
from copy import deepcopy

import pytest

from test_scope_readers import ticket_html,genre_breadcrumb,SOURCES
from isparta.runtime import adapt,sources_for_engine
from isparta.scope_readers import ticket_sessions
from news_engine.source_photos import candidate_urls


@pytest.mark.parametrize('change', [None, 'date', 'venue'])
def test_photo_manager_reads_parent_but_still_checks_the_original_session(tmp_path, monkeypatch, change):
    import io
    from contextlib import closing
    from unittest.mock import Mock
    from PIL import Image
    from news_engine.domain import parse_date
    from news_engine.source_photos import SourcePhotos
    from news_engine.store import Store

    source=sources_for_engine({'sources':[SOURCES['bubilet-isparta']]})[0]
    parent='https://www.bubilet.com.tr/isparta/etkinlik/ornek'
    image='https://cdn.bubilet.com.tr/cdn-cgi/image/width=1200,quality=100/files/Etkinlik/ornek.png'
    html=ticket_html().replace('https://cdn.bubilet.com.tr/event.png',image)+genre_breadcrumb()
    html+=f'<link rel="canonical" href="{parent}">'
    row=adapt(ticket_sessions(html,parent,source)[0])
    if change=='date':row['start']='2026-11-08T20:30:00+03:00'
    if change=='venue':row['location']='Başka salon'
    at=parse_date('2026-10-26T08:00:00+03:00')
    monkeypatch.setenv('SOURCE_PHOTOS_ENABLED','true')
    monkeypatch.setattr('news_engine.event_image_text.validate',lambda *args,**kwargs:True)
    check=Mock()
    monkeypatch.setattr('news_engine.visual_match.validate_event_photo',check)
    raw=io.BytesIO();Image.new('RGB',(640,960),'#345678').save(raw,'JPEG')
    fetcher=Mock();fetcher.get.return_value=(html,parent)
    fetcher.image.return_value=(raw.getvalue(),image)
    with closing(Store(tmp_path/'state.sqlite')) as store:
        store.upsert(row,at.isoformat());item=store.items()[0]
        photos=SourcePhotos(store,at,tmp_path/'photos',[source],fetcher=fetcher)
        result=photos.image(item)
        fetcher.get.assert_called_once_with(parent)
        assert photos.stats['source_checks']==1
        assert (result is not None)==(change is None)
        assert fetcher.image.call_count==(1 if change is None else 0)
        if change is None:
            saved=store.rows('SELECT payload FROM source_photos')[0]['payload']
            assert item['url'] in saved and item['start'] in saved
        else:
            assert photos.stats['rejection_stages']=={'source_binding':1}
        check.assert_not_called()  # Title-checked poster is not a stage-photo test.


def test_exact_session_redirect_and_reviewed_cdn_artwork_are_bound_together():
    source=sources_for_engine({'sources':[SOURCES['bubilet-isparta']]})[0]
    parent='https://www.bubilet.com.tr/isparta/etkinlik/ornek'
    image='https://cdn.bubilet.com.tr/cdn-cgi/image/width=1200,quality=100/files/Etkinlik/ornek.png'
    html=ticket_html().replace('https://cdn.bubilet.com.tr/event.png',image)
    row=ticket_sessions(html,parent,source)[0];item=adapt(row)
    assert item['url']==parent+'/seans/123'
    assert candidate_urls(html,parent,item,source)==[image]
    for changed in (parent+'-baska','https://foreign.example/isparta/etkinlik/ornek'):
        with pytest.raises(ValueError):candidate_urls(html,changed,item,source)
    wrong=deepcopy(item);wrong['start']='2026-11-08T20:30:00+03:00'
    with pytest.raises(ValueError):candidate_urls(html,parent,wrong,source)
    with pytest.raises(ValueError):candidate_urls(html.replace('cdn.bubilet.com.tr','foreign.example'),parent,item,source)
