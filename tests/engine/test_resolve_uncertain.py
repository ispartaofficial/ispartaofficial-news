import json
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yaml

from news_engine.instagram import Instagram, prepare_story_jobs, publish_one
from news_engine.operations import summary
from news_engine.publication_policy import day_claims
from news_engine.resolve import NOT_PUBLISHED, RESOLVE_AFTER, resolve, safe_report, write_summary
from news_engine.schedule import prepare
from news_engine.security import validate_state

ROOT = Path(__file__).resolve().parents[2]


def claim(store, event, at, status='publishing', container='1850', **extra):
    """An open claim like the 4 Nov one: container made, media_publish unknown."""
    store.upsert(event, at.isoformat())
    prepare(store, at)
    post = next(p for p in store.posts() if p['status'] == 'prepared' and not p.get('publish_format'))
    payload = {**{k: v for k, v in post.items() if k not in ('status', 'container_id', 'media_id')},
               'published_at': at.isoformat(), **extra}
    with store.db:
        store.db.execute('UPDATE posts SET status=?,container_id=?,payload=? WHERE id=?',
                         (status, container, json.dumps(payload), post['id']))
    return post['id']


def reader(state=None, failure=None):
    api = Mock()
    api.enabled.return_value = True
    api.account = '1234'
    api.session.head.return_value = SimpleNamespace(status_code=200, headers={'Content-Type': 'image/jpeg'})
    api.container.return_value = 'container-2'
    if failure:
        api.call.side_effect = failure
    else:
        api.call.return_value = {'status_code': state}
    return api


def only_status_reads(api, containers):
    assert [c.args for c in api.call.call_args_list] == [(c, 'GET') for c in containers]
    assert all(c.kwargs == {'fields': 'status_code'} for c in api.call.call_args_list)
    api.container.assert_not_called()


def row(store, key):
    return store.rows('SELECT status,container_id,media_id,payload FROM posts WHERE id=?', (key,))[0]


def test_published_container_closes_the_claim_as_published_without_media_id(store, event, at):
    key = claim(store, event, at)
    assert summary(store, at + RESOLVE_AFTER)['unresolved']['instagram'] == 1
    api = reader('PUBLISHED')
    result = resolve(store, api, at + RESOLVE_AFTER, apply=True)
    assert result['actions'] == {'marked_published': 1} and result['meta_writes'] == 0
    first = result['claims'][0]
    assert (first['post_id'], first['container_state'], first['format'], first['container_id']) == (key, 'PUBLISHED', 'feed', '1850')
    stored = row(store, key)
    assert stored['status'] == 'published' and stored['media_id'] is None and stored['container_id'] == '1850'
    assert json.loads(stored['payload'])['resolution'] == 'container_published'
    assert summary(store, at + RESOLVE_AFTER)['unresolved']['instagram'] == 0
    only_status_reads(api, ['1850'])
    validate_state(store.path)


@pytest.mark.parametrize('state,code', [('EXPIRED', 'container_expired'), ('ERROR', 'container_error'),
                                        ('FINISHED', 'container_finished')])
def test_unused_container_becomes_terminal_not_published(store, event, at, state, code):
    key = claim(store, event, at, status='uncertain', delivery_error='timeout')
    later = at + timedelta(days=3)
    api = reader(state)
    assert resolve(store, api, later, apply=True)['actions'] == {'marked_not_published': 1}
    stored = row(store, key)
    assert stored['status'] == NOT_PUBLISHED and json.loads(stored['payload'])['resolution'] == code
    validate_state(store.path)
    # Off the unresolved alarm, the not-sent tally and the claim's own day.
    for when in (at, later):
        result = summary(store, when)
        assert result['unresolved']['instagram'] == 0 and result['not_sent']['instagram'] == 0
        assert result['today']['instagram_feed'] == 0 and result['delivery_errors'] == {}
    assert day_claims(store, at) == []
    # A second run finds nothing open and reads nothing.
    assert resolve(store, api, later, apply=True)['claims'] == []
    assert api.call.call_count == 1


