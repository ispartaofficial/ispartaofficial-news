"""Isparta starts 25 October; no extra slot or fourth pair on the prior day."""
from datetime import date
import json
from pathlib import Path

import pytest

from news_engine.domain import parse_date
from news_engine.instagram import publish_automatic
from news_engine.publication_policy import (EVENING_EFFECTIVE_FROM, daily_limit_reason,
    dispatch_window, evening_enabled, evening_summary, news_windows)
from news_engine.schedule import SLOTS
from test_automatic_publication import api
from test_evening_policy import add_news, asset_map, three_pairs


def test_isparta_activation_is_same_in_runtime_config_and_actual_policy():
    runtime=json.loads(Path('config/runtime.json').read_text(encoding='utf-8'))
    assert EVENING_EFFECTIVE_FROM == date(2026,10,25)
    assert runtime['evening_news_effective_from'] == EVENING_EFFECTIVE_FROM.isoformat()
    assert runtime['daily_news_feed_limit'] == runtime['daily_news_story_limit'] == 3
    assert runtime['evening_news_daily_maximum'] == 4
    assert runtime['facebook_enabled'] is False
    assert runtime['weather_enabled'] is True and runtime['pharmacy_stories_enabled'] is True


@pytest.mark.parametrize('clock',['20:30','22:30','23:20'])
def test_previous_evening_has_neither_new_window_nor_fourth_pair(store,clock):
    at=parse_date('2026-10-24T'+clock+':00+03:00')
    three_pairs(store,at)
    parent=add_news(store,at,'notactive')
    assert not evening_enabled(at)
    assert dispatch_window(at,SLOTS) is None
    assert daily_limit_reason(store,at,parent) == 'daily_limit'
    adapter=api()
    before=store.rows("SELECT * FROM posts WHERE status IN ('published','publishing','uncertain') ORDER BY id")
    assert publish_automatic(store,at,'https://example.org/',asset_map(store),adapter)['status'] == 'outside_window'
    adapter.container.assert_not_called()
    assert store.rows("SELECT * FROM posts WHERE status IN ('published','publishing','uncertain') ORDER BY id") == before


def test_pre_activation_keeps_original_21_window_without_bonus():
    at=parse_date('2026-10-24T21:30:00+03:00')
    window=dispatch_window(at,SLOTS)
    assert window[0].hour == 21 and window[2] is False
    assert not evening_summary(at)['enabled']
    assert [w[0].hour for w in news_windows(at.date(),SLOTS)] == [8,12,15,18,21]


@pytest.mark.parametrize('clock,evening_only',[('20:30',True),('21:30',False),('22:30',True),('23:20',True)])
def test_activation_day_adds_only_the_bounded_evening_windows(clock,evening_only):
    at=parse_date('2026-10-25T'+clock+':00+03:00')
    assert evening_enabled(at)
    window=dispatch_window(at,SLOTS)
    assert window is not None and window[2] is evening_only
    assert evening_summary(at)['effective_from'] == '2026-10-25'
    assert dispatch_window(parse_date('2026-10-25T23:30:00+03:00'),SLOTS) is None


def test_operations_reports_true_effective_window_and_keeps_service_stories_separate(store):
    from news_engine.operations import summary
    from news_engine.factory import summary as factory_summary
    before=summary(store,parse_date('2026-10-24T20:30:00+03:00'))
    assert before['window_start'] == '2026-10-24T21:00:00+03:00'
    assert not before['window_open'] and not before['evening_news']['enabled']
    after=summary(store,parse_date('2026-10-25T23:20:00+03:00'))
    assert after['window_start'] == '2026-10-25T22:00:00+03:00'
    assert after['window_end'] == '2026-10-25T23:30:00+03:00' and after['window_open']
    assert after['daily_feed_limit'] == after['daily_story_limit'] == 3
    assert after['evening_news']['absolute_daily_feed_limit'] == 4
    assert after['service_stories_extra'] == ['weather','pharmacy']
    factory=factory_summary(store,parse_date('2026-10-25T10:00:00+03:00'))
    assert factory['daily_news_feed_limit'] == factory['daily_news_story_limit'] == 3
    assert factory['evening_news']['effective_from'] == '2026-10-25'
    assert factory['evening_news']['absolute_daily_story_limit'] == 4
