from dataclasses import replace
from pathlib import Path

from PIL import Image
import pytest

from isparta.editorial_cards import CardLayoutError, EventCard, render_event


@pytest.fixture
def event(tmp_path):
    photo = tmp_path / 'photo.png'
    Image.new('RGB', (900, 900), '#4a343d').save(photo)
    return EventCard('Kampüste canlı müzik', 'Konser', '23 Ekim 2026 · 20.00',
                     'Isparta Kültür Merkezi', 'Açıklanmadı',
                     'Katılım ve kayıt koşulları açıklamada.', photo)


@pytest.mark.parametrize('story', [False, True])
def test_formats_keep_all_facts_and_text_fields_separate(event, tmp_path, story):
    target = tmp_path / 'card.jpg'
    report = render_event(event, target, story=story)
    with Image.open(target) as card:
        assert card.size == (1080, 1920 if story else 1350)
    fields = {v['role']: v for v in report['fields']}
    assert fields['title']['text'] == event.title
    assert fields['date_time']['text'] == event.date_time
    assert fields['venue']['text'] == event.venue
    assert fields['fee']['text'] == 'Açıklanmadı'
    assert fields['caption_note']['text'] == 'Detaylar açıklamada.'
    assert all('…' not in v['text'] for v in report['fields'])
    for role in ('title', 'date_time', 'venue', 'fee', 'access', 'caption_note'):
        a = fields[role]['box']
        for other in ('title', 'date_time', 'venue', 'fee', 'access', 'caption_note'):
            if role == other:
                continue
            b = fields[other]['box']
            assert max(a[0], b[0]) >= min(a[2], b[2]) or max(a[1], b[1]) >= min(a[3], b[3])


@pytest.mark.parametrize('field,value', [
    ('title', 'A' * 400), ('venue', 'çok uzun mekân adı ' * 20),
    ('date_time', '23 Ekim 2026 20.00 ' * 12),
    ('fee', 'çok uzun ücret ve kayıt koşulu ' * 16),
    ('access', 'katılım koşulu ' * 30), ('title', 'Konser 🙏'),
])
def test_unreadable_essential_fact_or_unsupported_glyph_withholds_card(event, tmp_path, field, value):
    target = tmp_path / 'held.jpg'
    with pytest.raises(CardLayoutError):
        render_event(replace(event, **{field: value}), target)
    assert not target.exists()


def test_event_type_uses_turkish_capital_i(event, tmp_path):
    report = render_event(replace(event, category='Tiyatro'), tmp_path / 'theatre.jpg')
    assert next(f['text'] for f in report['fields'] if f['role'] == 'category') == 'TİYATRO'


def test_source_poster_complete_frame_is_retained(event, tmp_path):
    # A wide card must keep a square poster's corner information and its colors.
    poster = Image.new('RGB', (600, 600), 'white')
    for x, y, color in [(0, 0, 'red'), (550, 0, 'green'), (0, 550, 'blue'), (550, 550, 'black')]:
        poster.paste(color, (x, y, x + 50, y + 50))
    path = tmp_path / 'poster.png'
    poster.save(path)
    target = tmp_path / 'poster-card.jpg'
    render_event(replace(event, image=path), target)
    with Image.open(target) as result:
        # 600-square -> 420-square centered at x=330, y=140.
        assert result.getpixel((340, 150))[0] > 220
        green = result.getpixel((740, 150))
        assert green[1] > 90 and green[0] < 40
        assert result.getpixel((340, 550))[2] > 220
        assert max(result.getpixel((740, 550))) < 40


def test_no_picture_fallback_has_no_unrelated_scene(event, tmp_path):
    report = render_event(replace(event, image=None), tmp_path / 'information.jpg')
    assert next(f['text'] for f in report['fields'] if f['role'] == 'date_time') == event.date_time


def test_preview_is_explicit_without_invented_real_performance(event, tmp_path):
    report = render_event(event, tmp_path / 'preview.jpg', preview=True)
    assert report['preview'] is True
    assert any('GERÇEK ETKİNLİK DUYURUSU DEĞİLDİR' in f['text'] for f in report['fields'])
