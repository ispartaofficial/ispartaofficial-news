"""MGM Isparta morning forecast and one independent daily Instagram story."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import re
import time

import requests

from .brand import VERSION as BRAND_VERSION
from .domain import TZ, now
from .weather_copy import VERSION as DISPLAY_VERSION, WeatherTextError, display_condition
from .weather_data import SOURCE, SITE, asset_id, fresh, validate_forecast

ACCOUNT = '17841403171726739'
REPOSITORY = 'ispartaofficial/ispartaofficial-news'


class ForecastError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def parse_forecast(html, at):
    from bs4 import BeautifulSoup
    at = at.astimezone(TZ)
    soup = BeautifulSoup(html, 'html.parser')
    periods = {}
    for label, key in (('Başlangıç', 'period_start'), ('Bitiş', 'period_end')):
        stamps = []
        for match in soup.find_all(string=lambda t: t and t.strip() == label):
            row = match.find_parent('tr')
            cells = row.find_all(['td', 'th'], recursive=False) if row else []
            if len(cells) >= 2:
                raw = cells[1].get_text(' ', strip=True)
                if stamp := re.fullmatch(r':?\s*(\d{2}\.\d{2}\.\d{4}-\d{2}:\d{2})', raw):
                    stamps.append(datetime.strptime(stamp[1], '%d.%m.%Y-%H:%M').replace(tzinfo=TZ))
        if len(stamps) != 1:
            raise ForecastError('forecast_period_missing')
        periods[key] = stamps[0].isoformat()
    rows = []
    for row in soup.select('tr'):
        cells = row.find_all(['th', 'td'], recursive=False)
        if len(cells) == 4 and cells[0].get_text(' ', strip=True) == 'Isparta':
            rows.append([c.get_text(' ', strip=True) for c in cells])
    if len(rows) != 1:
        raise ForecastError('forecast_district_missing')
    _, condition, low, high = rows[0]
    temperatures = []
    for raw in (low, high):
        if not raw:
            temperatures.append(None)
        elif re.fullmatch(r'-?\d{1,2}', raw):
            temperatures.append(int(raw))
        else:
            raise ForecastError('forecast_temperature_missing')
    if temperatures == [None, None]:
        raise ForecastError('forecast_temperature_missing')
    value = dict(date=at.date().isoformat(), place='Isparta', condition=condition,
                 low=temperatures[0], high=temperatures[1], **periods, fetched_at=at.isoformat(),
                 source_url=SOURCE, display_version=DISPLAY_VERSION, brand_version=BRAND_VERSION)
    validate_forecast(value)
    from .security import assert_no_secrets
    assert_no_secrets(value)
    return value


def fetch_forecast(at, fetcher=None):
    if fetcher is None:
        from .collect import Fetcher
        fetcher = Fetcher([{'url': SOURCE, 'enabled': True}])
    html, _ = fetcher.get(SOURCE)
    return parse_forecast(html, at)


def weather_error_code(exc):
    if isinstance(exc, WeatherTextError):
        return 'forecast_text_unreadable'
    if isinstance(exc, ForecastError):
        return exc.code
    if isinstance(exc, requests.exceptions.SSLError):
        return 'source_tls_failed'
    if isinstance(exc, requests.Timeout):
        return 'source_timeout'
    if isinstance(exc, requests.HTTPError):
        return 'source_http_error'
    if isinstance(exc, requests.ConnectionError):
        return 'source_connection_failed'
    if isinstance(exc, requests.RequestException):
        return 'source_unavailable'
    if isinstance(exc, ValueError) and str(exc) == 'robots.txt disallows this path':
        return 'source_robots_denied'
    return 'forecast_invalid'


def refresh_weather(store, at, fetcher=None):
    at = at.astimezone(TZ)
    if not 6 <= at.hour < 9:
        return
    day = at.date().isoformat()
    old = store.rows('SELECT * FROM weather_stories WHERE day=?', (day,))
    old = old[0] if old else None
    if old and old['status'] in ('publishing', 'published', 'uncertain'):
        return
    if (old and old['status'] == 'prepared' and old['forecast']
            and datetime.fromisoformat(old['checked_at']) > at-timedelta(minutes=15)):
        return
    try:
        value = fetch_forecast(now(), fetcher)
        if value['date'] != day:
            raise ValueError('Research crossed a local day boundary')
        from .weather_render import condition_layout
        try:
            condition_layout(value)
        except (ValueError, OSError):
            raise WeatherTextError('Complete forecast cannot fit safely') from None
        payload = json.dumps(value, ensure_ascii=False)
        status = result = 'prepared'
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        payload = old['forecast'] if old else None
        status, result = 'blocked', weather_error_code(exc)
    with store.db:
        store.db.execute('INSERT INTO weather_stories(day,forecast,status,checked_at,last_result) VALUES(?,?,?,?,?) '
                         'ON CONFLICT(day) DO UPDATE SET forecast=excluded.forecast,status=excluded.status,'
                         'checked_at=excluded.checked_at,last_result=excluded.last_result '
                         "WHERE weather_stories.status IN ('prepared','blocked')",
                         (day, payload, status, now().isoformat(), result))


def export_weather(store, public_dir, at):
    today = at.astimezone(TZ).date().isoformat()
    current = None
    # Previously published URLs remain available after the local day changes.
    rows = store.rows("SELECT * FROM weather_stories WHERE day=? OR status IN ('publishing','published','uncertain') ORDER BY day", (today,))
    for row in rows:
        result = {k: row[k] for k in ('day', 'status', 'last_result', 'checked_at', 'published_at')}
        result.update(target_time='08:00', timezone='Europe/Istanbul')
        if row['forecast']:
            forecast = validate_forecast(json.loads(row['forecast']))
            result.update(forecast=forecast, display_condition=display_condition(forecast))
            if row['status'] != 'blocked':
                from .weather_render import render_weather
                try:
                    path = render_weather(forecast, public_dir)
                    expected = f'media/{asset_id(forecast)}/story-1.jpg'
                    if path != expected:
                        raise ValueError('Unexpected weather renderer path')
                    result.update(asset=path, asset_id=asset_id(forecast),
                                  sha256={path: hashlib.sha256((Path(public_dir)/path).read_bytes()).hexdigest()})
                except (ValueError, OSError):
                    if row['status'] != 'prepared':
                        raise  # Never rewrite a frozen claim to repair its card.
                    with store.db:
                        store.db.execute("UPDATE weather_stories SET status='blocked',last_result='forecast_text_unreadable' WHERE day=? AND status='prepared'", (row['day'],))
                    result.update(status='blocked', last_result='forecast_text_unreadable')
        if row['day'] == today:
            current = result
    return current


def _profile_enabled():
    settings = json.loads((Path(__file__).resolve().parents[1]/'config/runtime.json').read_text(encoding='utf-8'))
    return (settings.get('repository') == REPOSITORY and settings.get('publishing_enabled') is True
            and settings.get('meta_connected') is True and settings.get('weather_enabled') is True
            and settings.get('instagram_auth_mode') == os.getenv('INSTAGRAM_AUTH_MODE') == 'instagram_login')


def account_matches(api):
    if (api.account != ACCOUNT or getattr(api, 'auth_mode', None) != 'instagram_login'
            or not re.fullmatch(r'https://graph\.instagram\.com/v\d+\.0', api.base)):
        return False
    from .meta_identity import identity_problem
    return identity_problem(api.call('me', 'GET', fields='user_id,username,account_type'),
                            'instagram_login', ACCOUNT, 'ispartaofficial') is None


@dataclass(frozen=True)
class ReadyWeather:
    day: str
    forecast_json: str
    url: str


def _weather_readiness(store, at, site_url, api):
    if not _profile_enabled() or not api.enabled():
        return {'status': 'disabled'}
    if (api.account != ACCOUNT or getattr(api, 'auth_mode', None) != 'instagram_login'
            or not re.fullmatch(r'https://graph\.instagram\.com/v\d+\.0', api.base)):
        return {'status': 'account_mismatch'}
    if site_url.rstrip('/') != SITE:
        raise ValueError('Unexpected Isparta weather media site')
    day = at.astimezone(TZ).date().isoformat()
    rows = store.rows('SELECT * FROM weather_stories WHERE day=?', (day,))
    if not rows:
        return {'status': 'not_ready'}
    row = rows[0]
    if row['status'] == 'published':
        return {'status': 'already_published'}
    if row['status'] in ('publishing', 'uncertain'):
        return {'status': 'awaiting_resolution'}
    if row['status'] != 'prepared' or not row['forecast']:
        return {'status': row['last_result'] if row['status'] == 'blocked' else 'source_unavailable'}
    forecast = json.loads(row['forecast'])
    if not fresh(forecast, at):
        return {'status': 'forecast_stale'}
    try:
        response = api.session.get(SITE+'/data.json', timeout=(8, 20), allow_redirects=False)
        if response.status_code != 200 or len(response.content) > 8_000_000:
            return {'status': 'media_not_deployed'}
        snapshot = response.json()
        deployed = snapshot.get('weather_story') or {}
        expected = f'media/{asset_id(forecast)}/story-1.jpg'
        hashes = deployed.get('sha256', {})
        if (snapshot.get('demo') is not False or snapshot.get('brand', {}).get('version') != BRAND_VERSION
                or deployed.get('status') != 'prepared' or deployed.get('forecast') != forecast
                or deployed.get('display_condition') != display_condition(forecast)
                or deployed.get('asset') != expected or deployed.get('asset_id') != asset_id(forecast)
                or set(hashes) != {expected} or not re.fullmatch(r'[a-f0-9]{64}', hashes[expected])):
            return {'status': 'media_not_deployed'}
        image = api.session.get(SITE+'/'+expected, timeout=(8, 20), allow_redirects=False)
        if (image.status_code != 200 or not image.headers.get('Content-Type', '').startswith('image/jpeg')
                or len(image.content) > 6_000_000 or hashlib.sha256(image.content).hexdigest() != hashes[expected]):
            return {'status': 'media_not_deployed'}
        from PIL import Image
        with Image.open(BytesIO(image.content)) as jpeg:
            if jpeg.size != (1080, 1920) or jpeg.format != 'JPEG':
                return {'status': 'media_not_deployed'}
            jpeg.verify()
    except (requests.RequestException, ValueError, KeyError, TypeError, OSError):
        return {'status': 'media_not_deployed'}
    return ReadyWeather(day, row['forecast'], SITE+'/'+expected)


def publish_weather(store, at, site_url, adapter=None, checkpoint=None):
    at = at.astimezone(TZ)
    if at.hour != 8:
        return {'status': 'outside_window'}
    if checkpoint is None:
        return {'status': 'disabled'}
    from .instagram import Instagram
    api = adapter or Instagram()
    ready = _weather_readiness(store, at, site_url, api)
    if not isinstance(ready, ReadyWeather):
        return ready
    try:
        if not account_matches(api):
            return {'status': 'account_mismatch'}
    except (requests.RequestException, RuntimeError, ValueError, TypeError, KeyError):
        return {'status': 'account_mismatch'}
    with store.db:
        changed = store.db.execute("UPDATE weather_stories SET status='publishing',published_at=?,last_result='awaiting_resolution' "
                                   "WHERE day=? AND status='prepared' AND forecast=?",
                                   (at.isoformat(), ready.day, ready.forecast_json))
    if changed.rowcount != 1:
        return {'status': 'awaiting_resolution'}
    checkpoint()  # Required remote claim before the first Meta mutation.
    try:
        container = api.container([ready.url], '', True)
        if not isinstance(container, str) or not re.fullmatch(r'\d{1,32}', container):
            raise ValueError('Invalid weather container identity')
        with store.db:
            store.db.execute('UPDATE weather_stories SET container_id=? WHERE day=?', (container, ready.day))
        checkpoint()
        api.wait(container)
        media = api.call(f'{api.account}/media_publish', creation_id=container)['id']
        if not isinstance(media, str) or not re.fullmatch(r'\d{1,32}', media):
            raise ValueError('Invalid weather media identity')
        with store.db:
            store.db.execute("UPDATE weather_stories SET status='published',media_id=?,last_result='published' WHERE day=?", (media, ready.day))
        checkpoint()
        return {'status': 'published'}
    except (requests.RequestException, RuntimeError, KeyError, ValueError, TypeError):
        with store.db:
            store.db.execute("UPDATE weather_stories SET status='uncertain',last_result='uncertain' WHERE day=?", (ready.day,))
        checkpoint()
        return {'status': 'uncertain'}


def run_weather(store, site_url, adapter=None, checkpoint=None, *, wait_for_target=False,
                wait_for_morning=False, clock=None, sleeper=None):
    clock, sleeper = clock or now, sleeper or time.sleep
    at = clock().astimezone(TZ)
    target = at.replace(hour=8, minute=0, second=0, microsecond=0)
    start = target-timedelta(minutes=25)
    if not (wait_for_target or wait_for_morning) or not start <= at < target:
        return publish_weather(store, at, site_url, adapter, checkpoint)
    if checkpoint is None:
        return {'status': 'disabled'}
    from .instagram import Instagram
    api = adapter or Instagram()
    ready = _weather_readiness(store, target, site_url, api)
    if not isinstance(ready, ReadyWeather):
        return ready
    remaining = 25*60
    while at < target:
        if at.date() != target.date() or at < start or remaining <= 0:
            return {'status': 'outside_window'}
        seconds = min(30, (target-at).total_seconds(), remaining)
        sleeper(seconds)
        remaining -= seconds
        at = clock().astimezone(TZ)
    return publish_weather(store, at, site_url, api, checkpoint)


def record_result(store, day, result):
    if result['status'] == 'outside_window':
        return
    with store.db:
        store.db.execute("UPDATE weather_stories SET last_result=? WHERE day=? AND status IN ('prepared','blocked')", (result['status'], day))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    if not args.preview:
        parser.error('Use the authorized isparta.production weather entrypoint')
    # Preview never opens durable state, reads a social credential, or contacts Meta.
    value = fetch_forecast(now())
    from .weather_render import render_weather
    output = Path('work/weather-preview')
    output.mkdir(parents=True, exist_ok=True)
    path = render_weather(value, output, preview=True)
    result = dict(preview_only=True, publication_attempted=False, forecast=value,
                  display_condition=display_condition(value), asset=path,
                  sha256={path: hashlib.sha256((output/path).read_bytes()).hexdigest()})
    (output/'data.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'date': value['date'], 'place': value['place'], 'condition': display_condition(value),
                      'low': value['low'], 'high': value['high'], 'source': SOURCE,
                      'preview_only': True, 'publication_attempted': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
