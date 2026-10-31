import json
from datetime import datetime
from pathlib import Path

import pytest

from isparta.readers import TZ
from isparta.research import assess, same_story
from isparta.runtime import category
from isparta.scope_readers import listed_sessions, listing_entries

CONFIG = json.loads((Path(__file__).parents[1]/'config/research-sources.json').read_text(encoding='utf8'))
SOURCES = {s['id']: s for s in CONFIG['sources']}
AT = datetime(2026, 11, 1, 10, tzinfo=TZ)
TICKETS = 'https://biletinial.com/tr-tr/muzik/ozbi-konseri'
CALENDAR = 'https://etkinlik.io/etkinlik/306424/jefe'


def session(region='Isparta', start='2026-11-04T21:30:00+03:00', **values):
    return {'@context': 'https://schema.org', '@type': 'Event', 'name': 'Ozbi Konseri', 'startDate': start,
            'description': 'Ozbi, şarkılarını hayranlarıyla birlikte hep bir ağızdan seslendirecek.',
            'image': 'https://cdn.example.org/ozbi.jpg', 'eventStatus': 'https://schema.org/EventScheduled',
            'location': {'@type': 'Place', 'name': 'Isparta Holly Stone',
                         'address': {'streetAddress': 'Süleyman Demirel Cd. No:81', 'addressRegion': region}},
            'offers': {'price': 900.0, 'priceCurrency': 'TRY', 'availability': 'https://schema.org/InStock'},
            'organizer': {'@type': 'Organization', 'name': 'İyi Yapım'}, **values}


def page(*records, title='Ozbi Konseri', extra=''):
    return ('<html><body><h1>' + title + '</h1><dl><dt>Yaş Sınırı</dt><dd>18+</dd></dl>'
            '<script type="application/ld+json">' + json.dumps(list(records), ensure_ascii=False) + '</script>'
            + extra + '</body></html>')


def calendar_page(region='Isparta', genre='Konser', ticket=True):
    event = {'@type': 'Event', 'name': 'Jefe', 'startDate': '2026-11-18T22:00:00+03:00',
             'description': 'Jefe, 18 Kasım akşamı Holly Stone Isparta sahnesinde sizlerle.',
             'eventStatus': 'https://schema.org/EventScheduled',
             'location': {'name': 'Holly Stone Isparta', 'address': {'addressRegion': region}}}
    crumbs = {'@type': 'BreadcrumbList', 'itemListElement': [
        {'name': name} for name in ('Ana Sayfa', 'Isparta', genre, 'Parti ve Canlı Müzik', 'Jefe')]}
    link = '<a href="https://etkinlik.io/redirect-ticket-url/306424?token=x">Bilet Al</a>' if ticket else ''
    return ('<h1>Jefe</h1><script type="application/ld+json">' + json.dumps([crumbs, event], ensure_ascii=False)
            + '</script>' + link + '<a href="https://etkinlik.io/redirect-ticket-url/999">Bilet Al</a>')


def test_touring_show_keeps_only_its_isparta_session():
    rows = listed_sessions(page(session('İzmir', '2026-10-31T22:00:00+03:00'), session(),
                                session('Denizli', '2026-11-05T22:00:00+03:00')), TICKETS, SOURCES['biletinial-isparta'])
    assert [r['start'] for r in rows] == ['2026-11-04T21:30:00+03:00']
    row = rows[0]
    assert row['location'] == 'Isparta Holly Stone · Süleyman Demirel Cd. No:81 · Isparta'
    assert row['organizer'] == 'İyi Yapım' and row['price'] == 900.0 and row['currency'] == 'TRY'
    assert row['ticket_platform'] == 'Biletinial' and row['source_event_category'] == 'concert'
    assert row['audience'] == {'kind': 'ticketed', 'evidence': 'Biletli etkinlik. Yaş sınırı 18+.', 'minimum_age': 18}
    assert row['end'] == row['start'] and row['time_known'] is True and row['parser_holds'] == []


