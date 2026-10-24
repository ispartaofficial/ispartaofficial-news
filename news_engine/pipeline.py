from __future__ import annotations

import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
import requests
from datetime import datetime, timedelta
from pathlib import Path

from .collect import Fetcher, collect_source, network_error_kind
from .domain import now, parse_date
from .editor import ai_priority, verify
from .render import render_post
from .illustrations import Illustrator
from .media_caption import generated_image_caption
from .schedule import prepare
from .store import Store
from .timeliness import with_validity
from .security import ITEM_FIELDS, PUBLIC_ITEM_FIELDS, assert_no_secrets, contains_secret, public_url, validate_public


def source_error_code(exc: Exception) -> str:
    """Useful diagnostics without copying untrusted exception text or request data."""
    if isinstance(exc, requests.exceptions.SSLError):
        return 'source_tls_name_mismatch' if network_error_kind(exc) == 'tls_name_mismatch' else 'source_tls_failed'
    if isinstance(exc, requests.Timeout):
        return 'source_timeout'
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        code = exc.response.status_code
        if type(code) is int and 100 <= code <= 599:
            return 'source_http_' + str(code)
    if isinstance(exc, requests.ConnectionError):
        return 'source_dns_failed' if network_error_kind(exc) == 'dns_failed' else 'source_connection_failed'
    if isinstance(exc, (ET.ParseError, json.JSONDecodeError)):
        return 'source_parse_failed'
    if isinstance(exc, ValueError) and str(exc) == 'robots.txt disallows this path':
        return 'source_robots_denied'
    return 'collection_failed'


def export(store: Store, public_dir: Path, sources: list[dict], at: datetime, demo=False, *, instagram_manifest=None) -> dict:
    # Build a clean, validated staging directory. Never carry arbitrary old files
    # (.env, a database, logs or stale private media) into the Pages artifact.
    from .source_discovery import active_sources
    sources = active_sources(store, sources)
    root = Path(__file__).resolve().parents[1]
    resolved = public_dir.resolve()
    protected = [root, root / "site", root / "news_engine", root / "isparta", root / "config", root / "tests", root / ".git", root / ".github", root / "docs", store.path]
    if public_dir.is_symlink() or any(resolved == p or resolved in p.parents for p in protected) or any(p != root and p in resolved.parents for p in protected):
        raise ValueError("Public output must be an isolated directory")
    public_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pages-staging-", dir=public_dir.parent) as directory:
        staging = Path(directory) / "public"
        result = _export(store, staging, sources, at, demo, Path(directory) / 'illustrations', instagram_manifest=instagram_manifest)
        validate_public(staging)
        if public_dir.exists():
            shutil.rmtree(public_dir)
        shutil.move(str(staging), public_dir)
    return result


