"""Fixed Meta API routes and account identity; no credentials or network calls."""
import re

HOSTS = {'facebook_login': 'graph.facebook.com', 'instagram_login': 'graph.instagram.com'}


def base_url(mode, version):
    if mode not in HOSTS or not re.fullmatch(r'v\d+\.0', version):
        raise ValueError('Invalid Instagram authentication configuration')
    return f'https://{HOSTS[mode]}/{version}'


def identity_query(mode, account):
    if mode == 'instagram_login':
        return 'me', 'user_id,username,account_type'
    if mode == 'facebook_login':
        return account, 'id,username'
    raise ValueError('Invalid Instagram authentication configuration')


def identity_problem(value, mode, account, username):
    """An app-scoped id never substitutes for an Instagram professional user_id."""
    if mode not in HOSTS or not isinstance(value, dict) or 'error' in value:
        return 'account_mismatch'
    if 'data' in value:
        rows = value['data']
        if (not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict)
                or any(k in value for k in ('id', 'user_id', 'username', 'account_type'))):
            return 'account_mismatch'
        value = rows[0]
    if 'error' in value:
        return 'account_mismatch'
    field = 'user_id' if mode == 'instagram_login' else 'id'
    identity = value.get(field)
    if (not isinstance(identity, str) or not re.fullmatch(r'\d{1,32}', identity)
            or identity != account or value.get('username') != username):
        return 'account_mismatch'
    if mode == 'instagram_login':
        kind = value.get('account_type')
        if not isinstance(kind, str) or kind.upper() not in ('BUSINESS', 'MEDIA_CREATOR'):
            return 'account_type_unverified'
    return None
