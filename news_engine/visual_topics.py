"""Reviewed visual subjects, separate from claims about a real event or place.

The headline identifies the main subject. Generated briefs describe generic
objects, never reported people, a named street, a team, an accident or damage.
An unknown subject waits for a verified image instead of receiving filler.
"""
import re

from .domain import normalized

LABELS = {
    'citrus_processing': 'a photograph of tangerines, orange peels and a small oil bottle on a table',
    'adult_workspace': 'a photograph of folded clothes and everyday craft materials on an adult training workspace',
    'public_park': 'a photograph of a park bench under trees in a green public park',
    'hiking': 'a news photograph of people hiking or walking together on a nature trail',
    'hiking_gear': 'a photograph of hiking boots and a backpack beside a nature trail',
    'glass_litter': 'a photograph of broken glass bottle fragments on a paved walkway',
    'football': 'a sports photograph of a football match on a grass football field',
    'football_equipment': 'a photograph of a football on a grass pitch near a goal',
    'meeting_room': 'a photograph of an empty meeting table and office chairs',
    'rain_puddle': 'a photograph of rain drops and a small puddle on wet pavement',
    'electrical': 'a photograph of electrical utility cables and unlabelled electrical equipment',
    'water_utility': 'a photograph of water utility pipes and a metal valve',
    'weather_sky': 'a photograph of a natural sky and clouds',
    'health_workspace': 'a photograph of a stethoscope and ordinary medical equipment on a desk',
    'public_service': 'a photograph of a plain clipboard and office supplies on an administrative desk',
    'land_planning': 'a photograph of unlettered architectural plans and a small building model on a desk',
    'travel_gear': 'a photograph of a camera, folded map and travel bag on a table',
    'animal_care': 'a photograph of a small wooden cat shelter and pet food bowls',
    'parking': 'a photograph of marked parking bays with parked cars',
    'bus': 'a photograph of a city bus seen from the side',
    'maintenance_tools': 'a photograph of road maintenance cones, asphalt and maintenance equipment',
}

SCENES = {
    'citrus_basket': 'A photographic close view of freshly harvested mandarins in a plain wicker basket on a simple table. No people harvesting, orchard identity, lettering or claim about an actual crop.',
    'citrus_processing': 'A photographic close view of tangerines, a few fresh mandarin peels and a small plain unlabelled oil bottle. No factory, manufacturing process, animals, people, lettering or unverified scientific claim.',
    'public_park': 'A photographic view of an ordinary unidentifiable park bench under leafy trees with natural greenery. No people, recognizable landmark, lettering or reconstruction of a named project.',
    'traffic': 'Generic traffic on an ordinary unidentifiable roadway, photographed with natural light. No collision, emergency, recognizable street, people, signs or readable plates.',
    'event_calendar': 'A photographic close view of a plain open planner, blank unlettered tickets and a pen on a desk. No calendar numbers, text, logos, people or invented event details.',
    'hiking_gear': 'A close photographic view of hiking boots and a plain backpack beside a generic nature trail. No people, landmark, lettering or claim about an actual trip.',
    'glass_litter': 'A close photographic view of a few broken glass bottle fragments on ordinary outdoor paving. No people, injury, recognizable street, alcohol brand or lettering.',
    'football_equipment': 'A close photographic view of an unbranded football resting on grass near an empty goal. No people, team logo, scoreboard, lettering or reconstruction of an actual match.',
    'meeting_room': 'An empty generic meeting table with plain chairs, a blank notebook and a microphone. No people, official insignia, venue identity or lettering.',
    'rain_puddle': 'A close photographic view of raindrops falling into a small puddle on plain wet paving. No flood, damage, emergency, people or recognizable location.',
    'electrical': 'A close photographic view of ordinary electrical utility cables and unlabelled maintenance equipment. No sparks, damage, people, lettering or identifiable location.',
    'water_utility': 'A close photographic view of ordinary water utility pipes and a metal valve. No burst pipe, flood, damage, people or lettering.',
    'weather_sky': 'A natural photographic view of sky and clouds without a recognizable landscape, storm damage, destruction, people or lettering.',
    'health_workspace': 'A photographic close view of a stethoscope and unlabelled medical equipment on a neutral desk. No patients, diagnosis, staff identity or lettering.',
    'public_service': 'A photographic close view of a plain blank clipboard and ordinary office supplies on an administrative desk. No people, seal, invented notice or lettering.',
    'land_planning': 'A photographic close view of blank architectural drawings and a small plain building model on a desk. No actual property, address, figures, lettering or specific project details.',
    'travel_gear': 'A photographic close view of a camera, folded unlettered map and plain travel bag. No people, coastline, landmark, destination claim or lettering.',
    'animal_care': 'A photographic close view of a small plain wooden cat shelter and unlabelled pet food bowls. No people, rescue incident, lettering or identifiable location.',
    'parking': 'An ordinary generic parking area with marked unnumbered bays and parked unbranded cars. No people, signs, readable plates or recognizable location.',
    'bus': 'A generic unlettered city bus photographed from the side. No readable route display, plates, passengers or recognizable location.',
    'maintenance_tools': 'A photographic close view of road maintenance cones, asphalt and plain maintenance equipment. No people, project sign, readable plates or recognizable street.',
}