def _export(store: Store, public_dir: Path, sources: list[dict], at: datetime, demo=False, illustration_dir: Path | None = None, *, instagram_manifest=None) -> dict:
    public_dir.mkdir(parents=True)
    root = Path(__file__).resolve().parents[1]
    for filename in ("index.html", "style.css", "app.js"):
        shutil.copy2(root / "site" / filename, public_dir / filename)
    from .brand import VERSION as BRAND_VERSION, PUBLIC_ASSET, logo_path
    shutil.copy2(logo_path(), public_dir / PUBLIC_ASSET)
    source_map = {s["id"]: s for s in sources}
    safe_items = [i for i in store.items() if verify({k: v for k, v in i.items() if k in ITEM_FIELDS}, source_map.get(i["source_id"], {}), at) is None]
    safe_urls = {url for i in safe_items for url in i.get("sources", []) + [i["url"]]}
    posts = [p for p in store.posts() if not contains_secret(p) and set(p["source_urls"]) <= safe_urls]
    # data.json is also the publisher's asset manifest. Archive/story rows must
    # not consume a display limit and hide an older, still-due parent. Retain
    # every safe active parent, including frozen claims and blocked-source rows.
    parents = [p for p in posts if not p.get("publish_format")
               and p["status"] not in ("superseded", "expired")]
    assets = {}
    illustrator = Illustrator(store, at, illustration_dir or public_dir.parent / 'illustrations', demo=demo)
    from .source_photos import SourcePhotos
    from .instagram_source_photos import consume_photos
    instagram_photos,instagram_checks=consume_photos(instagram_manifest,sources,at)
    photos=SourcePhotos(store,at,(illustration_dir or public_dir.parent/'illustrations')/'source-photos',sources,demo=demo,
                        instagram_photos=instagram_photos,instagram_checks=instagram_checks)
    item_map = {i['id']: i for i in safe_items}
    photos.prune(set(item_map))
    illustrator.prune(set(item_map))
    # Public output always rebuilt; removed/sensitive/superseded images cannot linger.
    shutil.rmtree(public_dir / "media", ignore_errors=True)
    from .selection import prioritize
    # Spend the unchanged two-attempt budgets on the next editorial candidates,
    # before distant/old queue entries. Frozen cards retain their stored bytes.
    pending = [p for p in parents if p['status']=='prepared']
    ordered = prioritize(store,pending,at) + sorted(
        (p for p in parents if p['status']!='prepared'),key=lambda p:p['due_at'])
    for post in ordered:
        if post["status"] in ("prepared", "published", "publishing", "uncertain"):
            if post['status']=='prepared':
                from .quality import publication_copy_reason
                if reason := publication_copy_reason(post,item_map):
                    store.withhold(post['id'],reason,at.isoformat())
                    with store.db:
                        store.db.execute("UPDATE posts SET status='blocked_source' WHERE id=? AND status='prepared'",(post['id'],))
                    post['status']='blocked_source'
                    continue
                from .card_layout import prepare as prepare_card_layout
                prepare_card_layout(post)
                from .brand import prepare as prepare_brand
                prepare_brand(post)
            source_images = photos.for_post(post,item_map)
            illustrations = illustrator.for_post(post,item_map,skip_indices=source_images)
            illustrations.update(source_images)
            if post["status"] == "prepared":
                # Research records actual assignments. The publisher renders
                # locally with generation disabled, but uses deployed Pages
                # assets. Clean legacy caption notes only before a claim.
                generated = bool(illustrations) if illustrator.enabled else bool(post.get("illustration_keys"))
                post["caption"] = generated_image_caption(post["caption"], generated)
                rows = store.rows("SELECT payload FROM posts WHERE id=? AND status='prepared'", (post["id"],))
                if rows:
                    payload = json.loads(rows[0]["payload"])
                    payload["caption"] = post["caption"]
                    with store.db:
                        store.db.execute("UPDATE posts SET payload=? WHERE id=? AND status='prepared'",
                                         (json.dumps(payload, ensure_ascii=False), post["id"]))
                from .visual_gate import review, valid_review
                # Research checks real image pixels. A publisher without the
                # vision runtime retains that proof and consumes deployed bytes.
                if illustrator.enabled or photos.enabled or not valid_review(post):
                    post['visual_review'] = review(post, illustrations, item_map)
            from .text_quality import TextRenderError
            try:
                assets[post["id"]] = render_post(post, public_dir, illustrations)
            except TextRenderError:
                # A bad draft cannot abort research for every other source or
                # become an approved image with tofu/truncated heading.
                if post['status'] != 'prepared':
                    raise
                store.withhold(post['id'], 'unrenderable_card_text', at.isoformat())
                with store.db:
                    store.db.execute("UPDATE posts SET status='blocked_source' WHERE id=? AND status='prepared'", (post['id'],))
                post['status']='blocked_source'
                continue
            if post['status'] == 'prepared':
                from .visual_gate import record_assets
                # A no-generation publisher must not replace a previous photo
                # proof with hashes of its local text-only render.
                if illustrator.enabled or photos.enabled or not post['visual_review']['assets']:
                    record_assets(post, assets[post['id']], public_dir)
                with store.db:
                    store.db.execute("UPDATE posts SET payload=? WHERE id=? AND status='prepared'",
                                     (json.dumps({k:v for k,v in post.items() if k not in ('status','container_id','media_id')}, ensure_ascii=False), post['id']))
    illustrator.prune(set(item_map))
    from .schedule import blocked_sources, source_current
    failed = blocked_sources(store)
    public_items = [{**{k: v for k, v in i.items() if k in PUBLIC_ITEM_FIELDS or k in ("id", "revision", "first_seen", "last_seen")}, "source_current": source_current(i, at, failed)} for i in safe_items]
    events = sorted((e for e in public_items if e["kind"] == "event" and parse_date(e["start"]).date() >= at.date() - timedelta(days=1)), key=lambda e: e["start"])
    news = sorted((i for i in public_items if i["kind"] == "news"), key=lambda i: i["published_at"], reverse=True)
    public_posts = [{"id": p["id"], "kind": p["kind"], "title": p["title"], "due_at": p["due_at"], "status": p["status"],
                     "caption": p["caption"], "assets": assets.get(p["id"], {}), "category": p["category"],
                     **({'visual_review':p['visual_review']} if 'visual_review' in p else {})} for p in parents]
    snapshot = {"schema_version": 1, "generated_at": at.isoformat(), "demo": demo,
                "brand": {"version": BRAND_VERSION, "logo": PUBLIC_ASSET},
                "publishing_enabled": (os.getenv("PUBLICATION_AUTHORIZED") == "true" and
                    json.loads((Path(__file__).resolve().parents[1]/"config/runtime.json").read_text(encoding="utf-8")).get("publishing_enabled") is True),
                "illustrations": illustrator.stats,
                "news": news, "events": events, "posts": public_posts,
                "withheld_count": store.db.execute("SELECT COUNT(*) FROM withheld").fetchone()[0],
                "sources": [public_source(s) for s in sources], "source_photos":photos.stats,
                "candidate_count": store.db.execute("SELECT COUNT(*) FROM candidates").fetchone()[0],
                "source_health": store.rows('SELECT * FROM source_health ORDER BY source_id'),
                "runs": [{**r, "errors": json.loads(r["errors"])} for r in store.rows("SELECT * FROM runs ORDER BY id DESC LIMIT 20")]}
    catalogue_path = Path(__file__).resolve().parents[1] / 'config/source_catalog.json'
    from .operations import summary
    snapshot['operations'] = summary(store, at)
    from .factory import summary as factory_summary
    snapshot['factory'] = factory_summary(store, at)
    if not demo:
        from .weather import export_weather
        snapshot['weather_story'] = export_weather(store, public_dir, at)
        from .pharmacy import export as export_pharmacy
        snapshot['pharmacy_story'] = export_pharmacy(store, public_dir, at)
    if catalogue_path.exists():
        from .source_catalog import public_catalog
        catalogue = json.loads(catalogue_path.read_text(encoding='utf-8'))
        # A crawl can take several minutes after its reference/start time.
        # Evaluate live health at export time, not against that older start.
        snapshot['source_catalog'] = public_catalog(catalogue, sources, snapshot['source_health'], at if demo else now())
    assert_no_secrets(snapshot)
    (public_dir / "data.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    (public_dir / ".nojekyll").touch()
    export_calendar(events, public_dir)
    return assets


def public_source(source: dict) -> dict:
    from urllib.parse import urlsplit
    result = {k: source.get(k) for k in ("id", "name", "kind", "enabled", "trusted", "access")}
    display = source.get('display_url', source['url'])
    parts = urlsplit(display if public_url(display) else source['url'])
    result["url"] = f"https://{parts.hostname}{parts.path}"
    return result


def export_calendar(events: list[dict], public_dir: Path):
    def escape(value):
        return str(value or "").replace("\\", "\\\\").replace("\r", "").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")
    def fold(line):
        # RFC5545 folding is in octets, not Python code points (Turkish UTF-8).
        chunks, current = [], ""
        for char in line:
            if len((current + char).encode()) > 73:
                chunks.append(current)
                current = " "
            current += char
        chunks.append(current)
        return chunks
    from datetime import timezone
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Isparta Official//Etkinlik//TR", "CALSCALE:GREGORIAN"]
    for event in events:
        lines += ["BEGIN:VEVENT", f"UID:{event['id']}@ispartaofficial", "SEQUENCE:" + str(event["revision"]),
                  "DTSTAMP:" + parse_date(event["last_seen"]).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")]
        start = parse_date(event["start"])
        if event.get("time_known"):
            lines.append("DTSTART:" + start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        else:
            lines.append("DTSTART;VALUE=DATE:" + start.strftime("%Y%m%d"))
        lines += ["SUMMARY:" + escape(event["title"]), "LOCATION:" + escape(event.get("location")), "URL:" + event["url"],
                  "DESCRIPTION:" + escape("Son kaynak kontrolü: " + event["last_seen"] + (" · Kaynak yeniden doğrulanmalı" if not event.get("source_current", True) else "")),
                  "STATUS:" + ("CANCELLED" if event["status"] == "cancelled" else "TENTATIVE" if event["status"] == "postponed" or not event.get("source_current", True) else "CONFIRMED"), "END:VEVENT"]
    lines.append("END:VCALENDAR")
    (public_dir / "events.ics").write_bytes(("\r\n".join(chunk for line in lines for chunk in fold(line)) + "\r\n").encode())

