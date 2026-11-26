"""Conservative publication holds for incomplete or superseded social notices."""
import re

from .domain import normalized
from .text_quality import plain_display, source_body


def news_quality_reason(item: dict) -> str | None:
    if item.get('kind') != 'news':
        return None
    title = item.get('title', '')
    if not isinstance(title, str) or not re.search(r'[^\W\d_]', title):
        # A contact number, punctuation or emoji alone cannot describe a story.
        return 'insufficient_headline'
    if (item.get('source_id') == 'instagram-sehayder'
            and re.search(r'\b(?:ailesi|sahibi) bulundu\b|\b(?:sahiplendirildi|yuvalandirildi)\b', normalized(title))):
        # This source retains the earlier appeal/contact instructions below its
        # resolved heading. Do not republish that old call for help as current.
        return 'resolved_community_notice'
    return None


# Owner, 26 Nov 2026 (Seferihisar "Barınakta"): a one-word heading cut from an
# Instagram caption, over a shelter adoption appeal with a private mobile
# number, went out as a news card. Neither is a news story.
MIN_HEADLINE_WORDS = 3
# Turkish mobile numbers: 05xx / +90 5xx / 90 5xx / 5xx, with or without
# spaces, dots, dashes or brackets. Landlines (0232..., 0246...), 444 lines and
# short codes (112, 153) never start with 5 after the optional 0/90 prefix.
MOBILE_NUMBER = re.compile(r'(?<![\d+])(?:\+\s*90|\b90)?[\s.\-]*\(?\s*0?\s*5\d{2}\s*\)?[\s.\-]*'
                           r'\d{3}[\s.\-]*\d{2}[\s.\-]*\d{2}(?!\d)')
SOCIAL_SOURCES = ('instagram-', 'facebook-')


def mobile_number(text: str) -> bool:
    return bool(MOBILE_NUMBER.search(text or ''))


def headline_words(title: str) -> int:
    return sum(bool(re.search(r'\w', word)) for word in (title or '').split())


def caption_fragment(item: dict) -> bool:
    """A heading that is only the cut first line of a social media caption."""
    title = (item.get('title') or '').strip()
    if title.endswith(('…', '...')):
        return True
    if not str(item.get('source_id', '')).startswith(SOCIAL_SOURCES):
        return False
    prose = (item.get('description') or '').strip()
    if not title or not prose.startswith(title):
        return False
    rest = prose[len(title):]
    # The caption goes on with an ellipsis, or the length cap cut a word/sentence.
    return bool(re.match(r'\s*(?:…|\.\.)', rest) or re.match(r'\w', rest))


def headline_gate_reason(item: dict, display_title: str) -> str | None:
    if caption_fragment(item):
        return 'headline_caption_fragment'
    if headline_words(display_title) < MIN_HEADLINE_WORDS:
        return 'headline_too_short'
    return None


def folded(value: str) -> str:
    """`normalized` without Turkish diacritics: NÖBETÇİ, nöbetçi, nobetci agree."""
    return normalized(value).translate(str.maketrans('şğüöçâîû', 'sguocaiu'))


# Isparta, 22 Nov 2026: Haber32's "Isparta ve İlçelerde Nöbetçi Eczaneler
# (22 Kasım 2026)" went out as a news card: an address heap without pharmacy
# names, a source logo graphic and the source's own wrong date. The day's list
# already has its own checked story (pharmacy.py, docs/daily-pharmacy-story.md),
# and the morning forecast has one too (weather.py). A routine list or bulletin
# for those services is not a news card. Reports about a pharmacy (a robbery,
# a chamber statement) or a weather warning remain news.
PHARMACY_LIST = re.compile(
    r'\bnobetci (?:olan )?eczaneler\b|\bnobetci (?:olan )?eczane\w* listesi\b'
    r'|\bhangi eczaneler? nobetci\b|\bnobetci eczane\w* (?:hangi|nerede)\b')
