"""Weather production boundaries: isolated preview, shared state and existing identity."""
from contextlib import closing
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest
import yaml

from news_engine.domain import TZ
from news_engine.security import validate_state
from news_engine.store import Store

ROOT = Path(__file__).resolve().parents[1]
AT = datetime(2026, 10, 25, 7, 30, tzinfo=TZ)


def test_weather_workflow_keeps_manual_preview_separate_from_production():
    flow = yaml.safe_load((ROOT/'.github/workflows/weather-story.yml').read_text(encoding='utf-8'))
    events = flow.get('on', flow.get(True))
    assert [r['cron'] for r in events['schedule']] == ['35 4 * * *', '0,17,32,47 5 * * *']
    assert events['workflow_run']['workflows'] == ['Research and prepare Isparta content']
    assert flow['permissions'] == {'contents':'read'}
    assert flow['concurrency']['cancel-in-progress'] is False
    assert 'isparta-production' in flow['concurrency']['group']
    preview = flow['jobs']['preview']
    encoded = json.dumps(preview)
    assert "github.event_name == 'workflow_dispatch'" in preview['if']
    assert 'secrets.' not in encoded and 'STATE_WRITE_TOKEN' not in encoded
    assert 'state_git' not in encoded and 'isparta.production' not in encoded
    assert 'news_engine.weather --preview' in encoded
    live = flow['jobs']['weather']
    condition = live['if']
    assert "github.event_name == 'schedule'" in condition
    assert "head_repository.full_name == github.repository" in condition
    assert "head_branch == 'main'" in condition
    assert "conclusion == 'success'" in condition
    assert "'T04:'" in condition and "'T05:'" in condition
    assert "vars.INSTAGRAM_PUBLISH_ENABLED == 'true'" in condition
    assert "vars.META_TESTS_COMPLETED == 'true'" in condition
    assert live['environment'] == 'instagram-production'
    assert live['permissions'] == {'contents':'write'}
    assert 'isparta.production weather --wait-for-target' in json.dumps(live)
    assert live['steps'][-1]['if'] == "always() && steps.restore.outcome == 'success'"
    assert live['steps'][-1]['run'] == 'python -m news_engine.state_git persist'
    assert 'FACEBOOK' not in json.dumps(live)


def test_weather_is_enabled_but_existing_daily_news_and_pharmacy_limits_stay_independent():
    runtime = json.loads((ROOT/'config/runtime.json').read_text(encoding='utf-8'))
    assert runtime['weather_enabled'] is True
    assert runtime['daily_news_feed_limit'] == 3
    assert runtime['daily_news_story_limit'] == 3
    assert runtime['pharmacy_stories_enabled'] is True
    assert runtime['facebook_enabled'] is False
    research = yaml.safe_load((ROOT/'.github/workflows/research.yml').read_text(encoding='utf-8'))
    assert 'INSTAGRAM_ACCESS_TOKEN' not in json.dumps(research['jobs']['research'])
    assert research['concurrency']['group'] == 'isparta-production'


@pytest.mark.parametrize('result,exit_code', [
    ({'status':'published'}, None), ({'status':'already_published'}, None),
    ({'status':'outside_window'}, None), ({'status':'uncertain'}, 1),
    ({'status':'forecast_stale'}, 1),
])
def test_weather_entry_uses_same_durable_credential_and_restores_environment(tmp_path, monkeypatch, capsys, result, exit_code):
    from isparta import production
    from news_engine import weather, delivery_audit
    from news_engine.weather_data import SITE
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['production', 'weather', '--wait-for-target'])
    monkeypatch.setenv('INSTAGRAM_ACCESS_TOKEN', 'unit-original')
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(tmp_path/'summary.md'))
    checked = []
    def resolve(store, **kwargs):
        assert kwargs['maintain'] is True
        kwargs['checkpoint']()
        return 'unit-current-hidden', {'last_result':'waiting_minimum_age'}
    monkeypatch.setattr(production, 'resolve', resolve)
    monkeypatch.setattr(production, 'persist', lambda path: checked.append(str(path)))
    def run(store, site, **kwargs):
        assert site == SITE == 'https://ispartaofficial.github.io/ispartaofficial-news'
        assert kwargs['wait_for_target'] is True
        assert os.environ['INSTAGRAM_ACCESS_TOKEN'] == 'unit-current-hidden'
        kwargs['checkpoint']()
        return result
    monkeypatch.setattr(weather, 'run_weather', run)
    monkeypatch.setattr(delivery_audit, 'refresh', Mock(return_value={'results':{}}))
    if exit_code:
        with pytest.raises(SystemExit) as error: production.main()
        assert error.value.code == exit_code
    else:
        production.main()
    assert os.environ['INSTAGRAM_ACCESS_TOKEN'] == 'unit-original'
    assert checked == ['state/platform.sqlite', 'state/platform.sqlite'] or checked == [r'state\platform.sqlite', r'state\platform.sqlite']
    public_output = capsys.readouterr().out + (tmp_path/'summary.md').read_text(encoding='utf-8')
    assert 'unit-current-hidden' not in public_output and 'unit-original' not in public_output
    with closing(Store(tmp_path/'state/platform.sqlite')) as store:
        assert store.rows('SELECT * FROM posts') == []
        assert store.rows('SELECT * FROM pharmacy_stories') == []
        assert store.rows('SELECT * FROM facebook_deliveries') == []


