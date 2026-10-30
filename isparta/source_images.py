"""Source-specific image context; the reviewed reader still proves each item.

No HTML search, filename match or image model can establish article/session
identity. These adapters re-read the same fields used by normal research.
"""
from bs4 import BeautifulSoup

from .district_readers import official_article
from .readers import article, isubu, sdu, text
from .scope_readers import archive_article, ticket_sessions

VERSION = 'isparta-source-images-v1'
ARTICLE_SCOPES = {
    # The hero is outside .article-text and uses the publisher's own CDN.
    'bomba32': '.news-section .inner',
    'haber32': '.news-section .inner',
    # The lazy hero has srcset only, outside the text-content child article.
    'ajans32': '.article-detail.news-detail',
}
# These publishers supply natural originals as direct body paragraphs; their
# OpenGraph hero is often a headline collage (30 Oct: Ethem amca, Yiğit).
INLINE = {'haber32': '.article-text > p > img[src]', 'bomba32': '.article-text > p > img[src]'}
# Municipal and district portals put their own event photos in the body.
PAGE_READERS = {'archive_article': archive_article, 'official_portal': official_article}


def profile(source):
    reader = source.get('reader')
    if reader not in ('article', 'sdu', 'isubu', 'ticketing', *PAGE_READERS):
        return {}
    inline = INLINE.get(source['id']) or ('img[src]' if reader in PAGE_READERS else None)
    return {'photo_identity_reader': VERSION,
            **({'photo_article_selector': ARTICLE_SCOPES[source['id']]}
               if source['id'] in ARTICLE_SCOPES else {}),
            **({'photo_inline_selector': inline} if inline else {})}


def page_rows(html, url, source):
    """Re-read a portal article with its own reviewed reader.

    The listing isn't fetched again: the page heading stands in for the
    listing title, and only a date printed on the page can match the item.
    Isparta Belediyesi prints none, and its robots.txt (like the district
    governorates') disallows /kurumlar, where its photos live, anyway.
    """
    heading = BeautifulSoup(html, 'html.parser').select_one(source['title_selector'])
    entry = {'url': url, 'title': text(heading) if heading else '', 'archive_date': None,
             'archive_date_conflict': False, 'feed_kind': 'news'}
    return [PAGE_READERS[source['reader']](html, url, source, entry)]


def identity_rows(html, url, source):
    reader = source.get('reader')
    rows = ([article(html, url, source)] if reader == 'article' else
            page_rows(html, url, source) if reader in PAGE_READERS else
            ticket_sessions(html, url, source) if reader == 'ticketing' else
            {'sdu': sdu, 'isubu': isubu}[reader](html, source))
    for row in rows:
        if row['kind'] == 'event':
            row['end'] = row.get('end') or row.get('start')
            row['status'] = 'scheduled'
    return rows
