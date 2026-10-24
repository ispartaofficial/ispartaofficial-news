from datetime import datetime, timedelta
from io import BytesIO
import hashlib
import json
from pathlib import Path

from PIL import Image
import pytest
import requests

from news_engine import weather as w
from news_engine.domain import TZ
from news_engine.store import Store
from news_engine.weather_copy import display_condition
from news_engine.weather_data import SOURCE, SITE, asset_id, fresh, validate_forecast, validate_record

AT = datetime(2026, 10, 24, 8, 0, tzinfo=TZ)
HTML = (Path(__file__).parent/'fixtures/mgm-isparta-20261024.html').read_text(encoding='utf-8')


def forecast():
    return w.parse_forecast(HTML, AT-timedelta(minutes=30))


class Response:
    def __init__(self, data=None, content=b'', content_type='application/json'):
        self.status_code = 200
        self.data, self.content = data, content
        self.headers = {'Content-Type': content_type}

    def json(self):
        return self.data


class API:
    account = w.ACCOUNT
    auth_mode = 'instagram_login'
    base = 'https://graph.instagram.com/v26.0'

    def __init__(self, value=None, *, wrong_hash=False, wrong_image=False):
        self.value = value or forecast()
        data = BytesIO()
        Image.new('RGB', (100, 100) if wrong_image else (1080, 1920), 'white').save(data, format='JPEG')
        raw = data.getvalue()
        self.path = f'media/{asset_id(self.value)}/story-1.jpg'
        self.manifest = dict(demo=False, brand={'version': 'isparta-rose-v1'}, weather_story={
            'forecast': self.value, 'status': 'prepared', 'display_condition': display_condition(self.value),
            'asset': self.path, 'asset_id': asset_id(self.value),
            'sha256': {self.path: '0'*64 if wrong_hash else hashlib.sha256(raw).hexdigest()}})
        self.responses = {SITE+'/data.json': Response(self.manifest),
                          SITE+'/'+self.path: Response(content=raw, content_type='image/jpeg')}
        self.session = self
        self.reads, self.mutations = [], []
        self.fail = False

    def get(self, url, **kwargs):
        assert kwargs['allow_redirects'] is False
        self.reads.append(url)
        return self.responses[url]

    def enabled(self):
        return True

    def call(self, path, method=None, **kwargs):
        if path == 'me':
            assert method == 'GET'
            return {'user_id': self.account, 'username': 'ispartaofficial', 'account_type': 'BUSINESS'}
        self.mutations.append(('publish', path, kwargs))
        return {'id': '222'}

    def container(self, urls, caption, story):
        self.mutations.append(('container', urls, caption, story))
        if self.fail:
            raise requests.Timeout()
        return '111'

    def wait(self, container):
        assert container == '111'


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(w, '_profile_enabled', lambda: True)
    store = Store(tmp_path/'state.sqlite')
    value = forecast()
    with store.db:
        store.db.execute('INSERT INTO weather_stories(day,forecast,status,checked_at,last_result) VALUES(?,?,?,?,?)',
                         (value['date'], json.dumps(value), 'prepared', value['fetched_at'], 'prepared'))
    yield store
    store.close()


def test_real_official_antalya_fixture_isparta_not_guessed_region_or_temperature():
    value = forecast()
    assert SOURCE.endswith('?b=2')
    assert value['place'] == 'Isparta' and value['high'] == 24 and value['low'] is None
    assert value['condition'] == 'Parçalı az bulutlu'
    assert value['period_start'] == '2026-10-24T06:00:00+03:00'


def test_ambiguous_or_missing_district_refused():
    for html in (HTML.replace('Isparta', 'Antalya'), HTML.replace('</table>', '<tr><td>Isparta</td><td>Açık</td><td>3</td><td>20</td></tr></table>')):
        with pytest.raises(w.ForecastError, match='district'):
            w.parse_forecast(html, AT)


@pytest.mark.parametrize('html', [HTML.replace('Başlangıç', 'Başlama'), HTML.replace('Bitiş', 'Sona erme')])
def test_explicit_bulletin_period_required(html):
    with pytest.raises(w.ForecastError, match='period'):
        w.parse_forecast(html, AT)


def test_future_day_does_not_reuse_today_bulletin():
    with pytest.raises(ValueError, match='cover'):
        w.parse_forecast(HTML, AT+timedelta(days=1))


