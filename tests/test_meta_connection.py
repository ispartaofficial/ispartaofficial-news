"""Independent account/route checks with fake HTTP only; never live credentials."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from isparta import runtime
from news_engine.connection_health import check
from news_engine.instagram import Instagram
from news_engine.meta_identity import base_url, identity_problem


def env(mode='instagram_login'):
    return {'INSTAGRAM_AUTH_MODE':mode,'INSTAGRAM_USER_ID':'12345678',
            'INSTAGRAM_ACCESS_TOKEN':'fake-test-key','META_GRAPH_VERSION':'v26.0'}


def response(value,status=200):
    return SimpleNamespace(ok=status<400,status_code=status,json=lambda:value)


def identity():
    return {'id':'99999999','user_id':'12345678','username':'ispartaofficial','account_type':'BUSINESS'}


@pytest.mark.parametrize('mode,host,key',[('instagram_login','graph.instagram.com','user_id'),
                                       ('facebook_login','graph.facebook.com','id')])
def test_read_only_connection_keeps_route_and_identity_field_together(mode,host,key):
    value=identity() if mode=='instagram_login' else {'id':'12345678','username':'ispartaofficial'}
    session=Mock();session.get.side_effect=[response(value),response({'data':[{'quota_usage':3}]})]
    result=check(env(mode),session)
    assert result['instagram']=='connected' and result['quota_usage']==3
    assert result['expiry']=='not_checked' and result['publication_permission_verified'] is False
    assert result['publication_attempted'] is False
    assert session.get.call_count==2
    first=session.get.call_args_list[0]
    assert first.args[0]==f'https://{host}/v26.0/'+('me' if mode=='instagram_login' else '12345678')
    assert key in first.kwargs['params']['fields'].split(',')
    assert all(c.kwargs['allow_redirects'] is False for c in session.get.call_args_list)
    session.request.assert_not_called();session.post.assert_not_called()
    assert 'fake-test-key' not in json.dumps(result) and '12345678' not in json.dumps(result)


@pytest.mark.parametrize('change',[
    {'user_id':None}, {'user_id':'87654321'}, {'username':'seferihisarofficial'},
    {'user_id':12345678}, {'account_type':None}, {'account_type':'PERSONAL'},
])
def test_app_scoped_id_wrong_account_and_unknown_type_never_reach_quota(change):
    value={**identity(),'id':'12345678',**change}
    session=Mock();session.get.return_value=response(value)
    result=check(env(),session)
    assert result['instagram'] in ('account_mismatch','account_type_unverified')
    assert session.get.call_count==1 and 'quota_usage' not in result


@pytest.mark.parametrize('value',[
    {'data':[]}, {'data':[identity(),identity()]},
    {'data':[identity()],'user_id':'12345678'},
    {'data':[{**identity(),'error':{'code':190}}]},
])
def test_ambiguous_or_error_identity_wrappers_are_rejected(value):
    assert identity_problem(value,'instagram_login','12345678','ispartaofficial')=='account_mismatch'


def test_documented_single_row_and_professional_account_types():
    for kind in ('Business','BUSINESS','Media_Creator','MEDIA_CREATOR'):
        assert identity_problem({'data':[{**identity(),'account_type':kind}]},'instagram_login','12345678','ispartaofficial') is None


@pytest.mark.parametrize('changes',[{'INSTAGRAM_AUTH_MODE':'unknown'}, {'META_GRAPH_VERSION':'https://elsewhere.invalid'},
                                    {'INSTAGRAM_ACCESS_TOKEN':''}, {'INSTAGRAM_USER_ID':'not-an-id'}])
def test_invalid_settings_never_send_a_key(changes):
    session=Mock();result=check({**env(),**changes},session)
    assert result['instagram']!='connected'
    session.get.assert_not_called()


def test_instagram_login_never_sends_page_credentials_to_instagram_host():
    session=Mock();session.get.side_effect=[response(identity()),response({'data':[{'quota_usage':0}]})]
    result=check({**env(),'FACEBOOK_PUBLISH_ENABLED':'true','FACEBOOK_PAGE_ID':'55555555',
                  'FACEBOOK_PAGE_ACCESS_TOKEN':'fake-page-key'},session)
    assert result['facebook']=='unsupported_auth_mode' and session.get.call_count==2
    assert all('fake-page-key' not in str(c) for c in session.get.call_args_list)


def test_invalid_credentials_and_redirects_are_sanitized_without_retry():
    for value,status,expected in [({'error':{'code':190,'message':'fake-test-key'}},400,'credential_invalid'),
                                  ({},302,'read_failed')]:
        session=Mock();session.get.return_value=response(value,status)
        result=check(env(),session)
        assert result['instagram']==expected and session.get.call_count==1
        assert 'fake-test-key' not in json.dumps(result)


@pytest.mark.parametrize('mode,host',[('instagram_login','graph.instagram.com'),('facebook_login','graph.facebook.com')])
def test_adapter_uses_fixed_host_and_requires_explicit_controls(monkeypatch,mode,host):
    for key,value in env(mode).items():monkeypatch.setenv(key,value)
    monkeypatch.setenv('INSTAGRAM_PUBLISH_ENABLED','true');monkeypatch.delenv('META_TESTS_COMPLETED',raising=False)
    api=Instagram(Mock());assert not api.enabled()
    monkeypatch.setenv('META_TESTS_COMPLETED','true');assert api.enabled()
    assert api.base==f'https://{host}/v26.0'
    monkeypatch.setenv('INSTAGRAM_AUTH_MODE','facebook_login' if mode=='instagram_login' else 'instagram_login')
    assert not api.enabled()  # Changing the mode can't move an existing adapter's key.


@pytest.mark.parametrize('value,status',[({},302),({'error':{'message':'fake-test-key'}},200),([],200)])
def test_adapter_rejects_redirects_and_error_payloads_without_key_disclosure(monkeypatch,value,status):
    for key,v in env().items():monkeypatch.setenv(key,v)
    session=Mock();session.request.return_value=response(value,status)
    with pytest.raises(RuntimeError) as caught:Instagram(session).call('me','GET',fields='user_id,username')
    assert 'fake-test-key' not in str(caught.value)
    assert session.request.call_count==1 and session.request.call_args.kwargs['allow_redirects'] is False


@pytest.mark.parametrize('settings',[{'publishing_enabled':True,'meta_connected':False},
                                     {'publishing_enabled':True},
                                     {'publishing_enabled':True,'meta_connected':'false'}])
def test_profile_connection_gate_blocks_all_account_reads(tmp_path,monkeypatch,settings):
    (tmp_path/'config').mkdir();(tmp_path/'config/runtime.json').write_text(json.dumps(settings))
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    adapter=Mock(side_effect=AssertionError('No account read before setup'))
    monkeypatch.setattr('news_engine.instagram.Instagram',adapter)
    assert runtime.publish(tmp_path/'state.sqlite',tmp_path/'public')=={'status':'disabled'}
    adapter.assert_not_called();assert not (tmp_path/'state.sqlite').exists()


@pytest.mark.parametrize('mode,reason',[('facebook_login','authentication_mode_mismatch'),
                                       ('instagram_login','account_mismatch')])
def test_wrong_route_or_account_cannot_open_state_or_fetch_media(tmp_path,monkeypatch,mode,reason):
    (tmp_path/'config').mkdir();(tmp_path/'config/runtime.json').write_text(json.dumps(
        {'publishing_enabled':True,'meta_connected':True,'instagram_auth_mode':'instagram_login'}))
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    monkeypatch.setenv('GITHUB_REPOSITORY',runtime.REPOSITORY);monkeypatch.setenv('GITHUB_REF','refs/heads/main')
    api=Mock(auth_mode=mode);api.enabled.return_value=True;api.identity_problem.return_value='account_mismatch'
    monkeypatch.setattr('news_engine.instagram.Instagram',lambda:api)
    media=Mock(side_effect=AssertionError('No media request after wrong identity'))
    monkeypatch.setattr('requests.get',media)
    assert runtime.publish(tmp_path/'state.sqlite',tmp_path/'public')=={'status':reason}
    assert not (tmp_path/'state.sqlite').exists();media.assert_not_called();api.container.assert_not_called()