def test_weather_state_refuses_extra_columns_and_unvalidated_forecast(tmp_path):
    path = tmp_path/'state.sqlite'
    with closing(Store(path)) as store:
        with store.db:
            store.db.execute('INSERT INTO weather_stories(day,forecast,status,checked_at,last_result) VALUES(?,?,?,?,?)',
                             ('2026-10-25', '{"place":"Seferihisar"}', 'prepared', AT.isoformat(), 'prepared'))
        with pytest.raises(ValueError): validate_state(path)
        with store.db:
            store.db.execute('DELETE FROM weather_stories')
            store.db.execute('ALTER TABLE weather_stories ADD COLUMN unexpected TEXT')
        with pytest.raises(ValueError, match='Unexpected weather story fields'): validate_state(path)


def test_export_uses_weather_manifest_without_fetching_or_mutating_claims(tmp_path, monkeypatch):
    from news_engine import pipeline, weather
    monkeypatch.setenv('ILLUSTRATIONS_ENABLED', 'false')
    monkeypatch.setenv('SOURCE_PHOTOS_ENABLED', 'false')
    exporter = Mock(return_value=None)
    monkeypatch.setattr(weather, 'export_weather', exporter)
    with closing(Store(tmp_path/'state.sqlite')) as store:
        before = {table:store.rows('SELECT * FROM '+table) for table in ('posts','weather_stories','pharmacy_stories')}
        pipeline.export(store, tmp_path/'public', [], AT)
        assert {table:store.rows('SELECT * FROM '+table) for table in before} == before
    exporter.assert_called_once()
    manifest = json.loads((tmp_path/'public/data.json').read_text(encoding='utf-8'))
    assert manifest['weather_story'] is None


def test_weather_state_accepts_only_reviewed_isparta_forecast_identity(tmp_path):
    from news_engine.weather_data import SOURCE
    value = {'date':'2026-10-25', 'place':'Isparta', 'condition':'Parçalı bulutlu',
             'low':6, 'high':17, 'period_start':'2026-10-25T06:00:00+03:00',
             'period_end':'2026-10-26T06:00:00+03:00', 'fetched_at':AT.isoformat(),
             'source_url':SOURCE, 'display_version':'weather-copy-v1', 'brand_version':'isparta-rose-v1'}
    path = tmp_path/'state.sqlite'
    with closing(Store(path)) as store:
        with store.db:
            store.db.execute('INSERT INTO weather_stories(day,forecast,status,checked_at,last_result) VALUES(?,?,?,?,?)',
                             (value['date'], json.dumps(value,ensure_ascii=False), 'prepared', AT.isoformat(), 'prepared'))
        validate_state(path)
        for bad in (dict(value, place='Seferihisar'), dict(value, source_url='https://www.mgm.gov.tr/tahmin/gunluk-tahmin.aspx?b=3'),
                    dict(value, unreviewed='extra')):
            with store.db: store.db.execute('UPDATE weather_stories SET forecast=?', (json.dumps(bad,ensure_ascii=False),))
            with pytest.raises(ValueError): validate_state(path)
