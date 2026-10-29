"""City boundary around the reused production engine; no imported state/secrets."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from news_engine.domain import CATEGORIES, TZ, digest, now, normalized, parse_date
from news_engine.editor import caption, excerpt, news_body, verify
from news_engine.pipeline import export
from news_engine.security import ITEM_FIELDS, assert_no_secrets, validate_state
from news_engine.store import Store
from news_engine.timeliness import with_validity
from .research import collect_sources, public_report

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'ispartaofficial/ispartaofficial-news'
SITE = 'https://ispartaofficial.github.io/ispartaofficial-news'


def sources_for_engine(config):
    """Reviewed registry only; campus feed origins don't grant arbitrary trust."""
    result = []
    for source in config['sources']:
        if not source.get('research_enabled'):
            continue
        from .source_images import profile as photo_profile
        result.append({**source, **photo_profile(source), 'enabled': True, 'trusted': True, 'access': 'robots',
                       'kind': 'html', 'article_selector': source.get('body_selector', 'article'),
                       'reviewed_local_scope': source['id'] not in ('bomba32', 'haber32', 'kanal32', 'ajans32')})
    return result


def category(row):
    # A venue or incidental body detail doesn't identify the main subject.
    # For example, land-sale text can mention sports facilities without being
    # sports news. News uses only explicit headline cues. Ticket event genres
    # come from an exact event-bound provider breadcrumb, never a venue name.
    if row['kind'] == 'event' and row['source_id'] == 'bubilet-isparta':
        supplied = row.get('source_event_category')
        if supplied in ('theatre', 'concert', 'festival', 'cinema'):
            return supplied
    value = normalized(row['title'])
    words = (('outage', r'\bkesinti\w*'), ('theatre', r'\btiyatro\w*'),
             ('concert', r'\bkonser\w*|\bcanli müzik\b'), ('festival', r'\bfestival\w*'),
             ('cinema', r'\bsinema\w*|\bfilm göster\w*'), ('sport', r'\bspor\w*|\bturnuva\w*'),
             ('family', r'\bçocuk oyunu\b'),
             ('culture', r'\bsergi\w*|\batölye\w*|\bsöyleşi\w*'),
             ('transport', r'\bulaşim\w*|\btrafik\w*|\basfalt\w*'))
    if row['kind'] == 'event':
        words += (('education', r'\b(?:eğitim|kurs|seminer|konferans)(?:i|u|lar|lari|ler|leri)?\b'),)
    return next((label for label, pattern in words if re.search(pattern, value)),
                'event' if row['kind'] == 'event' else 'municipality' if 'belediye' in row['source_id'] else 'news')


def participation(row):
    evidence = row.get('audience', {}).get('evidence') or ''
    # Preserve literal relevant sentences, never turn a restricted invite public.
    sentences = re.split(r'(?<=[.!?])\s+|\n+', evidence)
    relevant = [s for s in sentences if re.search(
        r'öğrenci|üye|başvuru|kayıt|kontenjan|halka açık|herkese açık|yaş|kimlik|davetiye', s, re.I)]
    if not relevant:
        relevant = [s for s in sentences if re.search(r'bilet gereklidir|biletli|bilete tabidir', s, re.I)]
    return ' '.join(relevant) or ('Herkese açık' if row.get('audience', {}).get('kind') == 'public' else '')


def adapt(row):
    if 'description' not in row:
        raise ValueError('Full source collection required; public excerpts are not verification evidence')
    fields = {k: deepcopy(v) for k, v in row.items() if k in ITEM_FIELDS}
    fields.update(identity='https://' + urlsplit(row['url']).hostname + '/#isparta-record-' + row['id'],
                  sources=[row['url']], category=category(row),
                  verification_holds=list(row.get('holds', [])))
    if row['kind'] == 'event':
        fields.update(status='scheduled', audience_kind=row.get('audience', {}).get('kind', 'unknown'),
                      participation=participation(row),
                      free=True if row.get('fee') == 'Ücretsiz' else None)
        # An absent end clock is never filled with the publication timestamp.
        fields.setdefault('end', fields.get('start'))
        if len(fields['participation']) > 500:
            fields['verification_holds'].append('participation_conditions_exceed_card_budget')
        if type(row.get('price')) in (int, float):
            fields['price'] = str(row['price'])
    return with_validity(fields)


