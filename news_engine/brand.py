"""Independent Isparta brand; no imported legacy logos or claims."""
from pathlib import Path
VERSION = 'isparta-rose-v1'
LEGACY = VERSION
PUBLIC_ASSET = 'logo-isparta-rose-v1.jpg'
LOGOS = {VERSION: 'logo-profile.jpg'}
def logo_path(version=VERSION):
    if version not in LOGOS:
        raise ValueError('Unsupported Isparta brand version')
    return Path(__file__).resolve().parents[1] / 'isparta/assets' / LOGOS[version]
def prepare(post):
    if post.get('status', 'prepared') in ('prepared', 'blocked_source'):
        post['brand_version'] = VERSION
def version_for(post):
    return post.get('brand_version', VERSION)
