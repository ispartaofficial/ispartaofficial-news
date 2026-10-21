"""Isparta's deterministic card preview; not a publication or verification engine.

Text fields are separate and measured. Essential facts cannot be ellipsized.
The existing logo is placed intact; no generated image supplies typography.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import unicodedata

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PRIMARY, ACCENT, PAPER = '#68103f', '#a52e73', '#fcf8fa'
INK, MUTED, LINE = '#281e27', '#6d5867', '#ead9e2'


class CardLayoutError(ValueError):
    pass


def font(size, bold=False):
    for path in (
        f'/usr/share/fonts/truetype/dejavu/DejaVuSans{"-Bold" if bold else ""}.ttf',
        'C:/Windows/Fonts/segoeuib.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf',
    ):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    raise CardLayoutError('A reviewed Turkish-capable font is required')


def clean(value):
    if not isinstance(value, str) or not value.strip():
        raise CardLayoutError('Required card field is empty')
    value = unicodedata.normalize('NFC', value).strip()
    if any(unicodedata.category(c) in ('Cf', 'Cs', 'So') or (unicodedata.category(c) == 'Cc' and c != '\n') for c in value):
        raise CardLayoutError('Unsupported display characters')
    return value


class Fields:
    def __init__(self, draw):
        self.draw = draw
        self.items = []

    def block(self, value, box, sizes, role, *, bold=False, color=INK, lines_max=4):
        value = clean(value)
        for size in sizes:
            face = font(size, bold)
            lines = []
            fits = True
            for paragraph in value.splitlines():
                current = ''
                for word in paragraph.split():
                    if self.draw.textlength(word, font=face) > box[2] - box[0] - 4:
                        fits = False
                        break
                    trial = (current + ' ' + word).strip()
                    if self.draw.textlength(trial, font=face) <= box[2] - box[0] - 4:
                        current = trial
                    else:
                        lines.append(current)
                        current = word
                if current:
                    lines.append(current)
            step = size + 12
            if fits and len(lines) <= lines_max and len(lines) * step <= box[3] - box[1]:
                break
        else:
            raise CardLayoutError(f'Essential {role} does not fit')
        bounds = []
        for i, line in enumerate(lines):
            x, y = box[0], box[1] + i * step
            b = self.draw.textbbox((x, y), line, font=face, anchor='lt')
            x += max(0, box[0] - b[0])
            b = self.draw.textbbox((x, y), line, font=face, anchor='lt')
            if b[0] < box[0] or b[1] < box[1] or b[2] > box[2] or b[3] > box[3]:
                raise CardLayoutError(f'{role} ink exceeds its field')
            for old in self.items:
                for other in old['bounds']:
                    if max(b[0], other[0]) < min(b[2], other[2]) and max(b[1], other[1]) < min(b[3], other[3]):
                        raise CardLayoutError('Text fields overlap')
            self.draw.text((x, y), line, font=face, fill=color, anchor='lt')
            bounds.append(b)
        self.items.append({'role': role, 'text': value, 'font_size': size, 'box': box, 'bounds': bounds})


@dataclass(frozen=True)
class EventCard:
    title: str
    category: str
    date_time: str
    venue: str
    fee: str
    access: str
    image: Path | None = None


def render_event(card: EventCard, target: Path, *, story=False, preview=False, logo=None):
    """Render preverified text; caller must separately verify the actual event."""
    width, height = 1080, 1920 if story else 1350
    top = 220 if story else 0
    image = Image.new('RGB', (width, height), PAPER)
    draw = ImageDraw.Draw(image)
    fields = Fields(draw)
    brand = json.loads((ROOT / 'config/brand.json').read_text(encoding='utf-8'))
    path = Path(logo) if logo else ROOT / brand['logo']
    # Crop only the surrounding gradient whitespace, keeping the entire original
    # wordmark and rose visible. The source logo asset itself remains unchanged.
    with Image.open(path) as source:
        if source.size != (1080, 1080):
            raise CardLayoutError('Brand asset must be the reviewed original')
        wordmark = source.convert('RGB').crop((150, 300, 950, 720))
        wordmark = wordmark.resize((266, 140), Image.Resampling.LANCZOS)
    image.paste(wordmark, (0, top))
    fields.block('ŞEHİR / KAMPÜS / KÜLTÜR', (350, top + 38, 1016, top + 81),
                 (27,), 'masthead', bold=True, color=PRIMARY, lines_max=1)
    fields.block('TASARIM ÖRNEĞİ' if preview else 'ISPARTA OFFICIAL',
                 (350, top + 82, 1016, top + 120), (22,), 'edition', color=MUTED, lines_max=1)
    photo_top, photo_bottom = top + 140, top + 560
    if card.image:
        # A poster's edges can contain its date, access or price. Never crop them
        # away merely to fill the image slot; keep the complete source frame.
        with Image.open(card.image) as source:
            photo = ImageOps.pad(source.convert('RGB'), (width, photo_bottom - photo_top),
                                 method=Image.Resampling.LANCZOS, color=PRIMARY)
        image.paste(photo, (0, photo_top))
    else:
        # No arbitrary stock scene is substituted. This compact information-card
        # layout reserves the space for the literal facts instead.
        photo_bottom = top + 170
    y = photo_bottom
    draw.rectangle((0, y, width, y + 6), fill=ACCENT)
    tag = clean(card.category).translate(str.maketrans({'i': 'İ', 'ı': 'I'})).upper()
    face = font(24, True)
    tag_width = int(draw.textlength(tag, font=face)) + 36
    if tag_width > 952:
        raise CardLayoutError('Category does not fit')
    draw.rounded_rectangle((64, y + 32, 64 + tag_width, y + 73), radius=8, fill=ACCENT)
    fields.block(tag, (82, y + 37, 64 + tag_width, y + 75), (24,), 'category', bold=True, color='white', lines_max=1)
    fields.block(card.title, (64, y + 100, 1016, y + 282),
                 (82, 74, 68, 62, 56, 50, 44), 'title', bold=True, color=PRIMARY, lines_max=3)
    draw.rounded_rectangle((64, y + 300, 1016, y + 384), radius=16, fill='#f2e5ed')
    fields.block(card.date_time, (88, y + 316, 992, y + 382),
                 (38, 34, 30), 'date_time', bold=True, color=PRIMARY, lines_max=1)
    fields.block('MEKÂN', (64, y + 415, 664, y + 455), (23,), 'venue_label', bold=True, color=MUTED, lines_max=1)
    fields.block(card.venue, (64, y + 460, 660, y + 575),
                 (36, 34, 30, 28), 'venue', bold=True, lines_max=2)
    fields.block('ÜCRET', (714, y + 415, 1016, y + 455), (23,), 'fee_label', bold=True, color=MUTED, lines_max=1)
    fields.block(card.fee, (714, y + 460, 1016, y + 575),
                 (36, 34, 30, 28), 'fee', bold=True, lines_max=2)
    fields.block(card.access, (64, y + 585, 1016, y + 650),
                 (28, 26), 'access', color=MUTED, lines_max=1)
    fields.block('Detaylar açıklamada.', (64, y + 661, 1016, y + 707),
                 (28,), 'caption_note', bold=True, color=ACCENT, lines_max=1)
    draw.line((64, y + 722, 1016, y + 722), fill=LINE, width=2)
    fields.block(brand['handle'], (64, y + 739, 1016, y + 777), (23,), 'handle', bold=True, color=PRIMARY, lines_max=1)
    if y + 777 > (1680 if story else height):
        raise CardLayoutError('Content exceeds format safe area')
    if preview:
        # This can never be mistaken for a specific future performance.
        fields.block('ÖRNEK YERLEŞİM • GERÇEK ETKİNLİK DUYURUSU DEĞİLDİR',
                     (64, 1790 if story else 1321, 1016, 1832 if story else 1348),
                     (15,), 'preview_disclaimer', color=MUTED, lines_max=1)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, 'JPEG', quality=95, subsampling=0)
    return {'version': brand['card_version'], 'brand_version': brand['version'], 'preview': preview,
            'size': image.size, 'fields': fields.items, 'image': str(target)}
