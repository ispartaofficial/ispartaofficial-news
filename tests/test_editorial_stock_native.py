"""Actual deployed stock files must pass OCR and all three rendered crops."""
import json
import os
import pytest

from news_engine.editorial_stock import DIRECTORY,reviewed_calendar
from news_engine.image_safety import ocr_available,validate_text_free_illustration
from news_engine.visual_match import validate_match

ROWS=json.loads((DIRECTORY/'manifest.json').read_text())['scenes']


@pytest.mark.skipif(os.getenv('RUN_VISUAL_NATIVE')!='true',reason='Pinned model and native OCR job')
@pytest.mark.parametrize('row',ROWS,ids=lambda r:r['subject'])
def test_every_reviewed_stock_scene_passes_actual_ocr_and_crop_checks(row):
    assert ocr_available()
    data=(DIRECTORY/row['file']).read_bytes()
    validate_text_free_illustration(data)
    if row['subject']=='event_calendar':
        assert reviewed_calendar(data,row['subject'])
    else:
        assert validate_match(data,row['subject'])['subject']==row['subject']
