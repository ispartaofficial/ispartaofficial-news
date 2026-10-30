import json
import zipfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from news_engine.backup_history import drill
from news_engine.domain import digest, parse_date
from news_engine.ops_watch import MARKER, evaluate, notify, workflow_problems
from news_engine.state_backup import create, restore_drill

ROOT = Path(__file__).resolve().parents[2]


def healthy(at):
    return {'demo': False, 'runs': [{'finished_at': at.isoformat()}],
            'source_health': [{'status': 'ok'}] * 10, 'publishing_enabled': True,
            'weather_story': {'day': at.date().isoformat(), 'status': 'published'},
            'pharmacy_story': {'day': at.date().isoformat(), 'status': 'published'},
            'operations': {'unresolved': {'instagram': 0, 'facebook': 0}}}


def claim(store, at):
    parent = {'id': digest('parent'), 'item_id': digest('item'), 'revision': 1, 'kind': 'news',
              'due_at': at.isoformat(), 'published_at': at.isoformat(), 'caption': 'Yerel haber\n\nKaynak: kurum', 'category': 'culture'}
    store.queue(parent)
    store.db.execute("UPDATE posts SET status='published',media_id='111' WHERE id=?", (parent['id'],))
    store.db.commit()


def test_empty_sources_are_not_failure_and_coverage_drop_is():
    at = parse_date('2026-10-30T12:00:00+03:00')
    v = healthy(at)
    v['source_health'] = [{'status': 'empty'}] * 10
    assert evaluate(v, at) == []
    v['source_health'] = [{'status': 'failed'}] * 4 + [{'status': 'ok'}] * 6
    assert evaluate(v, at) == ['source_coverage_drop']


def test_daytime_gap_alerts_after_three_hours_not_after_githubs_usual_skips():
    at = parse_date('2026-10-30T15:00:00+03:00')
    v = healthy(at)
    v['runs'][0]['finished_at'] = (at - timedelta(minutes=157)).isoformat()
    assert 'research_stale' not in evaluate(v, at)
    v['runs'][0]['finished_at'] = (at - timedelta(hours=3, minutes=1)).isoformat()
    assert 'research_stale' in evaluate(v, at)


def test_overnight_pause_is_quiet_but_missing_morning_runs_alert():
    last = parse_date('2026-10-29T23:50:00+03:00')
    v = healthy(last)
    assert 'research_stale' not in evaluate(v, parse_date('2026-10-30T07:30:00+03:00'))
    assert 'research_stale' not in evaluate(v, parse_date('2026-10-30T09:59:00+03:00'))
    assert 'research_stale' in evaluate(v, parse_date('2026-10-30T10:00:00+03:00'))


def test_daily_stories_are_judged_only_from_a_panel_built_after_the_window():
    # 30 Oct: the 08:01 panel predates the 08:08 weather story; it is not missing yet.
    early = parse_date('2026-10-30T08:01:00+03:00')
    v = healthy(early)
    v['weather_story'] = {'day': '2026-10-30', 'status': 'prepared'}
    v['pharmacy_story'] = None
    assert evaluate(v, parse_date('2026-10-30T09:30:00+03:00')) == []
    late = parse_date('2026-10-30T09:25:00+03:00')
    v['runs'][0]['finished_at'] = late.isoformat()
    assert evaluate(v, late) == ['weather_missing']
    v['weather_story']['status'] = 'published'
    evening = parse_date('2026-10-30T18:25:00+03:00')
    v['runs'][0]['finished_at'] = evening.isoformat()
    assert evaluate(v, evening) == ['pharmacy_missing']
    v['pharmacy_story'] = {'day': '2026-10-30', 'status': 'published'}
    assert evaluate(v, evening) == []


def test_invalid_or_demo_panel_is_reported_not_trusted():
    at = parse_date('2026-10-30T12:00:00+03:00')
    assert evaluate({'demo': True}, at) == ['invalid_panel']
    v = healthy(at)
    v['runs'][0]['finished_at'] = (at + timedelta(hours=1)).isoformat()
    assert evaluate(v, at) == ['invalid_panel']