def news_subjects(item):
    """Return (source-photo subject, generic generated subject) when supported."""
    if item.get('kind') not in ('news', 'event'):
        return None, None
    title = normalized(item.get('title', ''))
    category = item.get('category')
    if item.get('kind') == 'event' and category != 'outage':
        return None, None
    rules = (
        (r'\b(?:kedi\w*|hayvan\w*)\b.*\b(?:ev\w*|yuva\w*|mama\w*|barinak\w*)\b', 'animal_care', 'animal_care'),
        (r'\b(?:kirik|cam)\b.*\b(?:şişe\w*|cam\w*|parça\w*)\b|\b(?:şişe\w*)\b.*\bkirik\b', 'glass_litter', 'glass_litter'),
        (r'\b(?:doğa yürüy\w*|yürüdü|yürüyüş\w*|trekking)\b', 'hiking', 'hiking_gear'),
        (r'\b(?:futbol\w*|isparta32spor|gol\w*|mağlup\w*|süper lig)\b', 'football', 'football_equipment'),
        (r'\b(?:sel|su baskini|göle döndü|sular altinda)\b', 'flood', 'rain_puddle'),
        (r'\b(?:toplanti\w*|genel kurul|bir araya gel\w*|buluştu|bulustu)\b', 'meeting', 'meeting_room'),
        (r'\b(?:otopark\w*)\b', 'parking', 'parking'),
        (r'\b(?:otobüs\w*|eshot|dolmuş\w*|toplu ulaşim)\b', 'bus', 'bus'),
        (r'\b(?:asfalt\w*|yol çaliş\w*|yol yap\w*|yol onar\w*|cadde\w*.*(?:yenile\w*|değişim\w*))\b', 'roadworks', 'maintenance_tools'),
        (r'\b(?:trafik|çevre yolu|kavşak\w*)\b', 'traffic', 'traffic'),
        (r'\b(?:elektrik\w*)\b', 'electrical', 'electrical'),
        (r'\b(?:su kesinti\w*|su ariza\w*|su hatt\w*)\b', 'water_utility', 'water_utility'),
        (r'\b(?:hava durumu|meteoroloji\w*|yağmur\w*|yağiş\w*|sağanak\w*)\b', 'weather_sky', 'weather_sky'),
        (r'\b(?:arsa\w*|toki|imar\w*|konut\w*|inşaat\w*)\b', 'land_planning', 'land_planning'),
        (r'\b(?:gezi\w*|keşfet\w*|huzurlu ilçe\w*|turizm\w*)\b', 'landscape', 'travel_gear'),
    )
    if (re.search(r'\b(?:mandalina\w*|satsuma)\b', title)
            and re.search(r'\bhasa[td]\w*\b', title)):
        actual = bool(re.search(r'\b(?:başladi|sürüyor|yapiliyor)\b', title))
        return ('citrus_harvest' if actual else None), 'market'
    if re.search(r'\b(?:mandalina\w*|satsuma)\b', title):
        return 'citrus_processing', 'citrus_processing'
    if re.search(r'\b(?:engelli genç\w*|bağimsiz yaşam|istihdam desteği)\b',title):
        return 'education', 'adult_workspace'
    if 'park alani' in title and ('araç' in title or category=='transport'):
        return 'parking','parking'
    if re.search(r'\bpark(?:i|lar|lari)?\b',title) and 'otopark' not in title:
        return 'public_park','public_park'
    for pattern, photo, generated in rules:
        if re.search(pattern, title):
            # An advance notice cannot prove a photograph of an incident.
            if photo in ('flood', 'meeting', 'hiking', 'football', 'traffic', 'roadworks') and re.search(
                    r'\b(?:uyari\w*|beklen\w*|risk\w*|iptal\w*|planlan\w*|yarin|yapilacak|gerçekleşecek|önlenecek)\b', title):
                photo = None
            return photo, generated
    fallback = {
        'education': ('education', 'education'), 'health': ('health_workspace', 'health_workspace'),
        'public': ('public_service', 'public_service'), 'municipality': ('public_service', 'public_service'),
        'weather': ('weather_sky', 'weather_sky'), 'tourism': ('landscape', 'travel_gear'),
        'food': ('food', 'food'), 'market': ('market', 'market'),
        'concert': ('concert', 'concert'), 'theatre': ('theatre', 'theatre'),
        'cinema': ('cinema', 'cinema'), 'festival': ('festival', 'festival'),
        'culture': ('culture', 'culture'),
    }
    return fallback.get(category, (None, None))
