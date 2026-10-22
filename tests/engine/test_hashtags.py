import re
from copy import deepcopy

import pytest

from news_engine.editor import caption, caption_with_hashtags, digest_hashtags, hashtags, headline
from news_engine.schedule import prepare


def test_theatre_tags_are_lowercase_local_and_do_not_invent_a_genre(event):
    event.update(title="Hafifletici Sebepler", category="theatre",
                 location="Yalvaç Belediyesi Atatürk Kültür Merkezi", description="Tiyatro oyunu duyurusu.")
    original = deepcopy(event)
    assert hashtags(event) == ["#yalvac", "#tiyatro", "#tiyatrooyunu", "#etkinlik", "#ispartaofficial"]
    assert "#komedi" not in hashtags(event)
    assert event == original


def test_location_precedes_other_real_mentions_and_source_hashtags_do_not_supply_a_location(event):
    event.update(title="Yalvaç'da konser #ISPARTA #Keşfet", category="concert",
                 location="Keçiborlu Atabey", description="Gelendost'deki dinleyicilere duyuru. #viral #fyp")
    tags = hashtags(event)
    assert tags == ["#keciborlu", "#atabey", "#konser", "#canlimuzik", "#ispartaofficial"]
    content = caption(event, headline(event, "announcement"))
    assert content.endswith(" ".join(tags))
    assert "#ISPARTA" not in content
    assert "#Keşfet" not in content
    assert "#viral" not in content
    assert "#fyp" not in content


@pytest.mark.parametrize("place,expected", [
    ("Eğirdir", "#egirdir"), ("Senirkent", "#senirkent"), ("Keçiborlu", "#keciborlu"),
    ("Gelendost", "#gelendost"), ("Isparta", "#isparta"),
])
def test_turkish_location_names_use_readable_lowercase_ascii(event, place, expected):
    event.update(location=place, title="Etkinlik", description="", category="event")
    assert hashtags(event)[0] == expected
    assert all(re.fullmatch(r"#[a-z0-9_]+", tag) for tag in hashtags(event))


def test_a_place_inside_a_larger_word_is_not_a_location(event):
    event.update(title="Buralarda kültür", location=None, description="Atabeyli tekne", category="culture")
    assert not any(tag in hashtags(event) for tag in ("#yalvac", "#atabey"))


def test_source_links_and_attached_campaign_tags_do_not_supply_topic_or_place(event):
    event.update(title="Duyuru#FYP", location="Yalvaç", category="transport",
                 description="Ayrıntı: https://example.org/isparta/yol-calismasi#program #Atabey")
    assert hashtags(event) == ["#yalvac", "#ulasim", "#trafik", "#kamuduyurusu", "#ispartaofficial"]
    content = caption(event, headline(event, "announcement"))
    assert "#FYP" not in content and "#Atabey" not in content
    assert "https://example.org/isparta/yol-calismasi#program" in content


def test_traffic_roadwork_tag_requires_an_actual_roadwork_cue(event):
    event.update(kind="news", title="Isparta ulaşım duyurusu", category="transport",
                 location="Isparta", description="Otobüs güzergâhı güncellendi.")
    assert hashtags(event) == ["#isparta", "#ulasim", "#trafik", "#yerelhaber", "#ispartaofficial"]
    event["description"] = "Yol çalışması nedeniyle trafik düzenlemesi yapıldı."
    assert hashtags(event) == ["#isparta", "#ulasim", "#yolcalismasi", "#trafik", "#ispartaofficial"]


def test_news_about_a_theatre_building_does_not_promise_a_performance(event):
    event.update(kind="news", category="theatre", title="Yalvaç tiyatro salonu yenilendi",
                 location="Yalvaç", description="Bina yenileme çalışmaları tamamlandı.")
    assert "#tiyatro" in hashtags(event)
    assert "#tiyatrooyunu" not in hashtags(event)


def test_caption_reserves_complete_source_url_and_hashtags_before_trimming(event):
    event.update(title="Yalvaç " + "duyuru " * 500, location="Yalvaç", description="Açıklama " * 300,
                 category="theatre", source_name="Isparta Art", url="https://www.isparta.art/etkinlik/123#program")
    content = caption(event, headline(event, "announcement"))
    assert len(content) <= 2200
    assert "Kaynak: Isparta Art\n" + event["url"] in content
    assert content.endswith("#yalvac #tiyatro #tiyatrooyunu #etkinlik #ispartaofficial")
    assert "#program" in content  # Preserve the canonical source URL fragment.


def test_caption_formatter_never_outputs_partial_or_invalid_footer_tags():
    content = caption_with_hashtags("Uzun açıklama " * 300,
                                    ["#yalvac", "#konser", "#CANLIMUZIK", "#yalvac", "#ispartaofficial"])
    assert len(content) <= 2200
    assert content.endswith("#yalvac #konser #ispartaofficial")


def test_calendar_tags_include_selected_category_diversity_without_repetition(event):
    theatre = {**event, "category": "theatre", "location": "Yalvaç", "title": "Oyun", "description": ""}
    festival = {**event, "category": "festival", "location": "Senirkent Isparta", "title": "Festival", "description": ""}
    assert digest_hashtags([theatre, festival]) == ["#yalvac", "#senirkent", "#tiyatro", "#festival", "#ispartaofficial"]


def test_weekly_and_monthly_caption_have_contextual_footer(store, event, at):
    event.update(title="Hafifletici Sebepler", category="theatre", location="Yalvaç", description="")
    store.upsert(event, at.isoformat())
    prepare(store, at)
    for post in store.posts():
        if post["kind"] in ("weekly", "monthly"):
            assert post["caption"].endswith("#yalvac #tiyatro #tiyatrooyunu #etkinlik #ispartaofficial")
            assert len(post["caption"]) <= 2200

