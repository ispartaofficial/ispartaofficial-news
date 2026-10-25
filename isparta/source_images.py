"""Source-specific image context; the reviewed reader still proves each item.

No HTML search, filename match or image model can establish article/session
identity. These adapters re-read the same fields used by normal research.
"""
from .readers import article, isubu, sdu
from .scope_readers import ticket_sessions

VERSION = 'isparta-source-images-v1'
ARTICLE_SCOPES = {
    # The hero is outside .article-text and uses the publisher's own CDN.
    'bomba32': '.news-section .inner',
    'haber32': '.news-section .inner',
    # The lazy hero has srcset only, outside the text-content child article.
    'ajans32': '.article-detail.news-detail',
}


def profile(source):
    if source.get('reader') not in ('article', 'sdu', 'isubu', 'ticketing'):
        return {}
    return {'photo_identity_reader': VERSION,
            **({'photo_article_selector': ARTICLE_SCOPES[source['id']]}
               if source['id'] in ARTICLE_SCOPES else {}),
            # This publisher supplies natural originals as direct body
            # paragraphs; its OpenGraph hero is often a text-heavy collage.
            **({'photo_inline_selector': '.article-text > p > img[src]'}
               if source['id'] == 'haber32' else {})}


def identity_rows(html, url, source):
    reader = source.get('reader')
    rows = ([article(html, url, source)] if reader == 'article' else
            ticket_sessions(html, url, source) if reader == 'ticketing' else
            {'sdu': sdu, 'isubu': isubu}[reader](html, source))
    for row in rows:
        if row['kind'] == 'event':
            row['end'] = row.get('end') or row.get('start')
            row['status'] = 'scheduled'
    return rows
