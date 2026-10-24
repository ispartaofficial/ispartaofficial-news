"""Isparta's public date-bound morning forecast contract; standard library only."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
import json
import re

from .brand import VERSION as BRAND_VERSION
from .domain import TZ, digest
from .weather_copy import VERSION as DISPLAY_VERSION

# Verified via MGM's own Antalya navigation link. b=7 is Kayseri, not Antalya.
SOURCE = 'https://www.mgm.gov.tr/tahmin/gunluk-tahmin.aspx?b=2'
SITE = 'https://ispartaofficial.github.io/ispartaofficial-news'
VERSION = 'isparta-weather-v1'
FIELDS = {'date', 'place', 'condition', 'low', 'high', 'period_start', 'period_end',
          'fetched_at', 'source_url', 'display_version', 'brand_version'}
STATES = {'prepared', 'blocked', 'publishing', 'published', 'uncertain'}
RESULTS = {'prepared', 'published', 'already_published', 'outside_window', 'disabled',
           'source_unavailable', 'forecast_invalid', 'forecast_stale', 'not_ready',
           'media_not_deployed', 'awaiting_resolution', 'uncertain', 'account_mismatch',
           'forecast_temperature_missing', 'forecast_district_missing', 'forecast_period_missing',
           'source_timeout', 'source_tls_failed', 'source_http_error', 'source_connection_failed',
           'source_robots_denied', 'forecast_text_unreadable'}


def validate_forecast(value):
    if (not isinstance(value, dict) or set(value) != FIELDS
            or value['display_version'] != DISPLAY_VERSION or value['brand_version'] != BRAND_VERSION
            or value['place'] != 'Isparta' or value['source_url'] != SOURCE):
        raise ValueError('Invalid Isparta forecast identity')
    day = date.fromisoformat(value['date'])
    if day.isoformat() != value['date']:
        raise ValueError('Invalid forecast date')
    condition = value['condition']
    if (not isinstance(condition, str) or not 2 <= len(condition) <= 240
            or not re.fullmatch(r'[\w\s,;:.()°/–%-]+', condition)):
        raise ValueError('Invalid forecast description')
    temperatures = [value[k] for k in ('low', 'high') if value[k] is not None]
    if (not temperatures or any(type(v) is not int or not -40 <= v <= 60 for v in temperatures)
            or len(temperatures) == 2 and value['low'] > value['high']):
        raise ValueError('Invalid forecast temperature')
    stamps = [datetime.fromisoformat(value[k]) for k in ('period_start', 'period_end', 'fetched_at')]
    if any(s.tzinfo is None for s in stamps):
        raise ValueError('Forecast timezone missing')
    start, end, fetched = [s.astimezone(TZ) for s in stamps]
    morning = datetime.combine(day, time(8), TZ)
    if not start <= morning < end or not timedelta(hours=12) <= end-start <= timedelta(hours=30):
        raise ValueError('Forecast does not cover this morning')
    if fetched.date() != day or not start-timedelta(hours=6) <= fetched < end:
        raise ValueError('Forecast retrieval outside validity')
    from .weather_copy import display_condition
    display_condition(value)
    return value


def asset_id(forecast):
    validate_forecast(forecast)
    # Checking an unchanged prediction again must not rewrite a published URL.
    values = {k: v for k, v in forecast.items() if k != 'fetched_at'}
    return digest(VERSION + ':' + json.dumps(values, ensure_ascii=False, sort_keys=True))


def fresh(forecast, at):
    try:
        validate_forecast(forecast)
        if at.tzinfo is None:
            return False
        at = at.astimezone(TZ)
        fetched = datetime.fromisoformat(forecast['fetched_at']).astimezone(TZ)
        return (forecast['date'] == at.date().isoformat()
                and datetime.fromisoformat(forecast['period_start']) <= at < datetime.fromisoformat(forecast['period_end'])
                and at-timedelta(minutes=90) <= fetched <= at+timedelta(minutes=5))
    except (ValueError, TypeError, KeyError):
        return False


def validate_record(row):
    """Validate one complete SQLite row, including frozen claims and identifiers."""
    if isinstance(row, dict):
        row = [row[k] for k in ('day', 'forecast', 'status', 'checked_at', 'last_result',
                               'container_id', 'media_id', 'published_at')]
    day, payload, status, checked, result, container, media, claimed = row
    if (date.fromisoformat(day).isoformat() != day or status not in STATES or result not in RESULTS
            or datetime.fromisoformat(checked).tzinfo is None):
        raise ValueError('Invalid weather story state')
    forecast = validate_forecast(json.loads(payload)) if payload else None
    if (forecast and forecast['date'] != day) or (not forecast and status != 'blocked'):
        raise ValueError('Missing or wrong weather day')
    for value in (container, media):
        if value is not None and (not isinstance(value, str) or not re.fullmatch(r'\d{1,32}', value)):
            raise ValueError('Invalid weather media id')
    if media and not container:
        raise ValueError('Weather media without container')
    if status in ('publishing', 'published', 'uncertain'):
        stamp = datetime.fromisoformat(claimed) if claimed else None
        if (stamp is None or stamp.tzinfo is None or stamp.astimezone(TZ).date().isoformat() != day
                or stamp.astimezone(TZ).hour != 8):
            raise ValueError('Invalid morning weather claim')
    elif claimed is not None or container is not None or media is not None:
        raise ValueError('Unclaimed weather has delivery metadata')
    if status == 'published' and (not container or not media):
        raise ValueError('Missing weather delivery identifiers')
    from .security import assert_no_secrets
    assert_no_secrets(tuple(row))
