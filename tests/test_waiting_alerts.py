"""Waits for a deploying card stay quiet; real failures and long waits still fail the job (7 Nov 2026)."""
import sys
from contextlib import closing
from datetime import timedelta
from unittest.mock import Mock

import pytest

from news_engine.domain import parse_date
from news_engine.operations import alarming, failed, record_check
from news_engine.store import Store

AT = parse_date('2026-11-06T19:03:00+03:00')
WAIT = {'status': 'visual_review_stale', 'outage_story': 'outside_window'}


def test_short_wait_for_a_deploying_card_does_not_fail_the_job(tmp_path):
    # 6 Nov 2026: three hourly runs waited for a rebuilt card, then it was published.
    with closing(Store(tmp_path / 'state.sqlite')) as store:
        for minutes in (0, 65, 115):
            at = AT + timedelta(minutes=minutes)
            observation = record_check(store, WAIT, at, 'automatic')
            assert failed(observation) and not alarming(store, observation, at)


def test_wait_alarms_after_two_hours_and_a_clear_check_restarts_the_clock(tmp_path):
    with closing(Store(tmp_path / 'state.sqlite')) as store:
        for minutes in (0, 60, 120):
            observation = record_check(store, WAIT, AT + timedelta(minutes=minutes), 'automatic')
        assert alarming(store, observation, AT + timedelta(minutes=120))
        record_check(store, {'status': 'published'}, AT + timedelta(minutes=180), 'automatic')
        observation = record_check(store, WAIT, AT + timedelta(minutes=240), 'automatic')
        assert not alarming(store, observation, AT + timedelta(minutes=240))


@pytest.mark.parametrize('result', [{'status': 'uncertain'}, {'status': 'disabled'},
    {'status': 'complete', 'facebook': {'status': 'media_missing'}},
    {'status': 'visual_review_stale', 'outage_story': 'awaiting_resolution'}])
def test_real_failure_still_fails_the_first_job(tmp_path, result):
    with closing(Store(tmp_path / 'state.sqlite')) as store:
        assert alarming(store, record_check(store, result, AT, 'automatic'), AT)


@pytest.mark.parametrize('status,exit_code', [('media_not_deployed', None), ('published', None),
                                              ('source_stale', 1), ('uncertain', 1)])
def test_pharmacy_job_waits_quietly_for_deployment(tmp_path, monkeypatch, status, exit_code):
    from isparta import production
    from news_engine import pharmacy
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['production', 'pharmacy'])
    monkeypatch.delenv('GITHUB_STEP_SUMMARY', raising=False)
    monkeypatch.setattr(production, 'resolve', lambda store, **kw: ('unit-hidden', {}))
    monkeypatch.setattr(production, 'persist', Mock())
    monkeypatch.setattr(pharmacy, 'run', lambda *a, **kw: {'status': status})
    if exit_code:
        with pytest.raises(SystemExit) as error:
            production.main()
        assert error.value.code == exit_code
    else:
        production.main()
