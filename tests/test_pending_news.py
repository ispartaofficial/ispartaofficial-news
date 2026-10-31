"""A story that leaves a short news list is not a withdrawn story."""
from contextlib import closing
from datetime import timedelta
import json
from pathlib import Path

from isparta.research import collect_sources
from isparta.runtime import PENDING_NEWS_CAP, ingest, pending_news, sources_for_engine
from news_engine.domain import parse_date
from news_engine.schedule import prepare
from news_engine.store import Store

CONFIG = json.loads((Path(__file__).parents[1]/'config/research-sources.json').read_text(encoding='utf8'))
SOURCE = dict(next(s for s in CONFIG['sources'] if s['id'] == 'bomba32'), link_selector='a', detail_path='/[a-z0-9-]+')
AT = parse_date('2026-10-21T18:00:00+03:00')
HOME = SOURCE['url']


def page(title):
    return f'''<meta name="datePublished" content="2026-10-21T15:00:00+03:00">
    <h1 itemprop="headline">{title}</h1><div class="article-text"><p>Isparta Belediyesi merkezde yol ve kaldırım
    çalışmaları hakkında ayrıntılı açıklama yaptı. Çalışmalar kent genelinde sürüyor.</p></div>'''


class Site:
    def __init__(self):
        self.pages = {}
        self.reads = []

    def publish(self, slug, title):
        self.pages['https://www.bomba32.com/' + slug] = page(title)

    def listing(self, *slugs):
        self.pages[HOME] = ''.join(f'<a href="https://www.bomba32.com/{slug}">haber</a>' for slug in slugs)

    def get(self, url):
        self.reads.append(url)
        if url not in self.pages:
            raise ValueError('offline')
        return self.pages[url], url


def pipeline(tmp_path):
    config = dict(CONFIG, sources=[SOURCE])
    path = tmp_path/'sources.json'
    path.write_text(json.dumps(config), encoding='utf8')
    return path, sources_for_engine(config)


def turn(store, path, sources, site, at):
    report = collect_sources(path, at=at, fetcher=site, pending=pending_news(store, at))
    ingest(store, report, sources, at)
    prepare(store, at)
    return report


def statuses(store):
    return {p['status'] for p in store.posts() if p['kind'] == 'news' and not p.get('publish_format')}


def test_story_that_left_the_list_stays_current_through_its_own_page(tmp_path):
    path, sources = pipeline(tmp_path)
    site = Site()
    site.publish('yol-calismasi', 'Isparta’da yol çalışması sürüyor')
    site.listing('yol-calismasi')
    with closing(Store(tmp_path/'state.sqlite')) as store:
        turn(store, path, sources, site, AT)
        assert statuses(store) == {'prepared'}
        site.publish('baska-haber', 'Isparta’da kaldırım çalışması başladı')
        site.listing('baska-haber')
        report = turn(store, path, sources, site, AT + timedelta(hours=2))
        assert 'https://www.bomba32.com/yol-calismasi' in site.reads[-2:]
        assert report['source_health'][0]['status'] == 'parsed'
        story = next(i for i in store.items() if 'yol çalışması' in i['title'])
        assert story['verification_holds'] == [] and story['revision'] == 1
        assert statuses(store) == {'prepared'}


def test_removed_page_holds_only_that_story(tmp_path):
    path, sources = pipeline(tmp_path)
    site = Site()
    site.publish('yol-calismasi', 'Isparta’da yol çalışması sürüyor')
    site.publish('baska-haber', 'Isparta’da kaldırım çalışması başladı')
    site.listing('yol-calismasi', 'baska-haber')
    with closing(Store(tmp_path/'state.sqlite')) as store:
        turn(store, path, sources, site, AT)
        del site.pages['https://www.bomba32.com/yol-calismasi']
        site.listing('baska-haber')
        report = turn(store, path, sources, site, AT + timedelta(hours=2))
        assert report['source_health'][0]['status'] == 'parsed' and report['source_health'][0]['errors'] == []
        held = next(i for i in store.items() if 'yol çalışması' in i['title'])
        assert held['verification_holds'] == ['not_reobserved_current_run']
        assert statuses(store) == {'prepared', 'blocked_source'}


def test_only_recent_waiting_stories_are_read_again_within_the_cap(tmp_path):
    with closing(Store(tmp_path/'state.sqlite')) as store:
        def add(key, hours, status='prepared'):
            url = f'https://www.bomba32.com/{key}'
            item = {'kind': 'news', 'title': key, 'description': 'd', 'url': url, 'sources': [url], 'source_id': 'bomba32',
                    'source_name': 'Bomba32', 'category': 'news', 'identity': url,
                    'published_at': (AT - timedelta(hours=hours)).isoformat()}
            item_id, _ = store.upsert(item, AT.isoformat())
            store.queue({'id': key, 'item_id': item_id, 'revision': 1, 'kind': 'news', 'due_at': AT.isoformat(),
                         'title': key, 'caption': 'c', 'category': 'news', 'source_urls': [url], 'slides': [],
                         'formats': ['feed', 'story']})
            with store.db:
                store.db.execute('UPDATE posts SET status=? WHERE id=?', (status, key))
        add('published-story', 1, 'published')
        add('old-story', 60)
        for hours in range(PENDING_NEWS_CAP + 2):
            add(f'waiting-{hours}', hours, 'blocked_source' if hours % 2 else 'prepared')
        urls = pending_news(store, AT)['bomba32']
    assert urls == [f'https://www.bomba32.com/waiting-{hours}' for hours in range(PENDING_NEWS_CAP)]