def ingest(store, collection, sources, at):
    source_map = {s['id']: s for s in sources}
    errors = [{'source_id': h['id'], 'code': 'source_not_current'} for h in collection['source_health']
              if h['status'] in ('failed', 'partial', 'empty')]
    with store.db:
        run_id = store.db.execute('INSERT INTO runs(started_at) VALUES(?)', (at.isoformat(),)).lastrowid
    accepted = 0
    accepted_by_source = {}
    stored_keys = set()
    for row in collection['items']:
        item = adapt(row)
        source = source_map.get(item['source_id'], {})
        reason = verify(item, source, at)
        if reason:
            store.withhold(row['id'], reason, at.isoformat())
            # A new source hold must revoke an older pending preparation in
            # this same run, even if it was eligible less than one hour ago.
            key = digest(item['kind'] + ':' + item['identity'])
            with store.db:
                old = store.rows('SELECT payload FROM items WHERE id=?', (key,))
                if old:
                    payload = json.loads(old[0]['payload'])
                    payload['verification_holds'] = [reason]
                    store.db.execute('UPDATE items SET payload=? WHERE id=?', (json.dumps(payload, ensure_ascii=False), key))
                store.db.execute("UPDATE posts SET status='blocked_source' WHERE item_id=? AND status IN ('prepared','blocked_source')", (key,))
            continue
        # The full body was checked above. Persist only a bounded display excerpt;
        # don't expose the full third-party article in a public state branch.
        item['description'] = excerpt(news_body(item) if item['kind'] == 'news' else item['description'], 600)
        assert_no_secrets(item)
        stored, _ = store.upsert(item, at.isoformat())
        if stored != digest(item['kind'] + ':' + item['identity']):
            # Another reviewed source re-observed an existing story through the
            # cross-source duplicate path. Its current verification lifts only
            # the reobservation hold; every content/verification hold stays.
            with store.db:
                old = store.rows('SELECT payload FROM items WHERE id=?', (stored,))
                payload = json.loads(old[0]['payload'])
                holds = payload.get('verification_holds') or []
                if 'not_reobserved_current_run' in holds:
                    payload['verification_holds'] = [h for h in holds if h != 'not_reobserved_current_run']
                    store.db.execute('UPDATE items SET payload=? WHERE id=?',
                                     (json.dumps(payload, ensure_ascii=False), stored))
        stored_keys.add(stored)
        accepted += 1
        accepted_by_source[item['source_id']] = accepted_by_source.get(item['source_id'], 0) + 1
    observed = {digest(row['kind'] + ':' + adapt(row)['identity']) for row in collection['items']} | stored_keys
    with store.db:
        for previous in store.items():
            if previous['id'] in observed:
                continue
            payload = {k: v for k, v in previous.items() if k in ITEM_FIELDS}
            payload['verification_holds'] = ['not_reobserved_current_run']
            store.db.execute('UPDATE items SET payload=? WHERE id=?',
                             (json.dumps(payload, ensure_ascii=False), previous['id']))
            store.db.execute("UPDATE posts SET status='blocked_source' WHERE item_id=? AND status IN ('prepared','blocked_source')", (previous['id'],))
    with store.db:
        for h in collection['source_health']:
            n = accepted_by_source.get(h['id'], 0)
            store.db.execute('INSERT OR REPLACE INTO source_health VALUES(?,?,?,?,?,?,?)',
                (h['id'], at.isoformat(), {'parsed': 'ok', 'partial': 'partial', 'empty': 'empty'}.get(h['status'], 'failed'),
                 h['parsed_items'], n, len(h['errors']), None))
        store.db.execute('UPDATE runs SET finished_at=?,collected=?,errors=? WHERE id=?',
                         (at.isoformat(), len(collection['items']), json.dumps(errors), run_id))
        store.db.execute('DELETE FROM runs WHERE id NOT IN (SELECT id FROM runs ORDER BY id DESC LIMIT 100)')
    return accepted


def run(db_path, public_dir, config_path, *, at=None, fetcher=None, collection=None):
    at = at or now()
    if at.tzinfo is None:
        raise ValueError('Timezone-aware timestamp required')
    config = json.loads(Path(config_path).read_text(encoding='utf-8'))
    live_collection = collection is None
    collection = collection if collection is not None else collect_sources(config_path, at=at, fetcher=fetcher)
    if parse_date(collection['checked_at']) != at:
        raise ValueError('Collection must belong to this run')
    store = Store(db_path)
    try:
        sources = sources_for_engine(config)
        accepted = ingest(store, collection, sources, at)
        from news_engine.schedule import prepare
        prepare(store, at)
        if live_collection:
            from news_engine.pharmacy import refresh as refresh_pharmacy
            refresh_pharmacy(store, at)
            settings = json.loads((ROOT / 'config/runtime.json').read_text(encoding='utf-8'))
            if settings.get('weather_enabled') is True:
                from news_engine.weather import refresh_weather
                refresh_weather(store, at)
        assets = export(store, Path(public_dir), sources, at)
        validate_state(Path(db_path))
        report = public_report(collection)
        report['engine'] = {'version': 'isparta-core-port-v1', 'accepted_items': accepted,
            'prepared_parents': sum(p['status'] == 'prepared' and not p.get('publish_format') for p in store.posts()),
            'rendered_parents': len(assets), 'publishing_enabled': False,
            'publication_configured': json.loads((ROOT/'config/runtime.json').read_text(encoding='utf-8')).get('publishing_enabled') is True}
        return report
    finally:
        store.close()


