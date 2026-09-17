import json
import socket

import pytest

from breachtwin.cli import builtin_contract
from breachtwin.contract import Assertion, Contract
from breachtwin.engine import exit_status, matches, run_contract


@pytest.mark.parametrize('mode,verdict,code', [('vulnerable', 'reproduced', 1), ('fixed', 'blocked', 0)])
def test_seeded_cases_and_controls(mode, verdict, code):
    payload = run_contract(builtin_contract(), f'breachtwin.lab:create_{mode}_app')
    assert payload['summary'][verdict] == 3
    assert all(r['controls_ok'] for r in payload['results'])
    assert sum(s['kind'] == 'control' and s['outcome'] == 'passed' for r in payload['results'] for s in r['steps']) == 6
    assert exit_status(payload) == code


@pytest.mark.parametrize('factory', ['create_outage', 'create_deny_everything', 'create_lifecycle_failure'])
def test_broken_apps_never_pass(factory):
    payload = run_contract(builtin_contract(), 'tests.fixtures:' + factory)
    assert payload['summary'] == {'reproduced': 0, 'blocked': 0, 'inconclusive': 3}
    assert exit_status(payload) == 2
    assert 'This text might contain a secret' not in json.dumps(payload)
    assert sum(s['kind'] == 'control' for r in payload['results'] for s in r['steps']) == 6


@pytest.mark.parametrize('factory', ['create_error', 'create_wrong_record', 'create_redirect'])
def test_unexpected_response_is_inconclusive(factory):
    payload = run_contract(builtin_contract(), 'tests.fixtures:' + factory)
    assert payload['results'][0]['verdict'] == 'inconclusive'
    assert payload['summary']['blocked'] == 2


def test_denial_status_with_leaked_data_is_still_a_failure():
    payload = run_contract(builtin_contract(), 'tests.fixtures:create_leak_with_denial')
    case = payload['results'][0]
    assert case['verdict'] == 'reproduced'
    assert case['steps'][1]['status'] == 403
    assert case['steps'][1]['expected_matched'] is True
    assert case['steps'][1]['violation_matched'] is True


def test_failed_setup_skips_probe_and_does_not_claim_a_fix():
    case = run_contract(builtin_contract(), 'tests.fixtures:create_failed_setup')['results'][1]
    assert case['verdict'] == 'inconclusive'
    assert case['steps'][1]['outcome'] == 'failed'
    assert case['steps'][2]['outcome'] == 'skipped'


def test_cookies_are_not_shared_across_actors():
    payload = run_contract(builtin_contract(), 'tests.fixtures:create_cookie_fixture')
    assert payload['summary']['blocked'] == 3
    assert 'admin-SESSION-SECRET' not in json.dumps(payload)


def test_fresh_state_and_lifespan_per_experiment():
    from tests import fixtures
    fixtures.STARTUPS = fixtures.SHUTDOWNS = 0
    for _ in range(2):
        payload = run_contract(builtin_contract(), 'tests.fixtures:create_lifecycle_app')
        assert payload['summary']['blocked'] == 3
    assert fixtures.STARTUPS == fixtures.SHUTDOWNS == 6


def test_local_requests_do_not_open_connections(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError('Unexpected outbound connection')
    monkeypatch.setattr(socket, 'create_connection', fail)
    payload = run_contract(builtin_contract(), 'breachtwin.lab:create_fixed_app')
    assert payload['summary']['blocked'] == 3


def test_environment_secrets_are_resolved_but_never_serialized(monkeypatch):
    monkeypatch.setenv('BT_TEST_AUTH', 'Bearer synthetic-SECRET-947')
    data = builtin_contract().model_dump(mode='json')
    for actor in data['actors'].values():
        actor['headers']['Authorization'] = {'env': 'BT_TEST_AUTH'}
    payload = run_contract(Contract.model_validate(data), 'tests.fixtures:create_credential_fixture')
    assert payload['summary']['blocked'] == 3
    encoded = json.dumps(payload)
    assert 'synthetic-SECRET-947' not in encoded
    assert 'response-SECRET-947' not in encoded
    assert 'BT_TEST_AUTH' in encoded


def test_missing_environment_secret_fails_closed(monkeypatch):
    monkeypatch.delenv('BT_MISSING', raising=False)
    data = builtin_contract().model_dump(mode='json')
    data['actors']['alice']['headers']['Authorization'] = {'env': 'BT_MISSING'}
    with pytest.raises(ValueError, match='Missing an environment'):
        run_contract(Contract.model_validate(data), 'breachtwin.lab:create_fixed_app')


def test_json_assertions_distinguish_boolean_from_integer():
    assertion = Assertion(json_equals={'created': True})
    assert not matches(assertion, 200, {'created': 1})
    assert matches(assertion, 200, {'created': True})
    assert not matches(Assertion(json_equals={'value': None}), 200, {})
