"""Independent research report. No social credentials, media fetch or publication.

"eligible_for_drafting" means only that source/date/area gates passed. It never
means factual corroboration, licensed imagery, visual approval or delivery.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re

from .fetch import Fetcher, error_code
from .outage_reader import aedas_outages
from .readers import DISTRICTS, OUTSIDE, TZ, article, isubu, news_links, norm, sdu, timestamp
from .scope_readers import (archive_article, campus_notice, correlate_campus, culture_items,
                           culture_year_link, listed_sessions, listing_entries, ticket_sessions)
from .district_readers import (campus_portal, club_directory, official_article,
                               official_entries, official_locality)

ROOT = Path(__file__).resolve().parents[1]
# Busy news listings move a local story out of the newest four links within an
# hour or two; reviewed sources may opt into a wider, still bounded window.
ARTICLE_LINK_CAP = 12
# An event outside the run's reads loses its "reobserved" status, so a city's
# whole short listing is read instead of rotating through it.
LISTED_SESSION_CAP = 14
# Bomba32 prints paid pieces with no section label (29 Oct: a developer's "yeni
# adresi" text ran as news). One such phrase occurs in real reporting; three
# different ones in a story mean a sales text, which waits for review.
SALES_PHRASES = ('ayricalikli', 'konforlu', 'modern yaşam', 'yaşam alan', 'yaşam kalite', 'yeni adres', 'prestijli',
                 'lüks', 'daire seçenek', 'satiş ofis', 'uygun fiyat', 'müşteri memnuniyet', 'kaliteli hizmet')
SALES_THRESHOLD = 3


def local_news(value):
    n = norm(value)
    # Aksu and Gönen are ambiguous elsewhere in Türkiye; never accept them alone.
    words = ('isparta',) + tuple(norm(x) for x in DISTRICTS)
    return any(re.search(r'\b' + re.escape(w) + r'(?:\b|li\b|da\b|de\b)', n) for w in words)


def local_venue(location, source_id, venues):
    n = norm(location)
    if not n or re.search(OUTSIDE, n):
        return False
    if local_news(n):
        return True
    return any(source_id in row['sources'] and norm(row['label']) == n for row in venues)


def assess(item, at, venues):
    reasons = list(item.get('parser_holds', []))
    combined = norm(item['title'] + ' ' + item['description'])
    if re.search(r'\b(?:kaybettiklerimiz|cenaze\w*|defin\w*|taziye\w*|vefat\w*|şehit\w*)\b', combined):
        reasons.append('sensitive_claim_requires_review')
    if not item['title'] or len(item['description']) < 30:
        reasons.append('insufficient_source_text')
    if re.search(r'\b(?:iptal|ertelendi|ertelenmiştir|ertelenmistir|vazgeçildi)\b', combined):
        reasons.append('cancelled_or_postponed_requires_review')
    if re.search(r'\b(?:cinayet\w*|intihar\w*|tutuk\w*|gözalt\w*|yarali\w*|hayatini kaybet\w*|ölüm\w*|iddia\w*|tecavüz\w*|istismar\w*|deprem\w*|sel felaketi|seçim\w*|siyasi|ak parti|chp|mhp)\b', combined):
        reasons.append('sensitive_claim_requires_review')
    if item['kind'] == 'news':
        if sum(phrase in combined for phrase in SALES_PHRASES) >= SALES_THRESHOLD:
            reasons.append('promotional_copy_requires_review')
        if re.search(r'\b(?:bebek\w*|çocuk\w*|özel gereksinim\w*|hastaliği|tedavisi)\b', combined):
            reasons.append('personal_or_child_story_requires_review')
        when = timestamp(item.get('published_at'))
        if not when:
            reasons.append('original_publication_date_missing')
        elif when > at:
            reasons.append('future_publication_time')
        elif at - when > timedelta(hours=48):
            reasons.append('news_older_than_48h')
        if not local_news(combined) and not official_locality(item, combined):
            reasons.append('Isparta_locality_unconfirmed')
        # A freshly uploaded old notice must not become a fresh service alert.
        # These need a separate event/service validity reader before drafting.
        if re.search(r'\b(?:konser|festival|tiyatro|kermes|etkinlik|atölye|workshop|kesinti|uyari|firtina|meteoroloji|başvuru|basvuru|son tarih|ihale)\w*\b', combined):
            reasons.append('event_or_notice_validity_requires_review')
    else:
        start, end = timestamp(item.get('start')), timestamp(item.get('end'))
        if not start or not item.get('time_known'):
            reasons.append('explicit_start_time_missing')
        elif start <= at:
            reasons.append('event_already_started')
        elif start > at + timedelta(days=30):
            reasons.append('event_beyond_30_day_window')
        if end and start and end < start:
            reasons.append('event_end_before_start')
        if end and end <= at:
            reasons.append('event_ended')
        if item.get('date_conflict'):
            reasons.append('calendar_and_description_dates_conflict')
        if re.search(r'\b(?:gerçekleştirildi|düzenlendi|tamamlandi|sona erdi)\b', combined):
            reasons.append('event_description_reports_completion')
        if not local_venue(item.get('location'), item['source_id'], venues):
            reasons.append('Isparta_venue_unconfirmed')
        if item.get('audience', {}).get('kind') == 'unknown':
            reasons.append('participation_conditions_unknown')
    item['holds'] = sorted(set(reasons))
    item['eligible_for_drafting'] = not reasons
    item['publication_ready'] = False
    return item


def same_story(a, b):
    if a['kind'] != b['kind']:
        return False
    ta, tb = norm(a['title']), norm(b['title'])
    # Two ticket listings spell one venue differently: Ozbi / Ozbi Konseri, 21:30.
    if a['kind'] == 'event' and a.get('start') and a.get('start') == b.get('start') and (ta in tb or tb in ta):
        return True
    if a['kind'] == 'event' and (a.get('start'), norm(a.get('location'))) != (b.get('start'), norm(b.get('location'))):
        return False
    if ta == tb:
        return True
    # Conservative current-batch matching. Persistent publication deduplication
    # belongs to the later delivery engine and is not claimed by this report.
    words_a = set(re.findall(r'\w+', norm(a['description'])))
    words_b = set(re.findall(r'\w+', norm(b['description'])))
    overlap = len(words_a & words_b) / max(1, min(len(words_a), len(words_b)))
    return SequenceMatcher(None, ta, tb).ratio() >= .74 and overlap >= .80


def deduplicate(items):
    kept = []
    for item in items:
        prior = next((a for a in kept if same_story(a, item)), None)
        if prior:
            item['duplicate_of'] = prior['id']
            item['eligible_for_drafting'] = False
            item['holds'] = sorted(set(item['holds'] + ['same_story_in_current_batch']))
        else:
            kept.append(item)


def collect_sources(config_path, *, at=None, fetcher=None):
    at = at or datetime.now(TZ)
    if at.tzinfo is None:
        raise ValueError('Timezone-aware run timestamp required')
    config = json.loads(Path(config_path).read_text(encoding='utf-8'))
    sources = [s for s in config['sources'] if s.get('research_enabled')]
    if not sources or len(sources) > 40 or len({s['id'] for s in sources}) != len(sources):
        raise ValueError('Reviewed unique source registry required')
    discovery_sources=[s for s in config.get('discovery_sources',[]) if s.get('research_enabled')]
    if len(discovery_sources)>4:
        raise ValueError('Reviewed discovery budget exceeded')
    fetcher = fetcher or Fetcher(sources+discovery_sources)
    items, health = [], []
    for source in sources:
        row = {'id': source['id'], 'name': source['name'], 'url': source['url'],
               'checked_at': at.isoformat(), 'read_pages': 0, 'parsed_items': 0, 'errors': []}
        try:
            body, final = fetcher.get(source['url'])
            row['read_pages'] += 1
            if source['reader'] == 'article':
                links = news_links(body, source, limit=min(ARTICLE_LINK_CAP, source.get('max_details', 4)))
                if not links:
                    raise ValueError('reviewed_article_links_missing')
                for url in links:
                    try:
                        page, detail_url = fetcher.get(url)
                        row['read_pages'] += 1
                        item = article(page, detail_url, source)
                        item['evidence_sha256'] = hashlib.sha256(page.encode()).hexdigest()
                        items.append(assess(item, at, config['venues']))
                        row['parsed_items'] += 1
                    except Exception as exc:
                        row['errors'].append({'stage': 'detail', 'url': url, 'code': error_code(exc)})
            elif source['reader'] in ('archive_article','campus_notice','ticketing','listed_sessions','culture_archive','official_portal','campus_portal'):
                listing_source=source
                if source['reader']=='culture_archive':
                    year_url=culture_year_link(body,source,at)
                    if year_url:
                        body,final=fetcher.get(year_url)
                        row['read_pages']+=1
                        listing_source=dict(source,url=final)
                    else:
                        row['note']='current_year_archive_not_published'
                        body=''
                limit=min({'ticketing':8,'listed_sessions':LISTED_SESSION_CAP}.get(source['reader'],4),source.get('max_details',4))
                entries=(official_entries(body,source,at,limit) if source['reader']=='official_portal'
                         else listing_entries(body,listing_source,at,limit))
                if not entries and 'note' not in row:
                    raise ValueError('reviewed_source_entries_missing')
                for entry in entries:
                    try:
                        page,detail_url=fetcher.get(entry['url'])
                        row['read_pages']+=1
                        if source['reader']=='ticketing':parsed=ticket_sessions(page,detail_url,source)
                        elif source['reader']=='listed_sessions':parsed=listed_sessions(page,detail_url,source)
                        elif source['reader']=='culture_archive':parsed=culture_items(page,detail_url,source,entry)
                        else:
                            reader={'archive_article':archive_article, 'campus_notice':campus_notice,
                                    'official_portal':official_article, 'campus_portal':campus_portal}[source['reader']]
                            parsed=[reader(page,detail_url,source,entry)]
                        for item in parsed:
                            item['evidence_sha256']=hashlib.sha256(page.encode()).hexdigest()
                            items.append(assess(item,at,config['venues']))
                        row['parsed_items']+=len(parsed)
                    except Exception as exc:
                        row['errors'].append({'stage':'detail','url':entry['url'],'code':error_code(exc)})
            else:
                parsed = (aedas_outages(body, source, at) if source['reader'] == 'aedas_outages'
                          else {'sdu': sdu, 'isubu': isubu}[source['reader']](body, source))
                for item in parsed:
                    item['evidence_sha256'] = hashlib.sha256(body.encode()).hexdigest()
                    items.append(assess(item, at, config['venues']))
                row['parsed_items'] = len(parsed)
            row['status'] = 'partial' if row['errors'] else 'parsed' if row['parsed_items'] else 'empty'
        except Exception as exc:
            row['status'] = 'failed'
            row['errors'].append({'stage': 'listing_or_calendar', 'code': error_code(exc)})
        health.append(row)
    discovery_health, discovered_clubs = [], []
    for source in discovery_sources:
        row={'id':source['id'],'url':source['url'],'checked_at':at.isoformat(),'status':'failed'}
        try:
            body,final=fetcher.get(source['url'])
            clubs=club_directory(body,source)
            discovered_clubs.extend(clubs)
            row.update(status='directory_read',organisations=len(clubs),event_records=0,
                       evidence_sha256=hashlib.sha256(body.encode()).hexdigest())
        except Exception as exc:
            row['error']=error_code(exc)
        discovery_health.append(row)
    correlate_campus(items)
    for item in items:
        item['holds']=sorted(set(item['holds']+item.get('parser_holds',[])))
        item['eligible_for_drafting']=not item['holds']
    # Identical same-source cards can appear twice. Conflicting payloads under
    # one stable identity are held together rather than silently selecting one.
    unique = {}
    for item in items:
        if item['id'] in unique:
            prior = unique[item['id']]
            if any(prior.get(k) != item.get(k) for k in ('title','description','start','end','location')):
                prior['holds'] = sorted(set(prior['holds'] + ['conflicting_source_identity']))
                prior['eligible_for_drafting'] = False
        else:
            unique[item['id']] = item
    items = list(unique.values())
    deduplicate(items)
    for row in health:
        source_items=[i for i in items if i['source_id']==row['id']]
        row['eligible_for_drafting']=sum(i['eligible_for_drafting'] for i in source_items)
        row['held_items']=sum(not i['eligible_for_drafting'] for i in source_items)
    for item in items:
        item['checked_at'] = at.isoformat()
    # Service/local news stays in the report even when campus events dominate.
    # This is a research ordering, not the future publication scheduler.
    items.sort(key=lambda i: (not i['eligible_for_drafting'], i['kind'] != 'event', i['title']))
    return {'schema': 'isparta-research-v1', 'checked_at': at.isoformat(),
            'publishing_enabled': False, 'source_health': health, 'items': items,
            'discovery_health':discovery_health,'discovered_clubs':discovered_clubs,
            'summary': {'sources': len(sources), 'parsed_items': len(items),
                        'eligible_for_drafting': sum(i['eligible_for_drafting'] for i in items),
                        'publication_ready': 0,
                        'holds': dict(Counter(r for i in items for r in i['holds']))}}


def public_report(collection):
    """Copy/redact; full bodies never enter artifacts or the public report."""
    from copy import deepcopy
    report = deepcopy(collection)
    items = report['items']
    for item in items:
        # Evidence excerpts and links, not full third-party article republication.
        description = item.pop('description')
        item['source_text_sha256'] = hashlib.sha256(description.encode()).hexdigest()
        item['source_excerpt'] = description[:600]
        item['excerpt_is_complete'] = len(description) <= 600
        if item.get('audience', {}).get('evidence'):
            evidence = item['audience'].pop('evidence')
            item['audience']['evidence_excerpt'] = evidence[:600]
            item['audience']['evidence_is_complete'] = len(evidence) <= 600
    return report


def run(config_path, *, at=None, fetcher=None):
    return public_report(collect_sources(config_path, at=at, fetcher=fetcher))


def main():
    parser = argparse.ArgumentParser(description='Isparta source research only; no publishing')
    parser.add_argument('--config', type=Path, default=ROOT / 'config/research-sources.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'state/research.json')
    args = parser.parse_args()
    report = run(args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False))
    summary_file = __import__('os').environ.get('GITHUB_STEP_SUMMARY')
    if summary_file:
        rows = ['## Isparta kaynak araştırması', '',
                'Bu çalışma araştırma yapar. Instagram/Facebook paylaşımı yapmaz.', '',
                '| Kaynak | Okuma | Ayrıştırılan kayıt |', '|---|---|---:|']
        rows += [f"| {s['name']} | {s['status']} | {s['parsed_items']} |" for s in report['source_health']]
        rows += ['', f"Toplam {len(report['items'])} kayıt; {report['summary']['eligible_for_drafting']} kayıt taslak incelemesine uygun. Yayına hazır kayıt: 0.",
                 '', 'Tüm gerekçeler ve kaynak adresleri research.json dosyasında.']
        if report['discovery_health']:
            rows += ['', 'Topluluk dizini ayrı keşiftir; listelenen topluluklar çalışan etkinlik okuyucusu sayılmaz.']
            rows += [f"- {d['id']}: {d['status']}; {d.get('organisations',0)} topluluk, 0 etkinlik kaydı." for d in report['discovery_health']]
        with open(summary_file, 'a', encoding='utf-8') as handle:
            handle.write('\n'.join(rows)+'\n')
    if all(s['status'] == 'failed' for s in report['source_health']):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
