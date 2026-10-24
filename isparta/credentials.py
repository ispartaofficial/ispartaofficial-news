"""Instagram Login renewal with an authenticated, encrypted durable capsule.

The original environment secret remains the wrapping key. It is never copied
to the state branch. Only AES-256-GCM ciphertext is persisted; plaintext and
provider responses never enter SQLite, summaries, artifacts or exceptions.
"""
from contextlib import contextmanager
from datetime import timedelta
import hashlib
import json
import os
import re

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import requests

from news_engine.domain import now, parse_date
from news_engine.meta_identity import base_url, identity_query, identity_problem

REPOSITORY = 'ispartaofficial/ispartaofficial-news'
ACCOUNT = '17841403171726739'
MAGIC = b'IGC1'
CONTEXT = (REPOSITORY + ':instagram_login:' + ACCOUNT + ':capsule-v1').encode()
FIELDS = {'credential', 'observed_at', 'refreshed_at', 'expires_at', 'next_attempt_at', 'last_result'}


class CredentialError(Exception):
    """Only fixed local codes may be exposed by callers."""


def valid_token(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{64,4096}', value) is not None


def validate_capsule_rows(db):
    if [r[1] for r in db.execute('PRAGMA table_info(credential_capsules)')] != ['slot', 'sealed']:
        raise ValueError('Unexpected encrypted credential fields')
    rows = list(db.execute('SELECT slot,sealed FROM credential_capsules'))
    if len(rows) > 1:
        raise ValueError('Unexpected encrypted credential history')
    for slot, sealed in rows:
        if slot != 'instagram-v1' or not isinstance(sealed, bytes) or not 100 <= len(sealed) <= 8192 or not sealed.startswith(MAGIC):
            raise ValueError('Invalid encrypted credential envelope')


def cipher(root):
    if not valid_token(root):
        raise CredentialError('credential_settings_missing')
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=hashlib.sha256(CONTEXT).digest(), info=CONTEXT).derive(root.encode())
    return AESGCM(key)


def seal(value, root):
    nonce = os.urandom(12)
    return MAGIC + nonce + cipher(root).encrypt(nonce, json.dumps(value, separators=(',', ':')).encode(), CONTEXT)


def unseal(sealed, root):
    try:
        value = json.loads(cipher(root).decrypt(sealed[4:16], sealed[16:], CONTEXT))
        if set(value) != FIELDS or not valid_token(value['credential']):
            raise ValueError()
        for key in ('observed_at', 'next_attempt_at'):
            if not parse_date(value[key]) or parse_date(value[key]).tzinfo is None:
                raise ValueError()
        for key in ('refreshed_at', 'expires_at'):
            if value[key] is not None and (not parse_date(value[key]) or parse_date(value[key]).tzinfo is None):
                raise ValueError()
        if value['last_result'] not in ('waiting_minimum_age', 'refreshed', 'refresh_failed'):
            raise ValueError()
        return value
    except Exception:
        raise CredentialError('credential_capsule_unreadable') from None


def load(store, root):
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='credential_capsules'").fetchone()
    if not exists:
        return None
    validate_capsule_rows(store.db)
    row = store.db.execute('SELECT sealed FROM credential_capsules WHERE slot=?', ('instagram-v1',)).fetchone()
    return unseal(row[0], root) if row else None


def save(store, value, root, checkpoint):
    if checkpoint is None:
        raise CredentialError('credential_checkpoint_required')
    sealed = seal(value, root)
    with store.db:
        store.db.execute('CREATE TABLE IF NOT EXISTS credential_capsules(slot TEXT PRIMARY KEY,sealed BLOB NOT NULL)')
        store.db.execute('INSERT OR REPLACE INTO credential_capsules VALUES(?,?)', ('instagram-v1', sealed))
    # Do not use a refreshed credential for publication before durable storage.
    checkpoint()


def verify_identity(session, token, version):
    path, fields = identity_query('instagram_login', ACCOUNT)
    try:
        r = session.get(base_url('instagram_login', version) + '/' + path,
                        headers={'Authorization': 'Bearer ' + token}, params={'fields': fields},
                        timeout=(8, 25), allow_redirects=False)
        if r.status_code != 200 or identity_problem(r.json(), 'instagram_login', ACCOUNT, 'ispartaofficial'):
            raise CredentialError('credential_identity_failed')
    except (requests.RequestException, ValueError):
        raise CredentialError('credential_identity_failed') from None


def resolve(store, *, maintain=False, checkpoint=None, at=None, environ=None, session=None):
    env = os.environ if environ is None else environ
    at = at or now()
    if (env.get('GITHUB_REPOSITORY') != REPOSITORY or env.get('GITHUB_REF') != 'refs/heads/main'
            or env.get('INSTAGRAM_AUTH_MODE') != 'instagram_login' or env.get('INSTAGRAM_USER_ID') != ACCOUNT):
        raise CredentialError('credential_account_boundary')
    root = env.get('INSTAGRAM_ACCESS_TOKEN', '')
    cipher(root)
    session = session or requests.Session()
    value = load(store, root)
    if value is None:
        value = dict(credential=root, observed_at=at.isoformat(), refreshed_at=None, expires_at=None,
                     next_attempt_at=(at + timedelta(hours=26)).isoformat(), last_result='waiting_minimum_age')
        if maintain:
            verify_identity(session, root, env.get('META_GRAPH_VERSION', 'v26.0'))
            save(store, value, root, checkpoint)
    elif value['expires_at'] and parse_date(value['expires_at']) <= at:
        raise CredentialError('credential_expired')
    elif maintain and parse_date(value['next_attempt_at']) <= at:
        verify_identity(session, value['credential'], env.get('META_GRAPH_VERSION', 'v26.0'))
        try:
            # Official refresh endpoint requires the credential in the query.
            # Fixed HTTPS host, no redirects, no URL/body/exception logging.
            r = session.get('https://graph.instagram.com/refresh_access_token',
                            params={'grant_type': 'ig_refresh_token', 'access_token': value['credential']},
                            timeout=(8, 30), allow_redirects=False)
            payload = r.json()
            if (r.status_code != 200 or not isinstance(payload, dict) or 'error' in payload
                    or not valid_token(payload.get('access_token')) or not isinstance(payload.get('token_type'), str)
                    or payload['token_type'].casefold() != 'bearer'
                    or type(payload.get('expires_in')) is not int or not 86400 <= payload['expires_in'] <= 61 * 86400):
                raise ValueError()
            verify_identity(session, payload['access_token'], env.get('META_GRAPH_VERSION', 'v26.0'))
            value.update(credential=payload['access_token'], refreshed_at=at.isoformat(),
                         expires_at=(at + timedelta(seconds=payload['expires_in'])).isoformat(),
                         next_attempt_at=(at + timedelta(days=7)).isoformat(), last_result='refreshed')
        except (requests.RequestException, ValueError, CredentialError):
            # Keep the still identity-verified credential; bounded daily retry.
            value.update(next_attempt_at=(at + timedelta(days=1)).isoformat(), last_result='refresh_failed')
        save(store, value, root, checkpoint)
    summary = {k: value[k] for k in ('observed_at', 'refreshed_at', 'expires_at', 'next_attempt_at', 'last_result')}
    return value['credential'], summary


@contextmanager
def active(token):
    previous = os.environ.get('INSTAGRAM_ACCESS_TOKEN')
    os.environ['INSTAGRAM_ACCESS_TOKEN'] = token
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('INSTAGRAM_ACCESS_TOKEN', None)
        else:
            os.environ['INSTAGRAM_ACCESS_TOKEN'] = previous
