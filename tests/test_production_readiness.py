from contextlib import closing
from datetime import timedelta
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
import yaml

from isparta import credentials as c
from news_engine.domain import digest, parse_date
from news_engine.security import validate_state
from news_engine.store import Store
from news_engine.delivery_audit import refresh

AT = parse_date('2026-10-23T18:00:00+03:00')
ROOT = 'SYNTHETIC_ROOT_' + 'x' * 100
NEW = 'SYNTHETIC_REFRESHED_' + 'y' * 100


def env():
    return dict(GITHUB_REPOSITORY=c.REPOSITORY, GITHUB_REF='refs/heads/main',
                INSTAGRAM_AUTH_MODE='instagram_login', INSTAGRAM_USER_ID=c.ACCOUNT,
                INSTAGRAM_ACCESS_TOKEN=ROOT)


def response(value, code=200):
    return Mock(status_code=code, ok=code == 200, json=Mock(return_value=value))


def identity():
    return response({'user_id': c.ACCOUNT, 'username': 'ispartaofficial', 'account_type': 'BUSINESS'})


def bootstrap(store):
    session = Mock(); session.get.return_value = identity()
    checkpoints = Mock()
    token, status = c.resolve(store, maintain=True, checkpoint=checkpoints, at=AT, environ=env(), session=session)
    assert token == ROOT and status['expires_at'] is None
    assert status['last_result'] == 'waiting_minimum_age'
    checkpoints.assert_called_once()
    return session


def test_real_encryption_survives_restart_root_expiry_and_keeps_plaintext_out(tmp_path):
    path = tmp_path / 'db.sqlite'
    with closing(Store(path)) as store:
        bootstrap(store)
        session = Mock(); session.get.side_effect = [identity(), response({'access_token': NEW, 'token_type': 'bearer', 'expires_in': 5184000}), identity()]
        checkpoints = Mock(side_effect=lambda: validate_state(path))
        token, status = c.resolve(store, maintain=True, checkpoint=checkpoints, at=AT + timedelta(hours=26), environ=env(), session=session)
        assert token == NEW and status['last_result'] == 'refreshed'
        assert parse_date(status['expires_at']) == AT + timedelta(hours=26, days=60)
        assert session.get.call_args_list[1].args[0] == 'https://graph.instagram.com/refresh_access_token'
        assert session.get.call_args_list[1].kwargs['allow_redirects'] is False
        checkpoints.assert_called_once()
    assert ROOT.encode() not in path.read_bytes() and NEW.encode() not in path.read_bytes()
    with closing(Store(path)) as store:
        session = Mock()
        token, _ = c.resolve(store, at=AT + timedelta(days=50), environ=env(), session=session)
        assert token == NEW  # Root is now only the wrapping secret, never sent.
        session.get.assert_not_called()
        validate_state(path)


def test_first_day_never_calls_refresh_endpoint(tmp_path):
    with closing(Store(tmp_path/'db')) as store:
        bootstrap(store)
        session = Mock(); checkpoint = Mock()
        c.resolve(store, maintain=True, checkpoint=checkpoint, at=AT+timedelta(hours=24), environ=env(), session=session)
        session.get.assert_not_called(); checkpoint.assert_not_called()


@pytest.mark.parametrize('fault', ['wrong_key', 'tamper', 'plain_text'])
def test_unreadable_capsule_fails_closed_without_falling_back_or_network(tmp_path, fault):
    with closing(Store(tmp_path/'db')) as store:
        bootstrap(store); values = env()
        if fault == 'wrong_key':
            values['INSTAGRAM_ACCESS_TOKEN'] = NEW
        else:
            blob = store.db.execute('SELECT sealed FROM credential_capsules').fetchone()[0]
            blob = blob[:-1] + bytes([blob[-1] ^ 1]) if fault == 'tamper' else ROOT
            with store.db: store.db.execute('UPDATE credential_capsules SET sealed=?', (blob,))
        session = Mock()
        with pytest.raises((c.CredentialError, ValueError)):
            c.resolve(store, maintain=True, checkpoint=Mock(), at=AT+timedelta(days=2), environ=values, session=session)
        session.get.assert_not_called()


@pytest.mark.parametrize('value', [None, [], {'access_token': NEW, 'expires_in': 0}, {'access_token': NEW, 'token_type': 'bearer', 'expires_in': True}, {'error': {'message': ROOT}}])
def test_refresh_failure_preserves_existing_credential_and_limits_retry(tmp_path, value):
    with closing(Store(tmp_path/'db')) as store:
        bootstrap(store)
        session = Mock(); session.get.side_effect = [identity(), response(value)]
        token, status = c.resolve(store, maintain=True, checkpoint=Mock(), at=AT+timedelta(days=2), environ=env(), session=session)
        assert token == ROOT and status['last_result'] == 'refresh_failed'
        assert ROOT not in json.dumps(status) and NEW not in json.dumps(status)
        quiet = Mock()
        c.resolve(store, maintain=True, checkpoint=Mock(), at=AT+timedelta(days=2, hours=1), environ=env(), session=quiet)
        quiet.get.assert_not_called()


