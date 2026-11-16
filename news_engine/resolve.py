"""Owner-run closing of Instagram claims whose delivery outcome is unknown.

`publish_one` never resends a claim once it reached Meta, and `settle_expired`
only marks a claim whose container reads `EXPIRED` as known unsent; it keeps
the claim open in the posts table. A claim left `publishing` or `uncertain`
for any other reason (container `PUBLISHED`, `FINISHED`, `ERROR`, or a status
read that keeps failing) is counted as `unresolved` for good. 16 Nov 2026:
the 4 Nov `publishing` claim still held the panel at `unresolved: 1`.

This module runs only from the manual `resolve-uncertain.yml` workflow.

* Dry run (default) reads each open claim's container status and reports it.
  It writes nothing.
* Apply: `PUBLISHED` closes the claim as `published` (the container status
  does not name the media, so `media_id` stays empty and the payload records
  `resolution`); `EXPIRED`, `ERROR` and `FINISHED` close it as
  `not_published`, a terminal status that is never claimed, counted or
  queued again. Anything else is left untouched.

Only `GET /{container}?fields=status_code` is called; nothing is ever posted.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta

from .domain import parse_date
from .security import RESOLUTIONS

OPEN = ('publishing', 'uncertain')
NOT_PUBLISHED = 'not_published'
# Past the claim's own day and the 48-hour delivery audit window, so a closed
# claim no longer competes with today's slots or an automatic readback.
RESOLVE_AFTER = timedelta(hours=48)
CONTAINER_STATES = frozenset(('PUBLISHED', 'FINISHED', 'EXPIRED', 'ERROR', 'IN_PROGRESS'))
UNUSED = {'EXPIRED': 'container_expired', 'ERROR': 'container_error', 'FINISHED': 'container_finished'}
POST_STATUSES = frozenset(('prepared', 'blocked_source', 'superseded', 'expired', 'published',
                           'publishing', 'uncertain', NOT_PUBLISHED))
ACTIONS = frozenset(('marked_published', 'marked_not_published', 'would_mark_published',
                     'would_mark_not_published', 'skipped_no_container', 'skipped_media_recorded',
                     'skipped_in_progress', 'skipped_unknown_state', 'skipped_unreadable',
                     'skipped_too_recent', 'skipped_not_open', 'skipped_changed', 'not_found'))


def valid_post_id(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r'[a-f0-9]{24}', value) is not None


def container_state(api, container: str) -> tuple[str | None, str | None]:
    """(status_code, read error code). Never a response body, URL or token."""
    import requests
    from .instagram import delivery_error
    try:
        value = api.call(container, 'GET', fields='status_code').get('status_code')
    except (requests.RequestException, RuntimeError, KeyError, ValueError, AttributeError) as exc:
        return None, delivery_error(exc)
    return (value, None) if value in CONTAINER_STATES else ('unknown', None)


def resolve(store, api, at: datetime, *, apply: bool = False, post_id: str | None = None) -> dict:
    if post_id is not None and not valid_post_id(post_id):
        raise ValueError('Invalid post identity')
    posts = store.posts()
    rows = []
    if post_id is not None:
        target = next((p for p in posts if p['id'] == post_id), None)
        if target is None:
            return report(apply, [{'post_id': post_id, 'action': 'not_found'}])
        if target['status'] not in OPEN:
            return report(apply, [{'post_id': post_id, 'status': target['status'], 'action': 'skipped_not_open'}])
        posts = [target]
    claims = sorted((p for p in posts if p['status'] in OPEN), key=lambda p: (p.get('published_at') or '', p['id']))
    for post in claims:
        stamp = parse_date(post.get('published_at'))
        row = {'post_id': post['id'], 'format': 'story' if post.get('publish_format') == 'story' else 'feed',
               'status': post['status'], 'published_at': stamp.isoformat() if stamp else None,
               'container_id': post.get('container_id'), 'delivery_error': post.get('delivery_error')}
        rows.append(row)
        if post.get('media_id'):
            row['action'] = 'skipped_media_recorded'
            continue
        if not post.get('container_id'):
            row['action'] = 'skipped_no_container'
            continue
        state, error = container_state(api, post['container_id'])
        row['container_state'] = state
        if error:
            row['read_error'] = error
            row['action'] = 'skipped_unreadable'
            continue
        if state == 'IN_PROGRESS':
            row['action'] = 'skipped_in_progress'
            continue
        if state != 'PUBLISHED' and state not in UNUSED:
            row['action'] = 'skipped_unknown_state'
            continue
        if not stamp or at - stamp < RESOLVE_AFTER:
            row['action'] = 'skipped_too_recent'
            continue
        published = state == 'PUBLISHED'
        if not apply:
            row['action'] = 'would_mark_published' if published else 'would_mark_not_published'
            continue
        payload = {k: v for k, v in post.items() if k not in ('status', 'container_id', 'media_id')}
        payload['resolution'] = 'container_published' if published else UNUSED[state]
        with store.db:
            changed = store.db.execute(
                "UPDATE posts SET status=?,payload=? WHERE id=? AND status=? AND container_id=? AND media_id IS NULL",
                ('published' if published else NOT_PUBLISHED, json.dumps(payload, ensure_ascii=False),
                 post['id'], post['status'], post['container_id']))
        row['action'] = ('marked_published' if published else 'marked_not_published') if changed.rowcount == 1 else 'skipped_changed'
    return report(apply, rows)


def report(apply: bool, rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row['action']] = counts.get(row['action'], 0) + 1
    return safe_report({'mode': 'apply' if apply else 'dry_run', 'claims': rows, 'actions': counts})


def safe_report(value: dict) -> dict:
    """Only enumerated codes, hex/number identifiers and timestamps; no captions or provider text."""
    def code(v, allowed):
        return v if isinstance(v, str) and v in allowed else ('invalid' if v is not None else None)

    def pattern(v, regex):
        return v if isinstance(v, str) and re.fullmatch(regex, v) else ('invalid' if v is not None else None)

    def stamp(v):
        parsed = parse_date(v) if isinstance(v, str) else None
        return parsed.isoformat() if parsed and parsed.tzinfo else ('invalid' if v is not None else None)

    rows = []
    for row in value.get('claims', []):
        clean = {'post_id': pattern(row.get('post_id'), r'[a-f0-9]{24}'),
                 'action': code(row.get('action'), ACTIONS) or 'invalid'}
        for key, check in (('format', lambda v: code(v, {'feed', 'story'})),
                           ('status', lambda v: code(v, POST_STATUSES)),
                           ('published_at', stamp),
                           ('container_id', lambda v: pattern(v, r'\d{1,32}')),
                           ('container_state', lambda v: code(v, CONTAINER_STATES | {'unknown'})),
                           ('delivery_error', lambda v: pattern(v, r'[a-z0-9_]{1,30}')),
                           ('read_error', lambda v: pattern(v, r'[a-z0-9_]{1,30}'))):
            if key in row:
                clean[key] = check(row[key])
        rows.append(clean)
    actions = {k: v for k, v in value.get('actions', {}).items() if k in ACTIONS and type(v) is int and v >= 0}
    return {'mode': 'apply' if value.get('mode') == 'apply' else 'dry_run', 'claims': rows, 'actions': actions,
            'meta_writes': 0}


def write_summary(result: dict, target):
    clean = safe_report(result)
    with open(target, 'a', encoding='utf-8') as out:
        out.write('### Belirsiz Instagram yayın kayıtları\n\n```json\n' + json.dumps(clean, indent=2) + '\n```\n\n')
        out.write('`dry_run`: yalnız rapor, durum değişmedi. `would_mark_*` uygulama modunda yapılacak değişikliği, '
                  '`skipped_*` dokunulmayan kaydı gösterir. Meta\'ya yalnız GET yapıldı.\n')
