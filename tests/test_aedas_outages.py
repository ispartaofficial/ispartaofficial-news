import json
from datetime import datetime
from pathlib import Path

import pytest

from isparta.outage_reader import aedas_outages, place_name, places, proper
from isparta.readers import TZ
from isparta.research import assess
from isparta.runtime import adapt, sources_for_engine
from news_engine.editor import verify

CONFIG = json.loads((Path(__file__).parents[1]/'config/research-sources.json').read_text(encoding='utf8'))
SOURCE = next(s for s in CONFIG['sources'] if s['id'] == 'aedas-planli')
AT = datetime(2026, 11, 1, 10, tzinfo=TZ)
TAIL = ' saatleri arasında Bakım Çalışması Sebebi ile elektrik kesintisi yapılacaktır.'


def record(areas, start='2026-11-02 09:00:00', end='2026-11-02 16:00:00', county='MERKEZ', reason='Bakım Çalışması'):
    day = lambda v: datetime.strptime(v, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
    return {'id': '1', 'plannedOutage': {
        'reason': reason, 'city': 'ISPARTA', 'county': county, 'startDateTime': start, 'endDateTime': end,
        'message': f'{areas} bölgelerinde {day(start)} - {day(end)}{TAIL}'}}


def read(*rows):
    return aedas_outages(json.dumps(list(rows), ensure_ascii=False), SOURCE, AT)


@pytest.mark.parametrize('value,expected', [
    ('SANAYİ', 'Sanayi'), ('KIZILBELEN', 'Kızılbelen'), ('İSTİKLAL', 'İstiklal'),
    ('ALACA MESCİT', 'Alaca Mescit'), ('IŞIKLAR', 'Işıklar'),
])
def test_turkish_title_case(value, expected):
    assert proper(value) == expected


@pytest.mark.parametrize('value,expected', [
    ('MERKEZ SANAYİ Mah. 153 Cd', ('Sanayi', True)),
    ('MERKEZ ALACA MESCİT Mah. YENİ Sk.', ('Alaca Mescit', True)),
    ('SAVKÖY KÖYÜ FATİH Mah. 540 Sk.', ('Savköy Köyü', True)),
    ('BOĞAZKÖY Köyü KÖYÜN KENDİSİ', ('Boğazköy Köyü', True)),
    ('MERKEZ DAVRAZ 3926', ('Davraz', False)),
    ('. .', (None, False)),
])
def test_place_names_from_the_official_fragments(value, expected):
    assert place_name(value) == expected


def test_bare_word_never_shortens_a_named_neighbourhood():
    assert places(['MERKEZ KONYA BUCAĞI HAŞİMAĞA ( 19.SOK. )', 'MERKEZ KONYA BUCAĞI Mah. BÜKLÜMOĞLU Sk.']) == ['Konya Bucağı']


def test_one_district_record_becomes_one_event():
    rows = read(record('ISPARTA,MERKEZ,MERKEZ SANAYİ 153,MERKEZ SANAYİ Mah. 3234 Sk.,MERKEZ İSTİKLAL Mah. 1102/1 Sk.'))
    assert len(rows) == 1
    row = rows[0]
    assert row['title'] == 'Isparta Merkez’de planlı elektrik kesintisi'
    assert row['location'] == 'Isparta Merkez · Sanayi, İstiklal'
    assert row['start'] == '2026-11-02T09:00:00+03:00' and row['end'] == '2026-11-02T16:00:00+03:00'
    assert row['valid_until'] == row['end'] and row['time_known'] is True and row['organizer'] == 'AEDAŞ'
    assert row['url'] == SOURCE['display_url'] and 'Neden: Bakım Çalışması.' in row['description']


def test_district_comes_from_the_message_not_the_county_field():
    row = read(record('ISPARTA,GÖNEN,GÖLBAŞI KÖYÜ 100025,MERKEZ ALACA MESCİT Mah. YENİ Sk.', county='MERKEZ'))[0]
    assert row['title'] == 'Isparta Gönen’de planlı elektrik kesintisi'
    assert row['location'] == 'Isparta Gönen · Gölbaşı Köyü, Alaca Mescit'


def test_other_provinces_in_one_record_are_dropped():
    rows = read(record('ANTALYA,MANAVGAT,MERKEZ YEŞİLBAĞ Mah.;ISPARTA,SÜTÇÜLER,MERKEZ BİRLİK Mah. ATATÜRK Cd'))
    assert rows[0]['location'] == 'Sütçüler · Birlik'


def test_record_only_for_another_province_is_ignored():
    assert read(record('BURDUR,BUCAK,KIZILLI KÖYÜ HATİPKÖY Mah.')) == []


def test_record_across_districts_names_each_district():
    row = read(record('ISPARTA,AKSU,AKPINAR KÖYÜ AŞAĞI Mah.;ISPARTA,EĞİRDİR,BAKLAN Köyü KÖYÜN KENDİSİ'))[0]
    assert row['title'] == 'Isparta’da planlı elektrik kesintisi'
    assert row['location'] == 'Isparta · Aksu, Eğirdir'


def test_same_district_and_clock_merge_into_one_card():
    rows = read(record('ISPARTA,MERKEZ,MERKEZ DAVRAZ Mah. 3932 Sk.'),
                record('ISPARTA,MERKEZ,MERKEZ VATAN Mah. 1 Sk.', reason='Deplase Çalışması'))
    assert len(rows) == 1 and rows[0]['location'] == 'Isparta Merkez · Davraz, Vatan'
    assert 'Bakım Çalışması, Deplase Çalışması' in rows[0]['description']


def test_identity_survives_a_change_in_the_affected_places():
    first = read(record('ISPARTA,MERKEZ,MERKEZ DAVRAZ Mah. 3932 Sk.'))[0]
    second = read(record('ISPARTA,MERKEZ,MERKEZ VATAN Mah. 1 Sk.'))[0]
    assert first['id'] == second['id'] and first['location'] != second['location']


def test_unnamed_area_keeps_the_district_only():
    assert read(record('ISPARTA,YALVAÇ,. .'))[0]['location'] == 'Yalvaç'


def test_long_area_list_is_bounded_for_the_card():
    areas = ','.join(f'MERKEZ MAHALLE{c} Mah. 1 Sk.' for c in 'ABCDEFG')
    location = read(record('ISPARTA,MERKEZ,' + areas))[0]['location']
    assert location.endswith(' ve diğer bölgeler') and location.count(',') == 4


@pytest.mark.parametrize('values', [
    {'start': '2026-10-31 09:00:00', 'end': '2026-10-31 16:00:00'},  # already over
    {'start': '2026-11-20 09:00:00', 'end': '2026-11-20 16:00:00'},  # beyond a week
    {'start': '2026-11-02 16:00:00', 'end': '2026-11-02 09:00:00'},  # reversed
    {'start': 'yarın', 'end': '2026-11-02 16:00:00'},
])
def test_unusable_clock_is_ignored(values):
    row = record('ISPARTA,MERKEZ,MERKEZ DAVRAZ Mah.')
    row['plannedOutage'].update(startDateTime=values['start'], endDateTime=values['end'])
    assert read(row) == []


def test_fields_that_disagree_with_their_own_message_prove_nothing():
    row = record('ISPARTA,MERKEZ,MERKEZ DAVRAZ Mah.')
    row['plannedOutage']['endDateTime'] = '2026-11-02 18:00:00'
    assert read(row) == []


def test_unexpected_list_shape_fails_the_source_visibly():
    with pytest.raises(ValueError):
        aedas_outages('{"error": true}', SOURCE, AT)


def test_outage_passes_research_and_engine_gates_as_a_story_only_cut():
    row = assess(read(record('ISPARTA,MERKEZ,MERKEZ DAVRAZ Mah. 3932 Sk.'))[0], AT, CONFIG['venues'])
    assert row['eligible_for_drafting'] is True
    item = adapt(row)
    assert item['category'] == 'outage' and item['status'] == 'scheduled'
    assert verify(item, sources_for_engine({'sources': [SOURCE]})[0], AT) is None
    from news_engine.publication_policy import story_only
    assert story_only(item)