def test_checkpoint_failure_stops_before_caller_receives_refreshed_credential(tmp_path):
    with closing(Store(tmp_path/'db')) as store:
        bootstrap(store)
        session = Mock(); session.get.side_effect = [identity(), response({'access_token':NEW,'token_type':'bearer','expires_in':5184000}), identity()]
        with pytest.raises(RuntimeError, match='storage unavailable'):
            c.resolve(store, maintain=True, checkpoint=Mock(side_effect=RuntimeError('storage unavailable')),
                      at=AT+timedelta(days=2), environ=env(), session=session)


@pytest.mark.parametrize('field,value', [('GITHUB_REPOSITORY','ntekintr/seferihisarofficial-news'),('GITHUB_REF','refs/heads/topic'),('INSTAGRAM_USER_ID','1'),('INSTAGRAM_AUTH_MODE','facebook_login')])
def test_credential_boundary_refuses_foreign_account_or_untrusted_branch(tmp_path,field,value):
    with closing(Store(tmp_path/'db')) as store:
        values=env(); values[field]=value; session=Mock()
        with pytest.raises(c.CredentialError,match='account_boundary'):
            c.resolve(store,maintain=True,checkpoint=Mock(),at=AT,environ=values,session=session)
        session.get.assert_not_called()


def test_read_only_check_does_not_create_capsule(tmp_path):
    with closing(Store(tmp_path/'db')) as store:
        session=Mock()
        token,_=c.resolve(store,at=AT,environ=env(),session=session)
        assert token == ROOT
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='credential_capsules'").fetchone()
        session.get.assert_not_called()


def test_delivery_audit_uses_instagram_login_identity_feed_caption_and_story_membership(tmp_path):
    with closing(Store(tmp_path/'db')) as store:
        parent = dict(id='a'*24,item_id=None,revision=1,kind='news',due_at=AT.isoformat(),title='Isparta',caption='Isparta. Kaynak: resmî duyuru',category='news',slides=[],created_at=AT.isoformat(),published_at=AT.isoformat())
        child = {**parent, 'id':'b'*24,'publish_format':'story','story_index':0,'parent_post_id':parent['id']}
        for post,media in ((parent,'1234'),(child,'5678')):
            store.queue(post)
            with store.db: store.db.execute("UPDATE posts SET status='published',media_id=? WHERE id=?",(media,post['id']))
        before=store.rows('SELECT * FROM posts')
        def get(url,**kwargs):
            if url.endswith('/me'):return identity()
            if url.endswith('/1234'):return response({'id':'1234','caption':parent['caption'],'timestamp':AT.isoformat()})
            if url.endswith('/stories'):return response({'data':[{'id':'5678'}]})
            raise AssertionError('Unexpected GET')
        session=Mock();session.get.side_effect=get
        result=refresh(store,AT+timedelta(minutes=4),environ=env(),session=session)
        assert result['results']=={'present':2}
        assert all(call.args[0].startswith('https://graph.instagram.com/') for call in session.get.call_args_list)
        assert all(call.kwargs['allow_redirects'] is False for call in session.get.call_args_list)
        assert store.rows('SELECT * FROM posts')==before
        session.request.assert_not_called()


def test_production_workflows_keep_secrets_out_of_research_and_share_serial_state():
    root=Path(__file__).resolve().parents[1]
    research=yaml.safe_load((root/'.github/workflows/research.yml').read_text())
    pharmacy=yaml.safe_load((root/'.github/workflows/pharmacy-story.yml').read_text())
    connection=yaml.safe_load((root/'.github/workflows/connection.yml').read_text())
    assert 'INSTAGRAM_ACCESS_TOKEN' not in json.dumps(research['jobs']['research'])
    publish=research['jobs']['publish']
    assert publish['environment']=='instagram-production'
    assert 'vars.INSTAGRAM_PUBLISH_ENABLED' in publish['if'] and 'vars.META_TESTS_COMPLETED' in publish['if']
    assert 'isparta.production publish' in json.dumps(publish)
    assert 'isparta-production' in research['concurrency']['group'] and 'isparta-production' in pharmacy['concurrency']['group']
    assert 'isparta.production pharmacy --wait-for-target' in json.dumps(pharmacy)
    assert 'isparta.production check' in json.dumps(connection)
    assert connection['permissions']=={'contents':'read'}


@pytest.mark.parametrize('status',['published','publishing','uncertain'])
def test_first_launch_is_bound_to_one_parent_and_manual_event(status):
    from isparta.runtime import initial_launch_allowed
    store=Mock();store.posts.return_value=[]
    assert initial_launch_allowed(store,'a'*24,'workflow_dispatch')
    assert not initial_launch_allowed(store,'a'*24,'schedule')
    assert not initial_launch_allowed(store,'wrong','workflow_dispatch')
    store.posts.return_value=[{'id':'a'*24,'status':status},{'id':'b'*24,'parent_post_id':'a'*24,'status':status}]
    assert initial_launch_allowed(store,'a'*24,'workflow_dispatch')
    assert not initial_launch_allowed(store,'c'*24,'workflow_dispatch')


def test_expired_capsule_cannot_use_even_present_root(tmp_path):
    with closing(Store(tmp_path/'db')) as store:
        bootstrap(store)
        value=c.load(store,ROOT)
        value['expires_at']=(AT+timedelta(hours=1)).isoformat()
        c.save(store,value,ROOT,Mock())
        session=Mock()
        with pytest.raises(c.CredentialError,match='expired'):
            c.resolve(store,at=AT+timedelta(days=2),environ=env(),session=session)
        session.get.assert_not_called()
