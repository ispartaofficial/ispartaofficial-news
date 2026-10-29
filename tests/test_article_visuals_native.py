"""Actual OCR and pinned model: article photos and described scenes."""
import json
import os
from pathlib import Path

import pytest

from news_engine.editorial_stock import DIRECTORY
from news_engine.image_safety import IllustrationTextRejected, ocr_available
from news_engine.source_photos import cleaned_photo
from news_engine.visual_match import LABELS, MatchRejected, validate_article_photo, validate_described

FIXTURES = Path(__file__).parent / 'fixtures/visual-followup'
# The calendar scene has its own reviewed-crop check instead of a model label.
ROWS = [row for row in json.loads((DIRECTORY / 'manifest.json').read_text())['scenes']
        if row['subject'] in LABELS and row['subject'] != 'event_calendar']
native = pytest.mark.skipif(os.getenv('RUN_VISUAL_NATIVE') != 'true', reason='Pinned model and native OCR job')


@native
@pytest.mark.parametrize('name', ['official-visit-exif-zero.jpg', 'thyme-article.jpg'])
def test_headline_collage_is_not_an_article_photo(name):
    assert ocr_available()
    # Same order as the source-photo pipeline: metadata-free, bounded pixels first.
    data = cleaned_photo((FIXTURES / name).read_bytes())
    with pytest.raises((IllustrationTextRejected, MatchRejected)):
        validate_article_photo(data)


@native
@pytest.mark.parametrize('row', ROWS, ids=lambda r: r['subject'])
def test_text_free_scene_matches_its_own_description_only(row):
    data = (DIRECTORY / row['file']).read_bytes()
    assert validate_described(data, LABELS[row['subject']])['subject'] == LABELS[row['subject']]
    with pytest.raises(MatchRejected):
        validate_described(data, 'a photograph of a bowl of lentil soup on a kitchen table')
