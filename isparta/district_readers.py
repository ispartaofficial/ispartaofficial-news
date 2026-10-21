"""Reviewed district portals and university channels; discovery is not news."""
from __future__ import annotations

from datetime import datetime
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .readers import (DISTRICTS, MONTHS, TZ, _audience,
                      date_conflict, dotted, norm, public_link, text)
from .scope_readers import archive_article, campus_notice


def source_identity(html, source):
    soup = BeautifulSoup(html, 'html.parser')
    node = soup.select_one(source['identity_selector'])
    if not node or not re.search(source['identity_pattern'], text(node), re.I):
        raise ValueError('official_district_identity_changed')
    return soup


def official_entries(html, source, at, limit):
    soup = source_identity(html, source)
    groups = []
    for feed in source['feeds']:
        entries = {}
        for a in soup.select(feed['selector']):
            url = public_link(a.get('href'), source['url'], same_host=True)
            if not url or not re.fullmatch(source['detail_path'], urlsplit(url).path):
                continue
            heading = a.select_one(feed['title_selector']) if feed.get('title_selector') else a
            label = text(heading)
            if not label:
                continue
            dates = [dotted(text(n)) for n in a.select(feed.get('date_selector', 'no-such-date'))]
            date = dates[0] if dates and all(d is not None and d == dates[0] for d in dates) else None
            entry = dict(url=url, title=label, archive_date=date.isoformat() if date else None,
                         archive_date_conflict=bool(dates and date is None), feed_kind=feed['kind'])
            if url in entries and entries[url] != entry:
                entries[url]['archive_date_conflict'] = True
            else:
                entries.setdefault(url, entry)
        groups.append(list(entries.values()))
    # Read both news and notices; a long news list must not hide the notice feed.
    result = []
    seen = set()
    for index in range(limit):
        for group in groups:
            if index < len(group) and group[index]['url'] not in seen:
                result.append(group[index]); seen.add(group[index]['url'])
                if len(result) == limit:
                    return result
    return result


def official_article(html, url, source, entry):
    source_identity(html, source)
    item = archive_article(html, url, source, entry)
    if not item['title']:
        raise ValueError('official_article_title_missing')
    item.update(official_jurisdiction='Isparta', official_district=source['district'],
                source_identity_verified=True, feed_kind=entry['feed_kind'])
    if entry['feed_kind'] == 'notice':
        # Public notices often consist of attachments. Upload date does not prove
        # a deadline, service window, cancellation status or current validity.
        item['parser_holds'].append('official_notice_validity_requires_review')
    return item


def official_locality(item, combined):
    district = norm(item.get('official_district', ''))
    reviewed = {norm(x) for x in DISTRICTS} | {'aksu', norm('Gönen')}
    if (item.get('official_jurisdiction') != 'Isparta'
            or item.get('source_identity_verified') is not True or district not in reviewed):
        return False
    # Registry plus the portal's actual contact address disambiguates Gönen and
    # Aksu. A syndicated outside-city report is still withheld for local review.
    from .readers import OUTSIDE
    if re.search(OUTSIDE, combined):
        return False
    return bool(re.search(r'\b' + re.escape(district) + r'\b|\bilçemiz\w*\b', combined))


def turkish_day(value):
    months = {norm(k): v for k, v in MONTHS.items()}
    match = re.fullmatch(r'(\d{1,2})\s+(' + '|'.join(months) +
                         r')\s+(20\d{2})(?:\s+(?:pazartesi|sali|çarşamba|perşembe|cuma|cumartesi|pazar))?', norm(value))
    if not match:
        return None
    try:
        return datetime(int(match[3]), months[match[2]], int(match[1]), tzinfo=TZ)
    except ValueError:
        return None


def campus_portal(html, url, source, entry):
    item = campus_notice(html, url, source, entry)
    soup = BeautifulSoup(html, 'html.parser')
    content = soup.select_one(source['body_selector'])
    # This portal uses sibling divs rather than paragraphs. Read the specific
    # article container, never navigation, footer dates or an image filename.
    description = text(content)
    if len(description) > 14000:
        raise ValueError('campus_article_exceeds_budget')
    # A free shuttle, meal or giveaway does not make event admission free.
    fee=('Ücretsiz' if re.search(r'\b(?:katilim|etkinlik|giriş)\s+ücretsiz(?:dir)?[.!;]?(?:\s|$)', norm(description))
         and not re.search(r'ücretsiz\s+(?:değil|degil)',norm(description)) else 'Ücret açıklanmamış')
    item.update(description=description, fee=fee, source_content_type='campus_article')
    lines = [text(n) for n in content.find_all(['p', 'div'], recursive=False) if text(n)]
    labels = {}
    for line in lines:
        match = re.fullmatch(r'(Tarih|Saat|Yer)\s*:\s*(.+)', line, re.I)
        if match:
            labels.setdefault(norm(match[1]), []).append(match[2])
    if any(len(set(v)) != 1 for v in labels.values()):
        item['parser_holds'].append('conflicting_labelled_session_details')
        return item
    day = turkish_day(labels.get('tarih', [''])[0]) or dotted(labels.get('tarih', [''])[0])
    clock = re.fullmatch(r'([01]?\d|2[0-3])[.:]([0-5]\d)', labels.get('saat', [''])[0])
    venue = labels.get('yer', [None])[0]
    if day and clock and venue:
        start = day.replace(hour=int(clock[1]), minute=int(clock[2]))
        item.update(start=start.isoformat(), time_known=True, location=venue,
                    date_conflict=date_conflict(description, start),
                    audience=_audience(description))
        item['parser_holds'].remove('campus_session_details_require_corroboration')
    return item


def club_directory(html, source):
    soup = BeautifulSoup(html, 'html.parser')
    content = soup.select_one(source['body_selector'])
    if content is None:
        raise ValueError('club_directory_structure_missing')
    clubs = []
    seen = set()
    for row in content.select('table tr'):
        cells = row.find_all(['td', 'th'], recursive=False)
        if len(cells) < 2 or not re.fullmatch(r'\d{1,3}', text(cells[0])):
            continue
        name = text(cells[1])
        if not 3 <= len(name) <= 180:
            raise ValueError('club_directory_name_invalid')
        if norm(name) not in seen:
            seen.add(norm(name))
            # Do not export student/adviser names or contact details from other
            # columns. This is an organisation directory, not an event record.
            clubs.append({'name': name, 'official_directory': source['url'],
                          'event_reader_verified': False, 'publishing_enabled': False})
    if not clubs or len(clubs) > 250:
        raise ValueError('club_directory_rows_missing_or_exceed_budget')
    return clubs
