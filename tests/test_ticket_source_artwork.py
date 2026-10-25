"""The exact ticket session can reuse its provider's own promotional artwork."""
from copy import deepcopy

import pytest

from test_scope_readers import ticket_html,SOURCES
from isparta.runtime import adapt,sources_for_engine
from isparta.scope_readers import ticket_sessions
from news_engine.source_photos import candidate_urls


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