@pytest.mark.parametrize('changes', [dict(place='Seferihisar'), dict(source_url=SOURCE.replace('b=2', 'b=7')),
                                     dict(low=25, high=24), dict(low=None, high=None), dict(high=True),
                                     dict(brand_version='snail-s-v1'), dict(display_version='old')])
def test_forecast_contract_rejects_foreign_or_invalid_values(changes):
    with pytest.raises(ValueError):
        validate_forecast(dict(forecast(), **changes))


def test_90_minute_freshness_is_independent_of_source_period_and_day():
    value = forecast()
    assert fresh(value, AT)
    assert not fresh(value, AT+timedelta(minutes=61))
    assert not fresh(value, AT+timedelta(days=1))
    changed_check = dict(value, fetched_at=(AT-timedelta(minutes=10)).isoformat())
    assert asset_id(value) == asset_id(changed_check)


def test_refresh_failure_blocks_previous_prepared_forecast(prepared, monkeypatch):
    at = AT+timedelta(minutes=5)
    monkeypatch.setattr(w, 'now', lambda: at)
    class Fetcher:
        def get(self, url):
            assert url == SOURCE
            raise requests.Timeout()
    w.refresh_weather(prepared, at, Fetcher())
    row = prepared.rows('SELECT * FROM weather_stories')[0]
    assert row['status'] == 'blocked' and row['last_result'] == 'source_timeout'
    validate_record(row)
    assert w.publish_weather(prepared, at, SITE, API(), lambda: None)['status'] == 'source_timeout'


@pytest.mark.parametrize('at', [AT-timedelta(minutes=1), AT+timedelta(hours=1)])
def test_no_weather_post_outside_morning_hour(prepared, at):
    api = API()
    assert w.publish_weather(prepared, at, SITE, api, lambda: None) == {'status': 'outside_window'}
    assert not api.reads and not api.mutations


def test_checkpoint_is_required_before_any_meta_mutation(prepared):
    api = API()
    assert w.publish_weather(prepared, AT, SITE, api)['status'] == 'disabled'
    assert not api.reads and not api.mutations


@pytest.mark.parametrize('flag', ['wrong_hash', 'wrong_image'])
def test_actual_jpeg_hash_and_geometry_gate_publication(prepared, flag):
    api = API(**{flag: True})
    assert w.publish_weather(prepared, AT, SITE, api, lambda: None)['status'] == 'media_not_deployed'
    assert not api.mutations
    assert prepared.rows('SELECT status FROM weather_stories')[0]['status'] == 'prepared'


def test_manifest_must_match_the_exact_forecast_and_version(prepared):
    api = API()
    api.manifest['weather_story']['forecast'] = dict(api.value, high=25)
    assert w.publish_weather(prepared, AT, SITE, api, lambda: None)['status'] == 'media_not_deployed'
    assert not api.mutations


def test_foreign_account_stops_before_meta_mutations(prepared):
    api = API()
    api.account = '999'
    assert w.publish_weather(prepared, AT, SITE, api, lambda: None)['status'] == 'account_mismatch'
    assert not api.mutations


def test_one_daily_claim_is_durable_and_restarts_cannot_republish(prepared):
    api = API()
    statuses = []
    def checkpoint():
        row = prepared.rows('SELECT * FROM weather_stories')[0]
        validate_record(row)
        statuses.append((row['status'], row['container_id'], row['media_id'], len(api.mutations)))
    assert w.publish_weather(prepared, AT, SITE, api, checkpoint) == {'status': 'published'}
    assert statuses[0] == ('publishing', None, None, 0)
    assert statuses[-1][:3] == ('published', '111', '222')
    frozen = prepared.rows('SELECT * FROM weather_stories')
    mutations = list(api.mutations)
    assert w.publish_weather(prepared, AT+timedelta(minutes=10), SITE, api, checkpoint)['status'] == 'already_published'
    w.refresh_weather(prepared, AT+timedelta(minutes=10))
    assert prepared.rows('SELECT * FROM weather_stories') == frozen
    assert api.mutations == mutations
    assert prepared.rows('SELECT * FROM posts') == []
    assert prepared.rows('SELECT * FROM pharmacy_stories') == []


def test_uncertain_delivery_consumes_the_claim_without_retry(prepared):
    api = API()
    api.fail = True
    assert w.publish_weather(prepared, AT, SITE, api, lambda: None)['status'] == 'uncertain'
    mutations = list(api.mutations)
    assert w.publish_weather(prepared, AT+timedelta(minutes=5), SITE, api, lambda: None)['status'] == 'awaiting_resolution'
    assert api.mutations == mutations
    validate_record(prepared.rows('SELECT * FROM weather_stories')[0])