def test_two_failed_research_runs_and_missing_backup_are_incidents():
    at = parse_date('2026-10-30T12:00:00+03:00')
    run = lambda conclusion, hours: {'head_branch': 'main', 'status': 'completed', 'conclusion': conclusion,
                                     'created_at': (at - timedelta(hours=hours)).isoformat()}
    api = Mock()
    api.call.side_effect = lambda method, path, **kw: (
        {'workflow_runs': [run('failure', 1), run('cancelled', 2), run('failure', 3)]} if 'research.yml' in path
        else {'workflow_runs': [run('success', 49)]})
    assert workflow_problems(api, at) == ['research_failed', 'backup_missing']
    api.call.side_effect = lambda method, path, **kw: (
        {'workflow_runs': [run('failure', 1), run('success', 2)]} if 'research.yml' in path
        else {'workflow_runs': [run('success', 20)]})
    assert workflow_problems(api, at) == []


def test_alert_is_assigned_to_the_isparta_owner_and_deduplicated(at):
    api = Mock()
    api.call.return_value = []
    assert notify(api, ['research_stale'], at) == 'opened'
    data = api.call.call_args.kwargs['json']
    assert data['assignees'] == ['ispartaofficial'] and MARKER in data['body']
    assert 'seferihisar' not in json.dumps(data).lower()
    previous = {'number': 42, 'body': data['body'], 'user': {'login': 'github-actions[bot]'}, 'state': 'open'}
    api.reset_mock()
    api.call.return_value = [previous]
    assert notify(api, ['research_stale'], at + timedelta(hours=1)) == 'unchanged'
    assert api.call.call_count == 1
    assert notify(api, [], at + timedelta(hours=1)) == 'resolved'
    assert api.call.call_args.args[1] == 'issues/42/comments'


def test_monitor_does_not_modify_user_issues_or_send_when_healthy(at):
    api = Mock()
    api.call.return_value = [{'number': 1, 'body': MARKER, 'user': {'login': 'someone'}, 'state': 'open'}]
    assert notify(api, [], at) == 'healthy_no_issue'
    assert api.call.call_count == 1
    with pytest.raises(ValueError):
        notify(api, ['PRIVATE_PROVIDER_TEXT'], at)


def test_backup_is_consistent_restorable_and_does_not_change_live_database(store, at, tmp_path):
    claim(store, at)
    before = store.path.read_bytes()
    archive = tmp_path / 'state.zip'
    result = create(store.path, archive, at, 'a' * 40)
    assert result['integrity'] == 'ok' and result['restored_in_isolation']
    assert result['production_modified'] is False and result['provider_independent'] is False
    assert store.path.read_bytes() == before
    assert restore_drill(archive) == result


def test_backup_rejects_changed_or_unexpected_archive_members(store, at, tmp_path):
    original = tmp_path / 'original.zip'
    create(store.path, original, at, 'a' * 40)
    with zipfile.ZipFile(original) as source:
        manifest = json.loads(source.read('manifest.json'))
        payload = source.read('platform.sqlite')
    changed = tmp_path / 'changed.zip'
    manifest['sha256'] = '0' * 64
    with zipfile.ZipFile(changed, 'w') as target:
        target.writestr('manifest.json', json.dumps(manifest))
        target.writestr('platform.sqlite', payload)
    with pytest.raises(ValueError, match='differs'):
        restore_drill(changed)
    with zipfile.ZipFile(changed, 'a') as target:
        target.writestr('../outside', 'x')
    with pytest.raises(ValueError, match='Unexpected'):
        restore_drill(changed)


def test_first_backup_does_not_fabricate_a_historical_restore(at):
    api = Mock()
    api.call.return_value = {'artifacts': []}
    session = Mock()
    assert drill(api, session, at, '1')['status'] == 'previous_day_backup_not_yet_available'
    session.get.assert_not_called()


def test_watch_and_backup_workflows_are_read_only_except_owner_issues():
    watch = yaml.safe_load((ROOT / '.github/workflows/operations-watch.yml').read_text(encoding='utf-8'))
    backup = yaml.safe_load((ROOT / '.github/workflows/state-backup.yml').read_text(encoding='utf-8'))
    assert watch['permissions'] == {'contents': 'read', 'actions': 'read', 'issues': 'write'}
    assert backup['permissions'] == {'contents': 'read', 'actions': 'read'}
    names = {yaml.safe_load(p.read_text(encoding='utf-8'))['name'] for p in (ROOT / '.github/workflows').glob('*.yml')}
    assert set(watch[True]['workflow_run']['workflows']) <= names
    for flow in (watch, backup):
        text = json.dumps(flow)
        assert 'secrets.' not in text and 'state_git persist' not in text and 'publish' not in text.lower()
        for job in flow['jobs'].values():
            assert all(s['with']['persist-credentials'] is False for s in job['steps'] if s.get('uses', '').startswith('actions/checkout@'))
