"""Reviewed Isparta source structures; parsing does not authorize publication."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

TZ = ZoneInfo('Europe/Istanbul')
MONTHS = {name: i for i, name in enumerate(('ocak', 'şubat', 'mart', 'nisan', 'mayıs',
    'haziran', 'temmuz', 'ağustos', 'eylül', 'ekim', 'kasım', 'aralık'), 1)}
DISTRICTS = ('eğirdir', 'gelendost', 'keçiborlu', 'senirkent', 'sütçüler',
             'şarkikaraağaç', 'uluborlu', 'yalvaç', 'yenişarbademli', 'atabey')
OUTSIDE = r'\b(?:antalya|ankara|istanbul|izmir|bursa|balikesir|bilecik|denizli|afyonkarahisar|burdur)\b'


def text(node):
    value = node.get_text(' ', strip=True) if hasattr(node, 'get_text') else str(node or '')
    value = ''.join(c for c in unicodedata.normalize('NFC', value)
                    if unicodedata.category(c) not in ('Cf', 'Cs', 'So'))
    return ' '.join(value.split())


def norm(value):
    return text(value).casefold().replace('i\u0307', 'i').replace('ı', 'i')


def canonical(url):
    p = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(p.query) if not k.startswith('utm_') and k not in ('fbclid', 'gclid')]
    return p._replace(fragment='', query=urlencode(query)).geturl()


def public_link(url, base, *, same_host=False):
    value = urljoin(base, str(url or ''))
    p = urlsplit(value)
    if (not url or p.scheme != 'https' or not p.hostname or p.username or p.password
            or p.port not in (None, 443) or (same_host and p.hostname != urlsplit(base).hostname)):
        return None
    if re.search(r'(?:token|password|secret|signature)', p.query, re.I):
        return None
    return canonical(value)


def timestamp(value):
    value = str(value or '').strip()
    if not re.fullmatch(r'20\d{2}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?', value):
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.replace(tzinfo=TZ) if dt.tzinfo is None else dt.astimezone(TZ)
    except ValueError:
        return None


def dotted(value):
    m = re.fullmatch(r'(\d{1,2})\.(\d{1,2})\.(20\d{2})(?: (\d{1,2}):(\d{2}))?', text(value))
    if not m:
        return None
    d, mo, y, h, mi = m.groups()
    try:
        return datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0), tzinfo=TZ)
    except ValueError:
        return None


def date_conflict(description, start, end=None):
    """Conservative contradiction check; unlabelled competing dates stay held.

    A date range matching the start/end is allowed. No year is invented for a
    candidate start: a yearless prose date only cross-checks the explicit calendar.
    """
    if not start:
        return False
    end = end or start
    normalized = norm(description)
    month_pattern = '|'.join(norm(x) for x in MONTHS)
    months = {norm(k): v for k, v in MONTHS.items()}
    range_confirmed = False
    for match in re.finditer(r'(?<!\d)(\d{1,2})(?:\s*[–—-]\s*(\d{1,2}))?\s+(' + month_pattern + r')(?:\s+(20\d{2}))?\b', normalized):
        day, last, month, year = match.groups()
        if (int(day), months[month]) != (start.day, start.month):
            return True
        if year and int(year) != start.year:
            return True
        if last and (int(last), months[month]) != (end.day, end.month):
            return True
        range_confirmed |= bool(last)
    for match in re.finditer(r'(?<!\d)(\d{1,2}\.\d{1,2}\.20\d{2})(?!\d)', normalized):
        dt = dotted(match[1])
        if not dt or dt.date() not in (start.date(), end.date()):
            return True
    if end.date() != start.date() and not range_confirmed:
        # A month-long calendar entry paired with a single-day description is
        # not treated as an ongoing event. A fuller reviewed range is needed.
        return True
    for match in re.finditer(r'(?<!\d)(\d{1,2})[.:](\d{2})\s*[–—-]\s*(\d{1,2})[.:](\d{2})(?!\d)', normalized):
        h, m, eh, em = map(int, match.groups())
        if (h, m) != (start.hour, start.minute) or (eh, em) != (end.hour, end.minute):
            return True
    return False


def base_item(source, title, description, *, kind, key, url=None):
    source_url = canonical(url or source['url'])
    identity = hashlib.sha256(f"{source['id']}|{key}".encode()).hexdigest()[:24]
    return {'id': identity, 'kind': kind, 'source_id': source['id'],
            'source_name': source['name'], 'url': source_url, 'title': text(title),
            'description': text(description), 'image_candidate': None,
            'image_status': 'not_reviewed', 'parser_holds': [], 'published': False}


def news_links(html, source, limit=4):
    soup = BeautifulSoup(html, 'html.parser')
    found = []
    for a in soup.select(source['link_selector']):
        target = public_link(a.get('href'), source['url'], same_host=True)
        if (target and re.fullmatch(source['detail_path'], urlsplit(target).path)
                and target not in found):
            found.append(target)
    return found[:limit]


def article(html, url, source):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.select_one(source['title_selector'])
    content = soup.select_one(source['body_selector'])
    if not title or not content:
        raise ValueError('reviewed_article_fields_missing')
    body = [text(p) for p in content.select('p') if len(text(p)) > 25]
    if not body:
        raise ValueError('article_body_missing')
    item = base_item(source, text(title), ' '.join(body), kind='news', key=canonical(url), url=url)
    dates = [timestamp(n.get('content')) for n in soup.select(source['date_selector'])]
    published = dates[0] if dates and all(d == dates[0] and d is not None for d in dates) else None
    if source.get('date_format') == 'dotted_date':
        dates = [dotted(text(n)) for n in soup.select(source['date_selector'])]
        published = dates[0] if dates and all(d == dates[0] and d is not None for d in dates) else None
    item['published_at'] = published.isoformat() if published else None
    # Never substitute dateModified, sidebar dates or the current header date.
    item['published_time_known'] = bool(published and source.get('date_format') != 'dotted_date')
    photo = soup.select_one('meta[property="og:image"]')
    item['image_candidate'] = public_link(photo.get('content'), url) if photo else None
    if len(item['description']) > 14000:
        raise ValueError('article_body_exceeds_budget')
    return item


def _audience(description):
    value = text(description)
    n = norm(value)
    # Keep the actual condition, not a generic "everyone" inferred from an invite.
    restricted = ('öğrenci', 'ogrenci', 'üyeler', 'uyeler', 'başvuru', 'basvuru',
                  'kayıt', 'kayit', 'kontenjan', 'sınıf', 'sinif')
    if any(k in n for k in restricted):
        return {'kind': 'restricted', 'evidence': value}
    if re.search(r'herkese açik|halka açik|tüm halkimiz|tum halkimiz', n):
        return {'kind': 'public', 'evidence': value}
    return {'kind': 'unknown', 'evidence': None}


def _fee(description):
    n = norm(description)
    return ('Ücretsiz' if re.search(r'\bücretsiz(?:dir)?\b', n)
            and not re.search(r'ücretsiz\s+(?:değil|degil)', n) else 'Ücret açıklanmamış')


def isubu(html, source):
    soup = BeautifulSoup(html, 'html.parser')
    groups = [c for c in soup.select('div.card-stretch') if c.select_one('.card-label')
              and text(c.select_one('.card-label')) == 'Yaklaşan etkinlikler']
    if len(groups) != 1:
        raise ValueError('isubu_upcoming_section_missing')
    cards = [c for c in groups[0].select('div.card.card-custom.gutter-b')
             if not c.select('div.card.card-custom.gutter-b')]
    if len(cards) > 100:
        raise ValueError('isubu_calendar_exceeds_budget')
    results = []
    for card in cards:
        title = card.select_one('.flex-grow-0')
        metadata = card.select('.d-flex.flex-wrap.my-2 a')
        description = card.select_one('.font-size-h7')
        if not title or len(metadata) != 3 or not description:
            raise ValueError('isubu_card_structure_changed')
        raw_dates = text(metadata[0]).split(' - ')
        start, end = (map(dotted, raw_dates) if len(raw_dates) == 2 else (None, None))
        venue, organizer = map(text, metadata[1:])
        item = base_item(source, title, description, kind='event', key=text(title)+'|'+str(start))
        item.update(start=start.isoformat() if start else None, end=end.isoformat() if end else None,
                    time_known=bool(start and end and all(':' in d for d in raw_dates)),
                    location=venue, organizer=organizer, audience=_audience(description),
                    fee=_fee(description), date_conflict=date_conflict(text(description), start, end))
        image = card.select_one('.symbol img')
        item['image_candidate'] = public_link(image.get('src'), source['url'], same_host=True) if image else None
        results.append(item)
    if not results:
        raise ValueError('isubu_calendar_missing')
    # This source currently reuses one placeholder for unrelated events.
    duplicates = Counter(x['image_candidate'] for x in results if x['image_candidate'])
    for item in results:
        if duplicates[item['image_candidate']] > 1:
            item['image_candidate'] = None
            item['image_status'] = 'reused_placeholder_rejected'
    return results


def sdu(html, source):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for table in soup.select('table'):
        fields = {text(tr.th): text(tr.td) for tr in table.select('tr') if tr.th and tr.td}
        if 'Etkinlik Adı' not in fields:
            continue
        title, description = fields['Etkinlik Adı'], fields.get('Açıklama', '')
        day = dotted(fields.get('Etkinlik Tarihi', ''))
        # A calendar day isn't a known performance time.
        hour = re.search(r'\bsaat(?:leri)?\s*[:*]*\s*(\d{1,2})[.:](\d{2})(?:\s*[–—-]\s*(\d{1,2})[.:](\d{2}))?', norm(description))
        start, end = day, None
        if hour and day:
            try:
                start = day.replace(hour=int(hour[1]), minute=int(hour[2]))
                if hour[3]:
                    end = day.replace(hour=int(hour[3]), minute=int(hour[4]))
            except ValueError:
                start = None
        venue = None
        # Preserve prose line boundaries when extracting a labelled venue.
        desc_node = next((tr.td for tr in table.select('tr') if tr.th and text(tr.th) == 'Açıklama'), None)
        if desc_node:
            raw = desc_node.get_text('\n', strip=True)
            venue = re.search(r'(?:yer|mek[âa]n)\s*[:*]+\s*([^\n\r]+)', raw, re.I)
        location = text(venue[1]).strip(' *') if venue else None
        item = base_item(source, title, description, kind='event', key=title+'|'+str(day))
        item.update(start=start.isoformat() if start else None, end=end.isoformat() if end else None,
                    time_known=bool(hour and start), location=location,
                    organizer=fields.get('Düzenleyen'), audience=_audience(description),
                    fee=_fee(description), date_conflict=date_conflict(description, start, end))
        modal = table.find_parent(class_='modal-body')
        image = modal.select_one('img') if modal else None
        item['image_candidate'] = public_link(image.get('src'), source['url']) if image else None
        results.append(item)
    if not results:
        raise ValueError('sdu_calendar_missing')
    return results