def test_failed_remote_checkpoint_never_calls_meta(prepared):
    api = API()
    def fail():
        raise RuntimeError('Remote state unavailable')
    with pytest.raises(RuntimeError, match='Remote state'):
        w.publish_weather(prepared, AT, SITE, api, fail)
    assert not api.mutations
    assert prepared.rows('SELECT status FROM weather_stories')[0]['status'] == 'publishing'


def test_early_ready_job_waits_boundedly_then_rechecks(prepared):
    api = API()
    clock = [AT-timedelta(minutes=25)]
    slept = []
    def sleep(seconds):
        slept.append(seconds)
        clock[0] += timedelta(seconds=seconds)
    assert w.run_weather(prepared, SITE, api, lambda: None, wait_for_target=True,
                         clock=lambda: clock[0], sleeper=sleep)['status'] == 'published'
    assert sum(slept) == 1500 and max(slept) <= 30
    assert api.reads.count(SITE+'/data.json') == 2


def test_export_preserves_frozen_previous_day_media(prepared, tmp_path):
    api = API()
    assert w.publish_weather(prepared, AT, SITE, api, lambda: None)['status'] == 'published'
    from news_engine.weather import export_weather
    output = tmp_path/'public'
    assert export_weather(prepared, output, AT+timedelta(days=1)) is None
    assert (output/api.path).is_file()
    with Image.open(output/api.path) as image:
        assert image.size == (1080, 1920) and image.format == 'JPEG'


def test_record_requires_identifiers_and_a_real_morning_claim(prepared):
    row = prepared.rows('SELECT * FROM weather_stories')[0]
    for changes in (dict(status='published'), dict(status='publishing', published_at=(AT+timedelta(hours=2)).isoformat()),
                    dict(container_id='not-meta-id')):
        with pytest.raises(ValueError):
            validate_record(dict(row, **changes))


def test_long_complete_condition_blocks_weather_without_aborting_other_exports(prepared, tmp_path, monkeypatch):
    # Legal source copy may still exceed the actual card's readable line budget.
    value = dict(forecast(), condition=('Kıyılarda yer yer kuvvetli sağanak yağmurlu ' * 5).strip())
    validate_forecast(value)
    with prepared.db:
        prepared.db.execute('UPDATE weather_stories SET forecast=?', (json.dumps(value),))
    before_posts = prepared.rows('SELECT * FROM posts')
    result = w.export_weather(prepared, tmp_path/'public', AT)
    assert result['status'] == 'blocked' and result['last_result'] == 'forecast_text_unreadable'
    assert 'asset' not in result
    assert prepared.rows('SELECT * FROM posts') == before_posts
    assert w.export_weather(prepared, tmp_path/'public', AT)['status'] == 'blocked'
    validate_record(prepared.rows('SELECT * FROM weather_stories')[0])


def test_unreadable_new_source_never_becomes_prepared(prepared, monkeypatch, tmp_path):
    value = dict(forecast(), condition=('Kıyılarda yer yer kuvvetli sağanak yağmurlu ' * 5).strip())
    at = AT+timedelta(minutes=5)
    monkeypatch.setattr(w, 'now', lambda: at)
    monkeypatch.setattr(w, 'fetch_forecast', lambda *args: value)
    w.refresh_weather(prepared, at)
    row = prepared.rows('SELECT * FROM weather_stories')[0]
    assert row['status'] == 'blocked' and row['last_result'] == 'forecast_text_unreadable'
    assert 'asset' not in w.export_weather(prepared, tmp_path/'public', at)


def test_frozen_claim_is_not_rewritten_to_repair_rendering(prepared, monkeypatch, tmp_path):
    api = API()
    assert w.publish_weather(prepared, AT, SITE, api, lambda: None)['status'] == 'published'
    frozen = prepared.rows('SELECT * FROM weather_stories')
    from news_engine import weather_render
    def cannot_render(*args, **kwargs):
        raise ValueError('No readable layout')
    monkeypatch.setattr(weather_render, 'render_weather', cannot_render)
    with pytest.raises(ValueError, match='readable'):
        w.export_weather(prepared, tmp_path/'public', AT)
    assert prepared.rows('SELECT * FROM weather_stories') == frozen
