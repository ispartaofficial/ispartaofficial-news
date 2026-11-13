"""Biletinial's poster host answers 403 for robots.txt and 200 for every poster.

Owner decision, 12 Nov 2026: that one reviewed host may be read as having no
robots file. Every other answer and every other host stays closed.
"""
from unittest.mock import Mock

import pytest
import requests

from news_engine.collect import Fetcher
from news_engine.source_photo_data import delivery_sources

POSTER = 'https://b6s54eznn8xq.merlincdn.net/Uploads/Films/perde.jpg'
STAGE = {'id': 'biletinial-isparta-sahne', 'url': 'https://biletinial.com/tr-tr/tiyatro/isparta', 'enabled': True}
PAPER = {'id': 'haber32', 'url': 'https://www.haber32.com.tr/', 'enabled': True}


def session(robots_status, monkeypatch):
    monkeypatch.setattr('news_engine.collect.safe_url', lambda url, hosts: url)
    monkeypatch.setattr('news_engine.collect.time.sleep', lambda seconds: None)

    def get(url, **kwargs):
        response = Mock(is_redirect=False, headers={'Content-Type': 'image/jpeg'})
        if url.endswith('/robots.txt'):
            response.status_code = robots_status
            response.raise_for_status.side_effect = requests.HTTPError(response=response)
        response.iter_content.return_value = [b'\xff\xd8poster']
        return response
    return Mock(get=Mock(side_effect=get))


def test_only_the_reviewed_poster_host_reads_a_403_robots_file_as_absent(monkeypatch):
    hosts = delivery_sources({STAGE['id']: STAGE, PAPER['id']: PAPER})
    assert [s['url'] for s in hosts if s.get('robots_absent_as_403')] == ['https://b6s54eznn8xq.merlincdn.net/']
    assert Fetcher([STAGE] + hosts, session(403, monkeypatch)).image(POSTER)[0] == b'\xff\xd8poster'


@pytest.mark.parametrize('status', [401, 404, 429, 500, 503])
def test_every_other_robots_answer_still_stops_the_poster(monkeypatch, status):
    hosts = delivery_sources({STAGE['id']: STAGE})
    with pytest.raises(requests.HTTPError):
        Fetcher([STAGE] + hosts, session(status, monkeypatch)).image(POSTER)


def test_a_403_robots_file_still_stops_every_other_host(monkeypatch):
    with pytest.raises(requests.HTTPError):
        Fetcher([PAPER], session(403, monkeypatch)).get('https://www.haber32.com.tr/haber')
    unreviewed = {'enabled': True, 'url': 'https://b6s54eznn8xq.merlincdn.net/'}
    with pytest.raises(requests.HTTPError):
        Fetcher([unreviewed], session(403, monkeypatch)).image(POSTER)
