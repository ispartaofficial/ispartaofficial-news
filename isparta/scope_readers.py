"""Official archives, campus notices and reviewed ticket sessions.

Missing dates/participation facts stay missing. Parsing a poster announcement
does not pretend its picture has been read. Public HTML transport is decoded as
JSON/text only; JavaScript is never executed and no private API is used.
"""
from __future__ import annotations

from datetime import timedelta
import json
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .readers import (base_item, canonical, dotted, norm, public_link, text,
                      timestamp, _audience, _fee)


def html_text(value):
    return text(BeautifulSoup(str(value or ''), 'html.parser'))


def listing_entries(html, source, at, limit):
    """Dates are bound to the very same anchor as the reviewed title/URL."""
    soup = BeautifulSoup(html, 'html.parser')
    entries = {}
    for a in soup.select(source['link_selector']):
        url = public_link(a.get('href'), source['url'], same_host=True)
        if not url or not re.fullmatch(source['detail_path'], urlsplit(url).path):
            continue
        title_node = a.select_one(source['listing_title_selector']) if source.get('listing_title_selector') else a
        label = text(title_node)
        if source.get('listing_title_before_break'):
            parts=[]
            for child in a.children:
                if getattr(child,'name',None)=='br':break
                parts.append(str(child))
            label=html_text(''.join(parts))
        dates = []
        if source.get('listing_date_selector'):
            dates = [dotted(text(n)) for n in a.select(source['listing_date_selector'])]
        date = dates[0] if dates and all(d == dates[0] and d is not None for d in dates) else None
        entry = {'url':url, 'title':label, 'archive_date':date.isoformat() if date else None,
                 'archive_date_conflict':bool(dates and (date is None))}
        if url in entries and (entries[url]['archive_date'], entries[url]['title']) != (entry['archive_date'], entry['title']):
            entries[url]['archive_date_conflict'] = True
        else:
            entries.setdefault(url, entry)
    rows = list(entries.values())
    if source.get('discovery_order') == 'id_descending':
        # Only crawl priority; IDs never become a publication date.
        rows.sort(key=lambda r:int(re.search(r'/TR-(\d+)/', r['url'])[1]), reverse=True)
    if source.get('reader') == 'ticketing' and len(rows) > limit:
        # Retain leading cards and rotate the rest. A permanently static first
        # page must not hide all other concerts. No dates inferred from labels.
        leading = min(4, limit)
        tail = rows[leading:]
        slot = int(at.timestamp() // 7200)
        offset = (slot * (limit-leading)) % len(tail)
        rows = rows[:leading] + (tail[offset:]+tail[:offset])[:limit-leading]
    return rows[:limit]


def _publication(soup, source):
    nodes = soup.select(source.get('date_selector', 'meta[name=datePublished]'))
    values = []
    for node in nodes:
        mode = source.get('date_format')
        raw = text(node) if mode in ('labelled', 'dotted_date', 'turkish_date') else node.get(source.get('date_attribute', 'content'))
        if mode == 'dotted_date':
            values.append(dotted(raw))
            continue
        if mode == 'turkish_date':
            from .district_readers import turkish_day
            values.append(turkish_day(raw))
            continue
        if mode == 'iso_date':
            values.append(timestamp(raw+'T00:00:00') if raw and re.fullmatch(r'20\d{2}-\d{2}-\d{2}', raw) else None)
            continue
        if source.get('date_format') == 'labelled':
            match = re.fullmatch(r'Yayın Tarihi:\s*(\d{1,2}[./]\d{1,2}[./]20\d{2}(?: \d{1,2}:\d{2})?)', raw)
            if match:
                values.append(dotted(match[1].replace('/','.')))
        else:
            values.append(timestamp(raw))
    return values[0] if values and all(d == values[0] and d is not None for d in values) else None


def archive_article(html, url, source, entry):
    soup = BeautifulSoup(html, 'html.parser')
    heading = soup.select_one(source['title_selector'])
    content = soup.select_one(source['body_selector'])
    if heading is None or content is None:
        raise ValueError('reviewed_official_article_structure_missing')
    paragraphs = [text(p) for p in content.select('p') if len(text(p)) > 25]
    description = ' '.join(paragraphs)
    if not description and source.get('body_text_fallback'):
        description = text(content)
    if len(description)>14000:
        raise ValueError('official_article_exceeds_budget')
    item = base_item(source, heading, description, kind='news', key=canonical(url), url=url)
    if norm(entry['title']) != norm(item['title']):
        item['parser_holds'].append('archive_title_does_not_match_article')
    explicit = _publication(soup, source)
    archive = timestamp(entry.get('archive_date'))
    if entry.get('archive_date_conflict') or (explicit and archive and explicit.date() != archive.date()):
        item['parser_holds'].append('archive_and_article_dates_conflict')
    date = explicit or archive
    item.update(published_at=date.isoformat() if date else None,
                published_time_known=bool(explicit and source.get('date_format') not in ('date_only','dotted_date','iso_date','turkish_date')),
                publication_date_origin='article' if explicit else 'same_anchor_archive' if archive else 'missing',
                publication_date_evidence=url if explicit else source['url'] if archive else None)
    image = content.select_one('img[src]')
    item['image_candidate'] = public_link(image.get('src'), url) if image else None
    if not description:
        item['parser_holds'].append('source_body_missing')
    if source.get('jurisdiction') == 'Isparta':
        item['official_jurisdiction'] = 'Isparta'
    return item


def campus_notice(html, url, source, entry):
    soup = BeautifulSoup(html, 'html.parser')
    heading = soup.select_one(source['title_selector'])
    content = soup.select_one(source['body_selector'])
    if heading is None or content is None:
        raise ValueError('reviewed_campus_notice_structure_missing')
    description = ' '.join(text(p) for p in content.select('p') if text(p))
    date = _publication(soup, source)
    item = base_item(source, heading, description, kind='event', key=canonical(url), url=url)
    image = content.select_one('img[src]')
    item.update(published_at=date.isoformat() if date else None,
                image_candidate=public_link(image.get('src'), url) if image else None,
                announcement_date_is_event_date=False, start=None, end=None, time_known=False,
                location=None, organizer=source['name'], audience=_audience(description), fee=_fee(description),
                source_content_type='poster_announcement' if len(description)<30 and image else 'campus_report_or_notice')
    item['parser_holds'].append('campus_session_details_require_corroboration')
    if date is None:
        item['parser_holds'].append('original_announcement_date_missing')
    if norm(entry['title']) != norm(item['title']):
        item['parser_holds'].append('archive_title_does_not_match_article')
    return item


def correlate_campus(items):
    """A matching, dated official calendar can corroborate a poster notice.

    Keep the calendar's restrictions and holds; an upload timestamp or a poster
    never approves or corrects a conflicting calendar. Ambiguous matches remain held.
    """
    for item in items:
        if 'campus_session_details_require_corroboration' not in item.get('parser_holds', []):
            continue
        calendar_id = 'sdu-calendar' if item['source_id']=='sdu-sks' else 'isubu-events'
        candidates = [c for c in items if c['source_id']==calendar_id and norm(c['title'])==norm(item['title']) and c.get('start')]
        if len(candidates) != 1:
            continue
        calendar = candidates[0]
        announced,start=timestamp(item.get('published_at')),timestamp(calendar.get('start'))
        if not announced or not start or not timedelta(0)<=start-announced<=timedelta(days=30):
            # Recurring generic titles must not link an old poster to a new year.
            continue
        item['corroborating_calendar_id'] = calendar['id']
        # The notice is evidence, never a second announcement of the same event.
        item['parser_holds'].append('corroborated_notice_use_calendar_record')
        calendar.setdefault('corroborating_sources', []).append(item['url'])


def culture_year_link(html, source, at):
    soup=BeautifulSoup(html,'html.parser')
    matches=[public_link(a.get('href'),source['url'],same_host=True)
             for a in soup.select('.inner_mid_left .art_loop .search_item a[href]')
             if text(a)==f'{at.year} Yılı']
    matches=[u for u in matches if u and re.fullmatch(r'/TR-\d+/20\d{2}-yili\.html',urlsplit(u).path)]
    if len(set(matches))>1:raise ValueError('ambiguous_current_year_archive')
    return matches[0] if matches else None


def culture_items(html,url,source,entry):
    soup=BeautifulSoup(html,'html.parser')
    heading=soup.select_one('#pageTitle')
    content=soup.select_one('.inner_mid_left .in_sec_1 > .art_loop')
    if not heading or content is None:raise ValueError('culture_article_structure_missing')
    day,venue,segment,items=None,None,[],[]
    for p in content.select('p'):
        value=text(p)
        if not value:continue
        date=dotted(value)
        if date and re.fullmatch(r'\d{1,2}\.\d{1,2}\.20\d{2}',value):
            day,venue,segment=date,None,[]
            continue
        place=re.fullmatch(r'Yer\s*:\s*(.{3,300})',value,re.I)
        clock=re.fullmatch(r'Saat\s*:\s*(\d{1,2})[.:](\d{2})',value,re.I)
        if place:
            venue=place[1]
        elif clock and day and venue:
            try:start=day.replace(hour=int(clock[1]),minute=int(clock[2]))
            except ValueError:continue
            description=' '.join(segment)
            item=base_item(source,heading,description,kind='event',key=url+'|'+start.isoformat()+'|'+norm(venue),url=url)
            item.update(start=start.isoformat(),end=None,time_known=True,location=venue,
                        organizer=source['name'],audience=_audience(description),fee=_fee(description),
                        date_conflict=False,source_content_type='explicit_local_program_session')
            items.append(item)
            venue,segment=None,[]
        else:
            segment.append(value)
    if items:return items
    # Body dates and a folder's creation date never become publication dates.
    return [archive_article(html,url,source,entry)]


def public_transport(soup):
    chunks = []
    for script in soup.select('script'):
        match = re.fullmatch(r'self\.__next_f\.push\((\[.*\])\);?', script.get_text(), re.S)
        if not match:
            continue
        try:
            record = json.loads(match[1])
        except (ValueError, TypeError):
            continue
        if len(record)==2 and record[0]==1 and isinstance(record[1],str):
            chunks.append(record[1])
    data = ''.join(chunks).encode('utf8')
    if len(data)>2_000_000:
        raise ValueError('public_transport_exceeds_budget')
    pos, texts, objects, seen = 0, {}, [], 0
    while pos<len(data) and seen<3000:
        seen += 1
        match = re.match(rb'([0-9a-f]+):', data[pos:])
        if not match:
            newline=data.find(b'\n',pos)
            pos=newline+1 if newline>=0 else len(data)
            continue
        key=match[1].decode();pos+=match.end()
        length=re.match(rb'T([0-9a-f]+),',data[pos:])
        if length:
            size=int(length[1],16);pos+=length.end()
            if size>100000 or pos+size>len(data):
                raise ValueError('invalid_public_text_record')
            value=data[pos:pos+size].decode('utf8');pos+=size
            if key in texts and texts[key]!=value:
                raise ValueError('conflicting_public_text_record')
            texts[key]=value
            continue
        newline=data.find(b'\n',pos)
        stop=newline if newline>=0 else len(data)
        raw=data[pos:stop].decode('utf8')
        if raw.startswith(('[','{')):
            try:objects.append(json.loads(raw))
            except ValueError:pass
        pos=stop+1
    return texts,objects


def _walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from _walk(child)
    elif isinstance(value,list):
        for child in value:yield from _walk(child)


def _ticket_category(soup, title, url):
    """A provider genre belongs to this event only with its exact breadcrumb.

    Navigation links, recommendations, venue names and organizer names are not
    genre evidence. Unknown tags (for example Trendler) add no classification.
    """
    genres = {'tiyatro': 'theatre', 'konser': 'concert',
              'festival': 'festival', 'sinema': 'cinema'}
    found = set()
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            value = json.loads(script.get_text())
        except (ValueError, TypeError):
            continue
        for obj in _walk(value):
            if obj.get('@type') != 'BreadcrumbList':
                continue
            elements = obj.get('itemListElement')
            if not isinstance(elements, list) or len(elements) != 3:
                continue
            if any(not isinstance(e, dict) for e in elements):
                continue
            if [e.get('position') for e in elements] != [1, 2, 3]:
                continue
            terminal = elements[-1]
            if (norm(terminal.get('name')) != norm(title)
                    or public_link(terminal.get('item'), url, same_host=True) != canonical(url)):
                continue
            genre = elements[1]
            label = norm(genre.get('name'))
            expected = urlsplit(url).path.split('/etkinlik/')[0] + '/etiket/' + label
            link = public_link(genre.get('item'), url, same_host=True)
            if label in genres and link == urlsplit(url)._replace(path=expected, query='', fragment='').geturl():
                found.add(genres[label])
    return next(iter(found)) if len(found) == 1 else None


def ticket_sessions(html, url, source):
    soup=BeautifulSoup(html,'html.parser')
    heading=soup.select_one('h1')
    title=text(heading)
    if not title:
        raise ValueError('ticket_title_missing')
    event_category = _ticket_category(soup, title, url)
    slug=urlsplit(url).path.rstrip('/').split('/')[-1]
    texts,records=public_transport(soup)
    event_metadata=[o for record in records for o in _walk(record)
                    if o.get('slug')==slug and norm(o.get('eventName'))==norm(title) and 'thingsToKnow' in o]
    rules=[]
    for obj in event_metadata:
        raw=obj['thingsToKnow']
        value=texts.get(raw[1:]) if isinstance(raw,str) and re.fullmatch(r'\$[0-9a-f]+',raw) else raw
        if isinstance(value,str) and not value.startswith('$'):
            rules.append(html_text(value))
    # Every separate rules component must agree with the current event's rules.
    for record in records:
        for obj in _walk(record):
            if set(obj)=={'thingsToKnow'}:
                value=obj['thingsToKnow']
                value=texts.get(value[1:]) if isinstance(value,str) and re.fullmatch(r'\$[0-9a-f]+',value) else value
                if isinstance(value,str) and not value.startswith('$'):rules.append(html_text(value))
    conditions=rules[0] if rules and all(r==rules[0] and len(r)>30 for r in rules) else None
    schemas=[]
    for script in soup.select('script[type="application/ld+json"]'):
        try:value=json.loads(script.get_text())
        except (ValueError,TypeError):continue
        # Do not borrow Site/Organization.address or unrelated recommendation events.
        candidates=value if isinstance(value,list) else [value]
        schemas += [o for o in candidates if isinstance(o,dict) and o.get('@type')=='Event' and norm(o.get('name'))==norm(title)]
    if len(schemas)!=1:
        raise ValueError('unique_ticket_event_schema_required')
    parent=schemas[0]
    sessions=parent.get('subEvent') or [parent]
    if not isinstance(sessions,list) or len(sessions)>40:
        raise ValueError('ticket_session_budget_or_structure')
    organizers=[text(a) for a in soup.select('#organizator-section a[href^="/organizator/"] h4')]
    results=[]
    for session in sessions:
        if not isinstance(session,dict):raise ValueError('ticket_session_structure')
        offer=session.get('offers',{})
        offer=offer if isinstance(offer,dict) else {}
        session_url=public_link(offer.get('url'),url,same_host=True)
        if session_url and not re.fullmatch(re.escape(urlsplit(url).path.rstrip('/'))+r'(?:/seans/\d+)?',urlsplit(session_url).path):
            session_url=None
        item=base_item(source,title,'',kind='event',key=session_url or url+'|'+str(session.get('startDate')),url=session_url or url)
        if event_category:
            item['source_event_category'] = event_category
        loc=session.get('location',{})
        loc=loc if isinstance(loc,dict) else {}
        address=loc.get('address',{})
        address=address if isinstance(address,dict) else {}
        venue=' · '.join(filter(None,[text(loc.get('name')),text(address.get('streetAddress')),text(address.get('addressLocality'))]))
        # Source schema commonly calls the ticket platform the organizer. Only
        # the event's actual organizer section can supply that separate fact.
        description=''
        for obj in event_metadata:
            value=obj.get('summary')
            value=texts.get(value[1:]) if isinstance(value,str) and re.fullmatch(r'\$[0-9a-f]+',value) else value
            if isinstance(value,str):description=html_text(value);break
        item['description']=description or html_text(session.get('description'))
        start,end=timestamp(session.get('startDate')),timestamp(session.get('endDate'))
        price=offer.get('price')
        price_valid=type(price) in (int,float) and 0<=price<=100000 and offer.get('priceCurrency')=='TRY'
        age=re.search(r'\b(\d{1,2})\s+yaş\s+alti\b',norm(conditions)) if conditions else None
        item.update(start=start.isoformat() if start else None,end=end.isoformat() if end else None,
                    time_known=bool(start and 'T' in str(session.get('startDate'))),location=venue or None,
                    organizer='; '.join(dict.fromkeys(organizers)) or None,ticket_platform='Bubilet',
                    audience={'kind':'ticketed' if conditions else 'unknown','evidence':conditions,
                              'minimum_age':int(age[1]) if age else None},
                    fee=f'Kaynak seans fiyatı: {price:g} TL' if price_valid else 'Ücret açıklanmamış',
                    price=price if price_valid else None,currency='TRY' if price_valid else None,
                    price_basis='listed_session_price_subject_to_ticket_conditions',
                    date_conflict=False)
        images=session.get('image') or parent.get('image') or []
        images=[images] if isinstance(images,str) else images
        item['image_candidate']=public_link(images[0],url) if isinstance(images,list) and images else None
        status=str(session.get('eventStatus','')).split('/')[-1]
        if status!='EventScheduled':item['parser_holds'].append('ticket_session_not_scheduled')
        availability=str(offer.get('availability','')).split('/')[-1]
        if availability!='InStock':item['parser_holds'].append('ticket_availability_unconfirmed_or_sold_out')
        if not conditions:item['parser_holds'].append('ticket_participation_conditions_unconfirmed')
        if not organizers:item['parser_holds'].append('actual_organizer_unconfirmed')
        if not session_url:item['parser_holds'].append('ticket_session_url_unconfirmed')
        results.append(item)
    return results