def test_not_published_claim_is_never_queued_or_published_again(store, event, at):
    key = claim(store, event, at)
    resolve(store, reader('EXPIRED'), at + RESOLVE_AFTER, apply=True)
    post = next(p for p in store.posts() if p['id'] == key)
    assert store.queue({**post, 'status': 'prepared'}) is False
    for hours in (49, 72, 200):
        prepare(store, at + timedelta(hours=hours))
        prepare_story_jobs(store, {key: {'feed': ['media/' + key + '/feed-1.jpg'], 'story': ['media/' + key + '/story-1.jpg']}})
    assert row(store, key)['status'] == NOT_PUBLISHED
    api = reader()
    api.call.return_value = {'id': 'media-2'}
    for target in (None, key):
        publish_one(store, at + timedelta(hours=49), 'https://example.org/', {key: {'feed': ['media/x/feed-1.jpg']}},
                    adapter=api, target_id=target, requested=target is not None)
    api.container.assert_not_called()
    assert row(store, key)['status'] == NOT_PUBLISHED


def test_in_progress_container_is_left_untouched(store, event, at):
    key = claim(store, event, at)
    before = store.rows('SELECT * FROM posts')
    result = resolve(store, reader('IN_PROGRESS'), at + timedelta(days=5), apply=True)
    assert result['actions'] == {'skipped_in_progress': 1}
    assert store.rows('SELECT * FROM posts') == before and row(store, key)['status'] == 'publishing'


def test_claim_without_container_is_reported_and_not_read(store, event, at):
    key = claim(store, event, at, status='uncertain', container=None, delivery_error='connection')
    api = reader('EXPIRED')
    result = resolve(store, api, at + timedelta(days=5), apply=True)
    assert result['claims'] == [{'post_id': key, 'action': 'skipped_no_container', 'format': 'feed', 'status': 'uncertain',
                                 'published_at': at.isoformat(), 'container_id': None, 'delivery_error': 'connection'}]
    api.call.assert_not_called()
    assert row(store, key)['status'] == 'uncertain'


def test_unreadable_status_and_recent_claims_stay_open(store, event, at):
    key = claim(store, event, at)
    api = reader(failure=RuntimeError('Meta API request failed (HTTP 400)'))
    result = resolve(store, api, at + timedelta(days=5), apply=True)
    assert result['claims'][0]['action'] == 'skipped_unreadable' and result['claims'][0]['read_error'] == 'http_400'
    assert row(store, key)['status'] == 'publishing'
    # A day-old claim may still compete for its slot or the delivery audit.
    result = resolve(store, reader('EXPIRED'), at + RESOLVE_AFTER - timedelta(minutes=1), apply=True)
    assert result['actions'] == {'skipped_too_recent': 1} and row(store, key)['status'] == 'publishing'


@pytest.mark.parametrize('state,action', [('PUBLISHED', 'would_mark_published'), ('EXPIRED', 'would_mark_not_published')])
def test_dry_run_reports_and_writes_nothing(store, event, at, state, action):
    claim(store, event, at)
    before = store.rows('SELECT * FROM posts')
    result = resolve(store, reader(state), at + timedelta(days=5))
    assert result['mode'] == 'dry_run' and result['actions'] == {action: 1}
    assert store.rows('SELECT * FROM posts') == before


def test_single_post_id_limits_the_run(store, event, at):
    first = claim(store, event, at)
    other = next(p for p in store.posts() if p['status'] == 'prepared' and p['id'] != first)
    with store.db:
        store.db.execute("UPDATE posts SET status='uncertain',container_id='1900' WHERE id=?", (other['id'],))
    api = reader('EXPIRED')
    result = resolve(store, api, at + timedelta(days=5), apply=True, post_id=first)
    assert [r['post_id'] for r in result['claims']] == [first]
    only_status_reads(api, ['1850'])
    assert row(store, other['id'])['status'] == 'uncertain'
    assert resolve(store, api, at, post_id='f' * 24)['claims'] == [{'post_id': 'f' * 24, 'action': 'not_found'}]
    assert resolve(store, api, at, post_id=first)['claims'][0]['action'] == 'skipped_not_open'
    with pytest.raises(ValueError):
        resolve(store, api, at, post_id='../x')