def test_show_without_an_isparta_session_yields_nothing():
    assert listed_sessions(page(session('İzmir')), TICKETS, SOURCES['biletinial-isparta']) == []


@pytest.mark.parametrize('values,hold', [
    ({'eventStatus': 'https://schema.org/EventCancelled'}, 'ticket_session_not_scheduled'),
    ({'offers': {'price': 900, 'priceCurrency': 'TRY', 'availability': 'https://schema.org/SoldOut'}},
     'ticket_availability_unconfirmed_or_sold_out'),
])
def test_unsold_or_cancelled_session_is_held(values, hold):
    assert hold in listed_sessions(page(session(**values)), TICKETS, SOURCES['biletinial-isparta'])[0]['parser_holds']


def test_records_of_another_show_are_not_borrowed():
    with pytest.raises(ValueError, match='ticket_event_schema_required'):
        listed_sessions(page(session(), title='Başka Konser'), TICKETS, SOURCES['biletinial-isparta'])


def test_calendar_event_is_ticketed_only_by_its_own_ticket_link():
    source = SOURCES['etkinlik-isparta']
    row = listed_sessions(calendar_page(), CALENDAR, source)[0]
    assert row['audience']['kind'] == 'ticketed' and row['fee'] == 'Ücret açıklanmamış'
    assert row['source_event_category'] == 'concert' and row['end'] == row['start']
    assert listed_sessions(calendar_page(ticket=False), CALENDAR, source)[0]['audience']['kind'] == 'unknown'


@pytest.mark.parametrize('genre,expected', [('Konser', 'concert'), ('Festival', 'festival'),
                                            ('Sahne Sanatları', 'theatre'), ('Spor', None)])
def test_calendar_genre_comes_from_the_events_own_breadcrumb(genre, expected):
    row = listed_sessions(calendar_page(genre=genre), CALENDAR, SOURCES['etkinlik-isparta'])[0]
    assert row.get('source_event_category') == expected


def test_supplied_genre_reaches_the_engine_category():
    row = listed_sessions(calendar_page(), CALENDAR, SOURCES['etkinlik-isparta'])[0]
    assert category(row) == 'concert'


def test_listing_page_is_not_read_as_a_show():
    html = ('<a href="/tr-tr/muzik/isparta">Isparta</a><a href="/tr-tr/muzik/ozbi-konseri">Ozbi</a>'
            '<a href="/tr-tr/tiyatro/oyun">Oyun</a>')
    rows = listing_entries(html, SOURCES['biletinial-isparta'], AT, 14)
    assert [r['url'] for r in rows] == [TICKETS]


def test_whole_short_calendar_is_read_without_rotation():
    html = ''.join(f'<a href="/etkinlik/{n}/etkinlik-{n}">x</a>' for n in range(1, 14))
    assert len(listing_entries(html, SOURCES['etkinlik-isparta'], AT, 14)) == 13


def test_concert_passes_research_gates():
    row = listed_sessions(page(session()), TICKETS, SOURCES['biletinial-isparta'])[0]
    assert assess(row, AT, CONFIG['venues'])['eligible_for_drafting'] is True


def test_same_session_on_two_listings_is_one_story():
    ticket = {'kind': 'event', 'source_id': 'biletinial-isparta', 'title': 'Ozbi Konseri', 'description': 'Birinci kaynak',
              'start': '2026-11-04T21:30:00+03:00', 'location': 'Isparta Holly Stone'}
    listing = {**ticket, 'source_id': 'etkinlik-isparta', 'title': 'Ozbi', 'description': 'İkinci kaynak',
               'location': 'Holly Stone Isparta'}
    assert same_story(ticket, listing)
    assert not same_story(ticket, {**listing, 'start': '2026-11-05T21:30:00+03:00'})
    assert not same_story(ticket, {**listing, 'title': 'Jefe'})