# A body names the list itself, not just pharmacies on duty during a holiday.
PHARMACY_LIST_BODY = re.compile(r'\bnobetci (?:olan )?eczane\w* listesi\b|\bnobetci olan eczaneler\b')
PHARMACY_STORY = re.compile(
    r'\b(?:soy(?:gun|ul|du)|hirsiz|gasp|saldir|kavga|yangin|kaza\b|kazada|ceza|muhur|tepki|'
    r'protesto|aciklama|eylem|kapat|grev|yakala|gozalti|tutuk|darp|bicak|silah|olay|sikayet|'
    r'eczaci|zam\b|zamm|ucret)\w*|\bodasi\w*')
WEATHER_BULLETIN = re.compile(r'\bhava durumu\b')
WEATHER_STORY = re.compile(
    r'\b(?:uyar|alarm|firtina|saganak|kuvvetli|siddetli|tehlike|dikkat|afet|zirai don|'
    r'sari kod|turuncu kod|kirmizi kod|kar yagis|dolu yagis|sel\b|selin|taskin)\w*')


def dedicated_service_reason(item: dict) -> str | None:
    """A routine list or bulletin another daily story already publishes."""
    from urllib.parse import urlsplit
    title = folded(plain_display(item.get('title') or ''))
    slug = folded(urlsplit(item.get('url') or '').path.replace('-', ' '))
    if (not PHARMACY_STORY.search(title)
            and (PHARMACY_LIST.search(title) or PHARMACY_LIST.search(slug)
                 or PHARMACY_LIST_BODY.search(folded(item.get('description') or '')))):
        return 'dedicated_pharmacy_story'
    if WEATHER_BULLETIN.search(title) and not WEATHER_STORY.search(title):
        return 'dedicated_weather_story'
    return None


MONTHS = ('ocak', 'subat', 'mart', 'nisan', 'mayis', 'haziran', 'temmuz',
          'agustos', 'eylul', 'ekim', 'kasim', 'aralik')
WEEKDAYS = ('pazartesi', 'sali', 'carsamba', 'persembe', 'cuma', 'cumartesi', 'pazar')
CALENDAR_DATE = re.compile(r'\b([0-3]?\d) (' + '|'.join(MONTHS) + r')\w*(?: (20\d\d))?'
                           r'(?: (' + '|'.join(WEEKDAYS) + r')\b(?! yer| esnaf| tezgah))?')
# "6 Mart Spor Salonu", "29 Ekim Caddesi": a yearless name, not a date.
PLACE_NAME = re.compile(r' (?:ataturk )?(?:spor|kapali|cad\b|cadde|bulvar|mah\b|mahalle|park|meydan|'
                        r'stad|okul|ilkokul|ortaokul|lise|kopru|sok\b|sokak|universite)')


def calendar_dates(value: str) -> list[tuple[int, int, int | None, str | None]]:
    """Explicit day+month(+year)(+weekday) dates only; nothing relative or numeric."""
    text, found = folded(value), []
    for match in CALENDAR_DATE.finditer(text):
        day, month, year, weekday = match.groups()
        if not 1 <= int(day) <= 31 or (not year and PLACE_NAME.match(text, match.end())):
            continue
        found.append((int(day), MONTHS.index(month) + 1, int(year) if year else None, weekday))
    return found


def date_mismatch(item: dict) -> bool:
    """The headline's one explicit date is absent from a body that gives dates,
    or a dated weekday is not that date's weekday ("12 Kasım 2026 Pazar").

    Relative words, numeric dates and several headline dates are left alone.
    """
    from datetime import date
    title = calendar_dates(item.get('title') or '')
    body = calendar_dates(item.get('description') or '')
    for day, month, year, weekday in title + body:
        if year and weekday:
            try:
                if WEEKDAYS[date(year, month, day).weekday()] != weekday:
                    return True
            except ValueError:
                return True
    named = {(day, month) for day, month, _, _ in title}
    if len(named) != 1 or not body:
        return False
    day, month = next(iter(named))
    years = {year for _, _, year, _ in title if year}
    return not any((d, m) == (day, month) and not (y and years and y not in years)
                   for d, m, y, _ in body)