def test_real_adapter_makes_only_a_status_get(store, event, at, monkeypatch):
    monkeypatch.setenv('INSTAGRAM_ACCESS_TOKEN', 'test-token-value')
    monkeypatch.setenv('INSTAGRAM_AUTH_MODE', 'instagram_login')
    claim(store, event, at)
    session = Mock()
    session.request.return_value = SimpleNamespace(ok=True, status_code=200, json=lambda: {'status_code': 'EXPIRED'})
    resolve(store, Instagram(session), at + timedelta(days=5), apply=True)
    assert session.request.call_count == 1
    method, url = session.request.call_args.args
    assert method == 'GET' and url.endswith('/1850') and 'media_publish' not in url
    assert session.request.call_args.kwargs['params'] == {'fields': 'status_code'}
    assert session.request.call_args.kwargs['data'] is None
    session.post.assert_not_called()


def test_summary_carries_only_codes_identifiers_and_times(store, event, at, tmp_path):
    claim(store, event, at)
    result = resolve(store, reader('EXPIRED'), at + timedelta(days=5))
    target = tmp_path / 'summary.md'
    write_summary(result, target)
    text = target.read_text(encoding='utf-8')
    assert event['title'] not in text and 'caption' not in text
    dirty = safe_report({'mode': 'apply', 'actions': {'x': 1, 'marked_published': 1},
                         'claims': [{'post_id': 'a' * 24, 'action': 'marked_published', 'container_id': '12&access_token=x',
                                     'container_state': 'Meta said <b>', 'read_error': 'Bearer abc def', 'published_at': 'soon'}]})
    assert dirty['actions'] == {'marked_published': 1}
    assert dirty['claims'][0] == {'post_id': 'a' * 24, 'action': 'marked_published', 'container_id': 'invalid',
                                  'container_state': 'invalid', 'read_error': 'invalid', 'published_at': 'invalid'}


def test_state_refuses_an_unknown_resolution(store, event, at):
    key = claim(store, event, at)
    payload = json.loads(row(store, key)['payload'])
    with store.db:
        store.db.execute('UPDATE posts SET payload=? WHERE id=?', (json.dumps({**payload, 'resolution': 'owner_says_so'}), key))
    with pytest.raises(ValueError, match='resolution'):
        validate_state(store.path)


def test_workflow_is_manual_report_first_and_shares_the_production_lock_to_write():
    flow = yaml.safe_load((ROOT / '.github/workflows/resolve-uncertain.yml').read_text(encoding='utf-8'))
    events = flow[True]
    assert set(events) == {'workflow_dispatch'}
    inputs = events['workflow_dispatch']['inputs']
    assert inputs['dry_run']['type'] == 'boolean' and inputs['dry_run']['default'] is True
    assert inputs['post_id']['default'] == ''
    assert flow['permissions'] == {'contents': 'read'}
    job = flow['jobs']['resolve']
    assert "github.ref == 'refs/heads/main'" in job['if']
    assert 'isparta-production' in job['concurrency']['group'] and job['concurrency']['cancel-in-progress'] is False
    run = next(s for s in job['steps'] if 'isparta.production' in s.get('run', ''))
    assert 'resolve-uncertain' in run['run'] and ' publish' not in run['run']
    assert run['env']['INSTAGRAM_PUBLISH_ENABLED'] == 'false' and run['env']['FACEBOOK_PUBLISH_ENABLED'] == 'false'
    assert '${{ inputs.post_id }}' == run['env']['POST_ID'] and '${{' not in run['run']
    persist = next(s for s in job['steps'] if 'state_git persist' in s.get('run', ''))
    assert 'inputs.dry_run == false' in persist['if'] and 'STATE_WRITE_TOKEN' in persist['env']
    assert 'STATE_WRITE_TOKEN' not in json.dumps(run)
