"""Reviewed weather spelling; no guessed timing, severity or temperatures."""
from __future__ import annotations

from datetime import date, datetime
import re
import unicodedata

VERSION = 'weather-copy-v1'


class WeatherTextError(ValueError):
    pass


def reviewed(forecast):
    return forecast.get('display_version') == VERSION


def display_condition(forecast):
    description = unicodedata.normalize('NFC', forecast['condition'])
    if (not reviewed(forecast) or any(unicodedata.category(c) in ('Cc', 'Cf', 'Cs') for c in description)
            or not any(c.isalpha() for c in description) or description.rstrip().endswith(('...', '…'))):
        raise WeatherTextError('Unreadable forecast text')
    # Exact reviewed spelling only; never fuzzily change the meaning of a term.
    def spelling(match):
        word = match.group()
        return 'PUSLU' if word.isupper() else 'Puslu' if word[:1].isupper() else 'puslu'
    description = re.sub(r'\bpuzlu\b', spelling, description, flags=re.I)
    description = ' '.join(description.split())
    if datetime.fromisoformat(forecast['period_start']).date() < date.fromisoformat(forecast['date']):
        description = re.sub(r'\byarın\b', 'bugün', description, flags=re.I)
    return description
