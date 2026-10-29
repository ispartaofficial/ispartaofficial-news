"""Bounded recovery of pre-protection visual cache loss from this repo's archive.

Never resets state, changes claims, replaces a new claim's image, or publishes.
Only listed byte-identical historical rows with unchanged owning claims qualify.
"""
import base64
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

MANIFEST = {'state_commit': '8d4c43157a99f95705163b1d66a82776e9633c1f', 'snapshot_sha256': '036b3a13e185d7c2138f2210bbb23d402c6caeadf79631cf847da6d46f7d4d76', 'rows': [{'key': '64b0870d8d0714a1fd8c94a0', 'original': 'cf05fd83633c155c74b30ca9b5758db6452295ee20dd71227a56f0385cc7b821', 'observed': None, 'owners': {'e6e5e94156a18505ba1a922e': '2f1e31d54e4a1a34c2838bd24a5ef5cf9029c1dc3a1115ee90ee8b9441056ee4', 'a620b64610193ffd0aaf7011': 'aab587e0cb44efd423ed49325d623cef74adb39e46a39e70ba9a97dc51642ac5', '7bbf151fe52ff69781b3e821': 'e4a995e8ce3b07a22f24be696dd2a31f31104c20dcdd01d4e088b5f4f0755a88', '70ed22bc5c53d14f79f3e373': '336ba30aa336f47dd2e4e0399c9293c2f112c10422b548b4f6f27d1c27ea8de3'}}]}


def fingerprint(row):
    return hashlib.sha256(json.dumps([base64.b64encode(v).decode() if isinstance(v, bytes) else v
        for v in row], ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def eligible(db, spec):
    owners = {}
    for row in db.execute("SELECT * FROM posts WHERE status IN ('published','publishing','uncertain')"):
        columns = [r[1] for r in db.execute('PRAGMA table_info(posts)')]
        post = dict(zip(columns, row))
        try:
            keys = json.loads(post['payload']).get('illustration_keys', {})
            if not isinstance(keys, dict): return False
            if spec['key'] in keys.values(): owners[post['id']] = fingerprint(row)
        except (TypeError, ValueError): return False
    if not owners or any(spec['owners'].get(k) != value for k, value in owners.items()):
        return False
    current = db.execute('SELECT * FROM illustrations WHERE id=?', (spec['key'],)).fetchone()
    observed = fingerprint(current) if current else None
    return observed != spec['original'] and observed == spec['observed']


def repair(db, archive_bytes, manifest=MANIFEST):
    if hashlib.sha256(archive_bytes).hexdigest() != manifest['snapshot_sha256']:
        raise ValueError('Historical snapshot checksum mismatch')
    archive = sqlite3.connect(':memory:')
    try:
        archive.deserialize(archive_bytes)
        if archive.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Historical snapshot integrity mismatch')
        replacements = []
        for spec in manifest['rows']:
            if not eligible(db, spec): continue
            row = archive.execute('SELECT * FROM illustrations WHERE id=?', (spec['key'],)).fetchone()
            if not row or fingerprint(row) != spec['original']:
                raise ValueError('Historical row checksum mismatch')
            replacements.append(row)
        # Archive recovery shares the existing bounded cache. Only images
        # referenced exclusively by expired/superseded drafts may be evicted;
        # every current draft and publication claim remains protected.
        from .image_safety import MAX_CACHE_BYTES, MAX_CACHED_IMAGES
        protected = {row[0] for row in replacements}
        for status, payload in db.execute('SELECT status,payload FROM posts'):
            if status in ('expired', 'superseded'): continue
            bindings = json.loads(payload).get('illustration_keys', {})
            if not isinstance(bindings, dict): return 0
            protected.update(bindings.values())
        projected = {row[0]: len(row[3] or b'') for row in db.execute(
            "SELECT * FROM illustrations WHERE status='ready'")}
        for row in replacements:
            if row[2] == 'ready': projected[row[0]] = len(row[3])
            else: projected.pop(row[0], None)
        evictions = []
        for (key,) in db.execute("SELECT id FROM illustrations WHERE status='ready' ORDER BY updated_at,id"):
            if len(projected) <= MAX_CACHED_IMAGES and sum(projected.values()) <= MAX_CACHE_BYTES: break
            if key in protected: continue
            evictions.append(key); projected.pop(key, None)
        if len(projected) > MAX_CACHED_IMAGES or sum(projected.values()) > MAX_CACHE_BYTES:
            return 0  # Never break a normal restore or discard an active image.
        for key in evictions:
            db.execute('DELETE FROM illustrations WHERE id=?', (key,))
        for row in replacements:
            db.execute('INSERT OR REPLACE INTO illustrations VALUES(?,?,?,?,?,?,?)', row)
        return len(replacements)
    finally:
        archive.close()


def recover(path: Path, git, manifest=MANIFEST):
    db = sqlite3.connect(path)
    try:
        if not any(eligible(db, spec) for spec in manifest['rows']): return 0
        revision = manifest['state_commit']
        try:
            snapshot = git('show', revision + ':platform.sqlite')
        except subprocess.CalledProcessError:
            git('fetch', '--no-tags', '--depth=1', 'origin', revision)
            snapshot = git('show', revision + ':platform.sqlite')
        with db:
            db.execute('BEGIN IMMEDIATE')
            return repair(db, snapshot, manifest)
    finally:
        db.close()
