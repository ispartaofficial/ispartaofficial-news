"""Conservative subject selection. A category is never evidence of an incident."""
from .editor import event_activity


def subject(item: dict) -> str | None:
    from .visual_topics import news_subjects
    if item.get('visual_calendar') is True and item.get('kind') == 'event':
        return 'event_calendar'
    if item.get('kind') != 'event' or item.get('category') == 'outage':
        return news_subjects(item)[1]
    if activity := event_activity(item.get('category'), item.get('title', '')):
        return activity
    from .domain import normalized
    import re
    # Rebetiko is an explicit musical genre, not an inference from a venue.
    if re.search(r'\brebetiko\b', normalized(item.get('title',''))):
        return 'concert'
    category = item.get('category')
    # Career days stay in the broad "event" category and could never get a
    # visual, so their card waited forever (31 Oct: "Geleceğim Meslekte").
    if category == 'event' and re.search(r'\b(?:kariyer|meslek|seminer|sempozyum)\w*\b', normalized(item.get('title',''))):
        return 'education'
    return category if category in (
        'theatre', 'concert', 'cinema', 'festival', 'culture', 'family',
        'sport', 'market', 'food', 'education') else None
