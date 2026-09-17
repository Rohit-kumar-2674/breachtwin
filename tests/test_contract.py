import copy

import pytest
from pydantic import ValidationError

from breachtwin.cli import builtin_contract
from breachtwin.contract import Contract


@pytest.mark.parametrize('path', ['https://example.com/records', '//example.com/records', '/\\example.com', '/records\r\nHost: evil', '/records#secret'])
def test_rejects_nonlocal_or_ambiguous_paths(path):
    data = builtin_contract().model_dump(mode='json')
    data['experiments'][0]['steps'][1]['path'] = path
    with pytest.raises(ValidationError):
        Contract.model_validate(data)


def test_rejects_missing_control_unknown_actor_and_duplicate_ids():
    source = builtin_contract().model_dump(mode='json')
    mutations = []
    data = copy.deepcopy(source)
    data['experiments'][0]['steps'].pop()
    mutations.append(data)
    data = copy.deepcopy(source)
    data['experiments'][0]['steps'][0]['actor'] = 'missing'
    mutations.append(data)
    data = copy.deepcopy(source)
    data['experiments'][1]['id'] = data['experiments'][0]['id']
    mutations.append(data)
    for data in mutations:
        with pytest.raises(ValidationError):
            Contract.model_validate(data)


@pytest.mark.parametrize('header', ['Authorization', 'Cookie', 'X-API-Key', 'X-Access-Token'])
def test_credentials_cannot_be_embedded_in_contract(header):
    data = builtin_contract().model_dump(mode='json')
    data['actors']['alice']['headers'][header] = 'secret'
    with pytest.raises(ValidationError):
        Contract.model_validate(data)


def test_rejects_status_only_violation_evidence():
    data = builtin_contract().model_dump(mode='json')
    data['experiments'][0]['steps'][1]['violation'] = {'status': [200]}
    with pytest.raises(ValidationError):
        Contract.model_validate(data)


def test_rejects_embedded_factory_or_unknown_contract_keys():
    data = builtin_contract().model_dump(mode='json')
    data['factory'] = 'unknown:execute'
    with pytest.raises(ValidationError):
        Contract.model_validate(data)
