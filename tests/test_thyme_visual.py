import os
from pathlib import Path
import pytest
from news_engine.source_photos import news_subject,cleaned_photo
from news_engine.visual_subject import subject
from news_engine.visual_match import validate_news_photo,validate_headline_photo,MatchRejected

@pytest.mark.parametrize('title',[
    'Sütçüler’in Endemik Kekiği Altın Değerinde',
    'Sütçüler kekiğinin hasadı başladı',
    'Kekik üretimi ilçeye değer katıyor',
])
def test_explicit_thyme_crop_has_specific_visual(title):
    item={'kind':'news','category':'news','title':title}
    assert news_subject(item)==subject(item)=='thyme_herbs'

@pytest.mark.parametrize('title',[
    'Lavanta hasadı başladı',
    'Kekik restoranında yeni menü',
    'Sütçüler’de yeni yol açıldı',
    'Başkan üreticilerle bir araya geldi',
])
def test_other_plants_venues_and_meetings_never_get_thyme(title):
    item={'kind':'news','category':'news','title':title}
    assert news_subject(item)!='thyme_herbs'
    assert subject(item)!='thyme_herbs'

