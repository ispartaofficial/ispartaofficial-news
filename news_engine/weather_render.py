"""Isparta weather: precise readable labels over a repository-owned stock scene."""
from datetime import date
from pathlib import Path
import math
import unicodedata

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .brand import logo_path
from .render import font, wrap
from .text_quality import ensure_glyphs
from .weather_data import asset_id, validate_forecast
from .weather_copy import display_condition

SCALE = 2
BACKGROUND = Path(__file__).resolve().parents[1] / 'isparta/assets/weather-background-v1.png'
PLUM, ACCENT, MUTED = '#67143f', '#a52d6d', '#636973'
WEEKDAYS = ('Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar')
MONTHS = ('Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık')


def condition_layout(forecast):
    text = display_condition(forecast)
    measure = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    for size in (44, 40, 36):
        face = font(size * SCALE, True)
        ensure_glyphs(text, face)
        lines = wrap(measure, text, face, 880 * SCALE)
        if len(lines) <= 3:
            return size, lines
    raise ValueError('Complete weather condition exceeds readable story budget')


def weather_kind(condition):
    text = unicodedata.normalize('NFC', condition).casefold()
    if 'gürült' in text or 'fırtına' in text:
        return 'storm'
    if 'kar' in text:
        return 'snow'
    if any(word in text for word in ('yağmur', 'sağanak', 'çisenti')):
        return 'rain'
    if 'sis' in text or 'pus' in text:
        return 'fog'
    if 'rüzg' in text:
        return 'wind'
    if 'bulut' in text:
        return 'partly' if any(word in text for word in ('az', 'parçalı')) else 'cloudy'
    return 'sunny' if any(word in text for word in ('açık', 'güneş')) else 'neutral'


def icon(condition):
    """Small deterministic weather symbol; never a claim about hourly timing."""
    size = 330 * SCALE
    layer = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    kind = weather_kind(condition)
    def ellipse(box, fill):
        ImageDraw.Draw(layer).ellipse(tuple(int(v * SCALE) for v in box), fill=fill)
    if kind in ('sunny', 'partly'):
        for radius in range(81, 0, -1):
            ratio = radius / 81
            color = (255, int(221 - 52 * ratio), int(112 - 70 * ratio), 255)
            cx, cy = (165, 155) if kind == 'sunny' else (133, 121)
            ellipse((cx-radius, cy-radius, cx+radius, cy+radius), color)
        glow = Image.new('RGBA', layer.size)
        gd = ImageDraw.Draw(glow)
        gd.ellipse((92*SCALE, 50*SCALE, 140*SCALE, 88*SCALE), fill=(255,255,255,100))
        layer = Image.alpha_composite(layer, glow.filter(ImageFilter.GaussianBlur(12*SCALE)))
    if kind != 'sunny':
        cloud = Image.new('RGBA', layer.size)
        mask = Image.new('L', layer.size)
        md = ImageDraw.Draw(mask)
        for box in ((55,150,270,230),(68,120,163,215),(124,98,238,221),(196,143,290,230)):
            md.ellipse(tuple(v*SCALE for v in box), fill=255)
        gradient = Image.new('RGBA', layer.size)
        gd = ImageDraw.Draw(gradient)
        for y in range(size):
            shade = int(252 - 52 * min(1, max(0, (y/SCALE-100)/140)))
            if kind == 'storm':
                shade -= 66
            gd.line((0,y,size,y), fill=(shade, min(255,shade+3), min(255,shade+10),255))
        cloud.paste(gradient, mask=mask)
        layer = Image.alpha_composite(layer, cloud)
        d = ImageDraw.Draw(layer)
        if kind in ('rain', 'storm'):
            for x in (105,172,239):
                d.line((x*SCALE,250*SCALE,(x-12)*SCALE,281*SCALE),fill='#69a8d1',width=9*SCALE)
        if kind == 'snow':
            for x in (105,172,239):
                for angle in (0,math.pi/3,2*math.pi/3):
                    dx,dy=11*math.cos(angle),11*math.sin(angle)
                    d.line(((x-dx)*SCALE,(263-dy)*SCALE,(x+dx)*SCALE,(263+dy)*SCALE),fill='#7aaecb',width=3*SCALE)
        if kind in ('fog','wind'):
            for y,x in ((251,77),(272,104),(292,64)):
                d.line((x*SCALE,y*SCALE,(x+158)*SCALE,y*SCALE),fill='#93a4ae',width=5*SCALE)
    shadow = Image.new('RGBA', layer.size)
    shadow.putalpha(layer.getchannel('A').filter(ImageFilter.GaussianBlur(11*SCALE)).point(lambda v:int(v*.16)))
    result = Image.new('RGBA', layer.size)
    result.alpha_composite(shadow, dest=(3*SCALE,8*SCALE))
    result.alpha_composite(layer)
    return result


def render_weather(forecast, public_dir, *, preview=False):
    validate_forecast(forecast)
    description = display_condition(forecast)
    condition_size, lines = condition_layout(forecast)
    with Image.open(BACKGROUND) as src:
        canvas = ImageOps.fit(src.convert('RGB'), (1080*SCALE,1920*SCALE), method=Image.Resampling.LANCZOS).convert('RGBA')
    with Image.open(logo_path()) as src:
        logo = ImageOps.fit(src.convert('RGB'),(150*SCALE,150*SCALE),method=Image.Resampling.LANCZOS)
    mask=Image.new('L',logo.size)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,logo.width-1,logo.height-1),radius=35*SCALE,fill=255)
    canvas.paste(logo,(838*SCALE,156*SCALE),mask)
    draw = ImageDraw.Draw(canvas)
    def text(x,y,value,size,color=PLUM,bold=False,anchor='lt'):
        face=font(size*SCALE,bold)
        ensure_glyphs(value,face)
        draw.text((x*SCALE,y*SCALE),value,font=face,fill=color,anchor=anchor)
    text(92,180,'Günaydın Isparta',45,ACCENT,True)
    text(92,253,'Günün havası',65,PLUM,True)
    day=date.fromisoformat(forecast['date'])
    text(92,354,f'{day.day} {MONTHS[day.month-1]} {day.year} · {WEEKDAYS[day.weekday()]}',30,MUTED)
    draw.rounded_rectangle((92*SCALE,415*SCALE,180*SCALE,421*SCALE),radius=3*SCALE,fill=ACCENT)
    canvas.alpha_composite(icon(description),(375*SCALE,441*SCALE))
    draw=ImageDraw.Draw(canvas)
    y=795
    for line in lines:
        text(540,y,line,condition_size,PLUM,True,'mt')
        y+=condition_size+13
    # The main number is explicitly a daily high/low, never a current reading.
    high=forecast['high']
    temp=high if high is not None else forecast['low']
    y+=26
    text(540,y,f'{temp}°',170,PLUM,True,'mt')
    y+=192
    text(540,y,'Gündüz en yüksek' if high is not None else 'Gece en düşük',29,MUTED,False,'mt')
    if high is not None and forecast['low'] is not None:
        text(540,y+54,f"Gece {forecast['low']}°",32,ACCENT,True,'mt')
    text(92,1740,'@ispartaofficial',27,PLUM,True)
    if preview:
        text(92,1813,'ÖRNEK TASARIM · PAYLAŞILMADI',22,MUTED)
    relative=f'media/{asset_id(forecast)}/story-1.jpg'
    target=Path(public_dir)/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    canvas.convert('RGB').resize((1080,1920),Image.Resampling.LANCZOS).save(target,'JPEG',quality=95,subsampling=0)
    return relative
