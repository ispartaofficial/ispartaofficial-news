"""AEDAŞ's own planned-outage list for Isparta.

The site's `county` field names one district of a record that can span several,
and a record can also carry Antalya or Burdur. The published message is the
evidence, so districts and places come from its Isparta segments. The official
list keeps unrelated street fragments, so the place names are a short summary;
the card still sends people to the official notice for streets.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import json
import re

from .readers import TZ, base_item, norm, text

WINDOW = timedelta(days=7)
MAX_RECORDS = 1000
MAX_PLACES = 5
STAMP = '%Y-%m-%d %H:%M:%S'
SPAN = '%d/%m/%Y %H:%M:%S'


def proper(value):
    """Turkish title case; `str.lower` and `upper` are wrong for I and i."""
    words = value.replace('I', 'ı').replace('İ', 'i').lower().split()
    return ' '.join({'i': 'İ', 'ı': 'I'}.get(w[0], w[0].upper()) + w[1:] for w in words)


def place_name(value):
    """`SAVKÖY KÖYÜ FATİH Mah.` is Savköy Köyü, `MERKEZ ALACA MESCİT Mah.` Alaca Mescit."""
    words = text(value).split()
    if len(words) >= 2 and norm(words[1]) == 'köyü':
        return proper(words[0]) + ' Köyü', True
    if len(words) >= 3 and norm(words[0]) == 'merkez' and 'Mah.' in words:
        return proper(' '.join(words[1:words.index('Mah.')])), True
    if len(words) >= 2 and norm(words[0]) == 'merkez' and words[1].isalpha():
        return proper(words[1]), False
    return None, False


def places(values):
    """Named neighbourhoods first; a bare word only where nothing longer covers it."""
    found = [place_name(v) for v in values]
    named = list(dict.fromkeys(name for name, certain in found if name and certain))
    bare = [name for name, certain in found if name and not certain
            and not any(n.startswith(name) for n in named)]
    return named + list(dict.fromkeys(bare))


def segments(message, province, counties):
    """{district: raw place fragments} from the Isparta parts of one message."""
    if ' bölgelerinde ' not in message:
        raise ValueError('aedas_message_structure')
    found = {}
    for part in message.split(' bölgelerinde ', 1)[0].split(';'):
        fields = [text(f) for f in part.split(',')]
        if len(fields) >= 2 and fields[0] == province and fields[1] in counties:
            found.setdefault(fields[1], []).extend(fields[2:])
    return found


def aedas_outages(body, source, at):
    rows = json.loads(body)
    if not isinstance(rows, list) or len(rows) > MAX_RECORDS:
        raise ValueError('aedas_list_structure')
    groups = {}
    for row in rows:
        plan = row.get('plannedOutage') if isinstance(row, dict) else None
        if not isinstance(plan, dict) or not isinstance(plan.get('message'), str):
            continue
        try:
            start = datetime.strptime(str(plan.get('startDateTime')), STAMP).replace(tzinfo=TZ)
            end = datetime.strptime(str(plan.get('endDateTime')), STAMP).replace(tzinfo=TZ)
        except ValueError:
            continue
        message = plan['message']
        # A record whose text disagrees with its own fields proves neither.
        if end <= start or f'{start.strftime(SPAN)} - {end.strftime(SPAN)} saatleri arasında' not in message:
            continue
        if end <= at or start > at + WINDOW:
            continue
        found = segments(message, source['province'], source['counties'])
        if not found:
            continue
        group = groups.setdefault((tuple(found), start, end), {'parts': {}, 'reasons': []})
        for county, values in found.items():
            group['parts'].setdefault(county, []).extend(values)
        reason = text(plan.get('reason'))
        if reason and reason not in group['reasons']:
            group['reasons'].append(reason)
    return [_item(source, *key, group) for key, group in groups.items()]


def _item(source, counties, start, end, group):
    locatives = source['counties']
    names = [locatives[c].split('’')[0] for c in counties]
    if len(counties) == 1:
        title = locatives[counties[0]] + ' planlı elektrik kesintisi'
        listed = places(group['parts'][counties[0]])
        shown = ', '.join(listed[:MAX_PLACES]) + (' ve diğer bölgeler' if len(listed) > MAX_PLACES else '')
        location = names[0] + (' · ' + shown if shown else '')
    else:
        title = 'Isparta’da planlı elektrik kesintisi'
        location = 'Isparta · ' + ', '.join(n.removeprefix('Isparta ') for n in names)
    reasons = ', '.join(group['reasons'])
    description = (f'AEDAŞ planlı kesinti kaydına göre {start:%d.%m.%Y %H:%M} ile {end:%d.%m.%Y %H:%M} arasında '
                   f'elektrik kesintisi yapılacak. Etkilenen bölge: {location}.' + (f' Neden: {reasons}.' if reasons else ''))
    item = base_item(source, title, description, kind='event', key=f'{"+".join(counties)}|{start}|{end}',
                     url=source['display_url'])
    item.update(start=start.isoformat(), end=end.isoformat(), time_known=True, location=location,
                organizer='AEDAŞ', valid_until=end.isoformat(), date_conflict=False,
                audience={'kind': 'public', 'evidence': None, 'minimum_age': None})
    return item