def initial_launch_allowed(store, target, event):
    if event != 'workflow_dispatch' or not re.fullmatch(r'[a-f0-9]{24}', target):
        return False
    claims = [p for p in store.posts() if p['status'] in ('publishing','published','uncertain')]
    return all(p['id'] == target or p.get('parent_post_id') == target for p in claims)


def publish(db_path, public_dir):
    """Production core remains gated until independent account setup is verified."""
    profile = json.loads((ROOT/'config/runtime.json').read_text(encoding='utf-8'))
    if profile.get('publishing_enabled') is not True or profile.get('meta_connected') is not True:
        return {'status': 'disabled'}
    if os.getenv('GITHUB_REPOSITORY') != REPOSITORY or os.getenv('GITHUB_REF') != 'refs/heads/main':
        raise ValueError('Isparta main workflow required')
    from news_engine.instagram import Instagram, publish_automatic
    api = Instagram()
    if api.auth_mode != profile.get('instagram_auth_mode'):
        return {'status': 'authentication_mode_mismatch'}
    if not api.enabled():
        return {'status': 'disabled'}
    if reason := api.identity_problem('ispartaofficial'):
        return {'status': reason}
    # A separate runner reads only the public manifest; raw image bytes are
    # rechecked by the inherited deployed-asset gate immediately before writes.
    import requests
    response = requests.get(SITE + '/data.json', timeout=(8, 25), allow_redirects=False)
    if response.status_code != 200 or len(response.content) > 8_000_000:
        return {'status': 'media_not_deployed'}
    manifest = response.json()
    if manifest.get('demo') or manifest.get('brand', {}).get('version') != 'isparta-rose-v1':
        raise ValueError('Independent deployed Isparta manifest required')
    from news_engine.state_git import persist
    store = Store(db_path)
    try:
        assets = {p['id']: p['assets'] for p in manifest['posts']}
        # Real publication always checkpoints remotely before contacting Meta.
        target = os.getenv('INITIAL_POST_ID', '')
        if target:
            if not initial_launch_allowed(store, target, os.getenv('GITHUB_EVENT_NAME')):
                return {'status': 'already_claimed'}
            from news_engine.instagram import publish_requested
            result = publish_requested(store, now(), SITE, assets, target, adapter=api,
                                       checkpoint=lambda: persist(Path(db_path)), require_visual_review=True)
        else:
            result = publish_automatic(store, now(), SITE, assets, adapter=api,
                                       checkpoint=lambda: persist(Path(db_path)), require_visual_review=True)
        from news_engine.operations import record_check
        return record_check(store, result, now(), 'automatic')
    finally:
        store.close()


def main():
    parser = argparse.ArgumentParser(description='Isparta independent source and production core')
    parser.add_argument('action', choices=('prepare', 'publish'))
    parser.add_argument('--db', type=Path, default=Path('state/platform.sqlite'))
    parser.add_argument('--public', type=Path, default=Path('dist'))
    parser.add_argument('--config', type=Path, default=ROOT/'config/research-sources.json')
    parser.add_argument('--report', type=Path, default=Path('state/research.json'))
    args = parser.parse_args()
    if args.action == 'publish':
        print(json.dumps(publish(args.db, args.public)))
        return
    report = run(args.db, args.public, args.config)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report['engine'], ensure_ascii=False))
    if summary_file := os.getenv('GITHUB_STEP_SUMMARY'):
        rows = ['## Isparta içerik hazırlığı', '',
                'Bu iş yalnız araştırır ve kart hazırlar. Sosyal teslim ayrı yayın işinde doğrulanır.', '',
                f"Araştırılan kayıt: {len(report['items'])}; çekirdeğin kabulü: {report['engine']['accepted_items']}; "
                f"kartı hazırlanan içerik: {report['engine']['rendered_parents']}.", '',
                '| Kaynak | Okuma | Ayrıştırılan |', '|---|---|---:|']
        rows += [f"| {s['name']} | {s['status']} | {s['parsed_items']} |" for s in report['source_health']]
        with open(summary_file, 'a', encoding='utf-8') as stream:
            stream.write('\n'.join(rows) + '\n')


if __name__ == '__main__':
    main()