def news_editorial_reason(item: dict) -> str | None:
    """Publication hold, separate from immutable source intake/provenance."""
    if item.get('kind') != 'news':
        return None
    from .domain import local
    from .editorial_voice import neutral_terms, source_voice
    if not isinstance(item.get('title'),str) or not isinstance(item.get('description'),str):
        return 'editorial_copy_required'
    if reason := dedicated_service_reason(item):
        return reason
    if date_mismatch(item):
        # The card would carry one of the two dates, and nothing says which.
        return 'date_mismatch'
    if mobile_number(item['title'] + '\n' + item['description']):
        # A private contact number marks an adoption/help appeal, not news.
        return 'personal_mobile_number'
    title = plain_display(item.get('title',''))
    value = normalized(title)
    vague = re.search(r'\bböyle\b.*\bhep olsun$|\biyi ki varsiniz\b|^(?:'
                      r'dikkat(?: dikkat)*|bekle\b.*|engelli canlara öncelik|'
                      r'elleri minik\b.*|harika haber\b.*|müjde(?: müjde)*)$', value)
    if (not value or len(title)>160 or vague or title.endswith(('…','...'))
            or source_voice(neutral_terms(title))):
        return 'editorial_headline_required'
    from .editor import news_title
    if reason := headline_gate_reason(item, news_title(item)):
        return reason
    body = source_body(item)
    if len(re.findall(r'\w+',body)) < 5 or normalized(body) == value:
        return 'editorial_copy_required'
    outside_quotes = re.sub(r'“[^”]*”|"[^"]*"','',body)
    if re.search(r'\b(?:takip etmeyi|abone olmayı|yorumlarda buluş|iyi ki varsınız|'
                 r'hep olsun|paylaşmayı unutmayın)\b',outside_quotes,re.I):
        return 'editorial_copy_required'
    from .editor import news_body
    if 'Kaynak açıklamasında “' in news_body(item):
        # The old fallback could turn unreviewed institutional/campaign voice
        # into a long quotation card. It is not an edited news summary.
        return 'editorial_copy_required'
    if item.get('source_id','').startswith('instagram-') and not local(
            title+' '+body+' '+(item.get('location') or '')):
        return 'editorial_context_required'
    return None


def publication_copy_reason(post: dict, items: dict) -> str | None:
    """Recheck the frozen draft at the actual destination, before any claim."""
    from . import event_metadata
    from .editor import caption
    from .schedule import slide_body
    if post.get('kind') in ('weekend', 'free_week'):
        from .local_series import current_copy
        if not current_copy(post, items):
            return 'event_metadata_stale'
    item = items.get(post.get('item_id'), {})
    if item.get('kind') == 'event' and item.get('category') != 'outage' and event_metadata.needs_review(item):
        if (post.get('caption') != caption(item, post.get('title', ''))
                or post.get('slides') != [{'title': post.get('title'), 'body': slide_body(item)}]):
            return 'event_metadata_stale'
    if post.get('kind') in ('weekly', 'monthly', 'weekend', 'free_week'):
        urls = post.get('source_urls', [])
        slides = post.get('slides', [])
        for index, url in enumerate(urls, 1):
            matches = [i for i in items.values() if i.get('kind') == 'event'
                       and url in i.get('sources', []) + [i.get('url')]]
            if any(event_metadata.needs_review(i) for i in matches):
                if (len(slides) != len(urls) + 1
                        or not any(slides[index].get('body') == slide_body(i) for i in matches)):
                    return 'event_metadata_stale'
    if post.get('kind') != 'news':
        return None
    item = items.get(post.get('item_id'),{})
    if item.get('kind') != 'news' or news_editorial_reason(item):
        return 'editorial_review_required'
    from .editor import headline, caption
    from .media_caption import without_photo_credit
    from .schedule import slide_body
    title = headline(item,'news')
    if (post.get('title') != title
            or without_photo_credit(post.get('caption', '')) != without_photo_credit(caption(item,title))
            or post.get('slides') != [{'title':title,'body':slide_body(item)}]):
        return 'editorial_copy_stale'
    return None
