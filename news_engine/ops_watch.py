"""Independent public health observer and deduplicated owner GitHub alerts."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import timedelta
from pathlib import Path

from .domain import TZ, now, parse_date

REPO = 'ispartaofficial/ispartaofficial-news'
PANEL = 'https://ispartaofficial.github.io/ispartaofficial-news/data.json'
MARKER = '<!-- isparta-operations-watch:v1 -->'
LABELS = {
    'panel_unreachable': 'Canlı durum verisine erişilemiyor.',
    'invalid_panel': 'Canlı durum verisi doğrulanamadı.',
    'research_stale': 'Son tamamlanmış araştırma beklenen aralıktan eski.',
    'source_coverage_drop': 'Kaynakların en az yüzde 40’ı okunamıyor veya kısmi okunuyor.',
    'weather_missing': 'Sabah hava yayını penceresi kapandı; başarılı günlük teslim kaydı yok.',
    'pharmacy_missing': 'Nöbetçi eczane yayını penceresi kapandı; başarılı günlük teslim kaydı yok.',
    'unresolved_delivery': 'Sonucu belirsiz Instagram veya Facebook teslimi var; yeniden gönderilmedi.',
    'delivery_audit_failed': 'Son 24 saatte yayın sonrası okuma kontrolü başarısız veya uyumsuz.',
    'research_failed': 'Son iki ana dal araştırması başarısız.',
    'backup_missing': 'Son iki gün içinde başarılı bağımsız yedek işi bulunamadı.',
    'source_silent': 'Daha önce kayıt veren kaynak, beklenen süre boyunca yeni kayıt vermedi; şu an boş veya okunamıyor.',
}


def quiet(snapshot):
    """Unacknowledged silent readers; only reviewed config ids and dates enter issues."""
    rows = snapshot.get('quiet_sources', []) if isinstance(snapshot, dict) else []
    result = []
    for row in rows if isinstance(rows, list) else []:
        stamp = parse_date(row.get('last_new_item_at')) if isinstance(row, dict) else None
        if (stamp and row.get('acknowledged') is False and row.get('status') in ('empty', 'failed')
                and re.fullmatch(r'[a-z0-9-]{1,80}', str(row.get('source_id', '')))):
            result.append((row['source_id'], row['status'], stamp.astimezone(TZ).date().isoformat()))
    return sorted(result)


def stale_after(local):
    # research.yml runs 07:20–23:50 TR and GitHub skips some slots (gaps up to
    # 157 min seen on 25–30 Oct). Overnight only a missing morning run counts.
    return timedelta(hours=3) if local.hour >= 10 else timedelta(hours=11)


def daily_missing(story, panel_time, hour, minute):
    # Only research deploys refresh the panel, and its slots are irregular.
    # Judge a window from a panel built after it closed; staleness is separate.
    closed = panel_time.hour > hour or (panel_time.hour == hour and panel_time.minute >= minute)
    story = story or {}
    return closed and (story.get('day') != panel_time.date().isoformat() or story.get('status') != 'published')


def evaluate(snapshot, at):
    if not isinstance(snapshot, dict) or snapshot.get('demo') is not False:
        return ['invalid_panel']
    finished = next((parse_date(r.get('finished_at')) for r in snapshot.get('runs', []) if r.get('finished_at')), None)
    if not finished or finished > at + timedelta(minutes=5):
        return ['invalid_panel']
    local = at.astimezone(TZ)
    problems = []
    if at - finished > stale_after(local):
        problems.append('research_stale')
    health = snapshot.get('source_health', [])
    if health and sum(r.get('status') in ('failed', 'partial') for r in health) / len(health) >= .4:
        problems.append('source_coverage_drop')
    if snapshot.get('publishing_enabled') is True:
        panel_time = finished.astimezone(TZ)
        if daily_missing(snapshot.get('weather_story'), panel_time, 9, 20):
            problems.append('weather_missing')
        if daily_missing(snapshot.get('pharmacy_story'), panel_time, 18, 20):
            problems.append('pharmacy_missing')
        unresolved = snapshot.get('operations', {}).get('unresolved', {})
        if any(isinstance(v, int) and v > 0 for v in unresolved.values()):
            problems.append('unresolved_delivery')
    if snapshot.get('factory', {}).get('delivery_audit', {}).get('recent_failures', 0):
        problems.append('delivery_audit_failed')
    if quiet(snapshot):
        problems.append('source_silent')
    return sorted(problems)


class Github:
    def __init__(self, token, session):
        self.token, self.session = token, session

    def call(self, method, path, **kwargs):
        response = self.session.request(method, 'https://api.github.com/repos/' + REPO + '/' + path,
            headers={'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28'}, timeout=(5, 15), allow_redirects=False, **kwargs)
        if not response.ok or response.status_code >= 300:
            raise RuntimeError('GitHub observation or notification failed')
        return response.json() if response.content else {}


def workflow_problems(api, at):
    result = []
    # Publication is a job of research.yml here, so a failed publish fails the run.
    rows = api.call('GET', 'actions/workflows/research.yml/runs', params={'branch': 'main', 'per_page': 6}).get('workflow_runs', [])
    rows = [r for r in rows if r.get('head_branch') == 'main' and r.get('status') == 'completed'
            and r.get('conclusion') not in ('skipped', 'cancelled')]
    if len(rows) >= 2 and all(r.get('conclusion') == 'failure' for r in rows[:2]):
        stamp = parse_date(rows[0].get('created_at'))
        if stamp and at - stamp <= timedelta(days=2):
            result.append('research_failed')
    rows = api.call('GET', 'actions/workflows/state-backup.yml/runs', params={'branch': 'main', 'per_page': 8}).get('workflow_runs', [])
    if not any(r.get('conclusion') == 'success' and (stamp := parse_date(r.get('created_at')))
               and at - timedelta(days=2) <= stamp <= at for r in rows):
        result.append('backup_missing')
    return result


def notify(api, problems, at, silent=()):
    problems = sorted(set(problems))
    if any(p not in LABELS for p in problems):
        raise ValueError('Unapproved incident code')
    silent = sorted(silent) if 'source_silent' in problems else []
    if any(not re.fullmatch(r'[a-z0-9-]{1,80}', sid) or status not in ('empty', 'failed')
           or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) for sid, status, day in silent):
        raise ValueError('Unapproved silent source detail')
    # A changed set of silent readers is a new state, so the issue is updated.
    fingerprint = hashlib.sha256((','.join(problems) + '|' + ','.join(s[0] for s in silent)).encode()).hexdigest()[:24]
    stamp = '<!-- state:' + fingerprint + ' -->'
    issues = api.call('GET', 'issues', params={'state': 'all', 'per_page': 100, 'creator': 'github-actions[bot]'})
    previous = next((r for r in issues if not r.get('pull_request') and MARKER in (r.get('body') or '')
                     and r.get('user', {}).get('login') == 'github-actions[bot]'), None)
    if previous and stamp in (previous.get('body') or '') and (previous.get('state') == 'open') == bool(problems):
        return 'unchanged'
    body = MARKER + '\n' + stamp + '\n\n'
    body += ('Kontrol: ' + at.astimezone(TZ).isoformat() + '\n\n')
    detail = {'failed': 'okunamıyor', 'empty': 'boş'}
    lines = []
    for p in problems:
        lines.append('- ' + LABELS[p])
        if p == 'source_silent':
            lines += ['  - `' + sid + '`: ' + detail[status] + ', son yeni kayıt ' + day for sid, status, day in silent]
    body += '\n'.join(lines) if problems else 'Önceki işletim uyarıları bu kontrolde görülmedi.'
    body += '\n\n[Sistem paneli](https://ispartaofficial.github.io/ispartaofficial-news/) · [Kontrol işleri](https://github.com/' + REPO + '/actions/workflows/operations-watch.yml)\n\nBu kontrol paylaşım yapmaz; kayıtları sıfırlamaz.'
    if not previous:
        if not problems:
            return 'healthy_no_issue'
        api.call('POST', 'issues', json={'title': 'IspartaOfficial — otomatik işletim uyarısı', 'body': body, 'assignees': ['ispartaofficial']})
        return 'opened'
    path = 'issues/' + str(previous['number'])
    api.call('PATCH', path, json={'body': body, 'state': 'open' if problems else 'closed'})
    api.call('POST', path + '/comments', json={'body': body})
    return 'updated' if problems else 'resolved'


def main():
    import requests
    at = now()
    session = requests.Session()
    problems, silent = [], []
    try:
        r = session.get(PANEL, timeout=(5, 20), allow_redirects=False)
        snapshot = r.json() if r.status_code == 200 else None
        problems = evaluate(snapshot, at) if snapshot is not None else ['panel_unreachable']
        silent = quiet(snapshot) if snapshot is not None else []
    except (requests.RequestException, ValueError, TypeError, KeyError):
        problems = ['panel_unreachable']
    result = {'version': 'operations-watch-v1', 'checked_at': at.isoformat(), 'problems': problems,
              'notification': 'settings_missing', 'publication_attempted': False}
    token = os.getenv('GITHUB_TOKEN', '')
    try:
        if token:
            api = Github(token, session)
            problems = sorted(set(problems + workflow_problems(api, at)))
            result.update(problems=problems, silent_sources=[s[0] for s in silent],
                          notification=notify(api, problems, at, silent))
    except (requests.RequestException, RuntimeError, ValueError, KeyError, TypeError):
        result['notification'] = 'failed'
    path = Path('work/operations-watch/summary.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
    if result['notification'] in ('failed', 'settings_missing'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
