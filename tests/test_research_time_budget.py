"""22 Nov: four research runs were cancelled at the 15-minute job limit (#550-#577)."""
import json
from pathlib import Path
from urllib.parse import urlsplit

import requests
import yaml

from isparta.fetch import Fetcher

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config/research-sources.json').read_text(encoding='utf-8'))
SOURCES = {s['id']: s for s in CONFIG['sources']}


def test_research_job_leaves_room_for_a_slow_apt_mirror_and_other_jobs_are_unchanged():
    flow = yaml.safe_load((ROOT / '.github/workflows/research.yml').read_text(encoding='utf-8'))
    jobs = flow['jobs']
    # 9-11 minute preparation + up to 4 minutes of setup on a slow mirror.
    assert jobs['research']['timeout-minutes'] == 22
    assert jobs['publish']['timeout-minutes'] == 15
    assert 'timeout-minutes' not in jobs['deploy']
    # The production lock still never cancels a running job.
    assert flow['concurrency'] == {'group': 'isparta-production', 'cancel-in-progress': False}


def test_cloud_timed_out_outage_source_gets_one_short_attempt():
    source = SOURCES['aedas-planli']
    assert source['research_enabled'] and 'zaman aşımı' in source['quiet_acknowledged']
    fetcher = Fetcher([source])
    host = urlsplit(source['url']).hostname
    connect, read = fetcher.timeouts[host]
    assert (connect, read) == (8, 20) and fetcher.timeout_retries[host] == 0
    # Was up to two attempts of 15 + 45 seconds in every run.
    assert (connect + read) * (1 + fetcher.timeout_retries[host]) <= 30


def test_a_timed_out_outage_read_is_not_repeated(monkeypatch):
    source = SOURCES['aedas-planli']
    fetcher = Fetcher([source])
    calls = []

    def once(url):
        calls.append(url)
        raise requests.Timeout('offline')
    monkeypatch.setattr(fetcher, '_get_once', once)
    monkeypatch.setattr('isparta.fetch.time.sleep', lambda seconds: None)
    try:
        fetcher.get(source['url'])
    except requests.Timeout:
        pass
    assert calls == [source['url']]


def test_cloud_blocked_press_source_is_acknowledged_not_bypassed():
    source = SOURCES['uyan32']
    # Same pattern as Bubilet and Etkinlik.io: still read, known block, no workaround.
    assert source['research_enabled'] and '403' in source['quiet_acknowledged']
    assert 'Engel aşılmaz' in source['quiet_acknowledged']
