import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from breachtwin.cli import builtin_contract, main
from breachtwin.contract import Contract
from breachtwin.engine import run_contract
from breachtwin.evidence import bundle, export_regression, read_bundle, verify_bundle, write_bundle
from breachtwin.report import write_report


@pytest.fixture
def evidence():
    return bundle(run_contract(builtin_contract(), 'breachtwin.lab:create_fixed_app', label='Fixed'))


def test_checksum_detects_modified_evidence(evidence):
    evidence['payload']['label'] = 'Modified'
    with pytest.raises(ValueError, match='checksum mismatch'):
        verify_bundle(evidence)


def test_evidence_roundtrip_and_unsupported_version(evidence, tmp_path):
    path = tmp_path / 'evidence.json'
    write_bundle(path, evidence)
    assert read_bundle(path) == evidence
    evidence['schema_version'] = 2
    with pytest.raises(ValueError, match='Unsupported'):
        verify_bundle(evidence)


def test_report_escapes_script_termination(evidence, tmp_path):
    payload = copy.deepcopy(evidence['payload'])
    attack = '</script><script>window.UNEXPECTED_EXECUTION=true</script>'
    payload['label'] = attack
    output = tmp_path / 'report.html'
    write_report([bundle(payload)], output)
    text = output.read_text()
    assert attack not in text
    assert '\\u003c/script\\u003e' in text
    assert '__BREACHTWIN_DATA__' not in text


def test_regression_passes_fixed_and_detects_reintroduced_bugs(evidence, tmp_path):
    output = tmp_path / 'test_regression.py'
    export_regression(evidence, 'breachtwin.lab:create_fixed_app', output)
    fixed = subprocess.run([sys.executable, str(output)], capture_output=True, text=True)
    assert fixed.returncode == 0, fixed.stderr
    env = dict(os.environ, BREACHTWIN_FACTORY='breachtwin.lab:create_vulnerable_app')
    vulnerable = subprocess.run([sys.executable, str(output)], env=env, capture_output=True, text=True)
    assert vulnerable.returncode == 1
    assert 'FAILED (failures=3)' in vulnerable.stderr


def test_external_replay_requires_explicit_factory(evidence, tmp_path, capsys):
    evidence['payload']['factory'] = 'unknown:execute'
    path = tmp_path / 'external.json'
    write_bundle(path, bundle(evidence['payload']))
    assert main(['replay', str(path), '--out', str(tmp_path / 'replay')]) == 2
    assert 'supply --factory' in capsys.readouterr().err


def test_demo_and_replay_commands(tmp_path):
    folder = tmp_path / 'demo'
    assert main(['demo', '--out', str(folder)]) == 0
    assert (folder / 'report.html').is_file()
    fixed = folder / 'fixed/evidence.json'
    assert main(['verify', str(fixed)]) == 0
    assert main(['replay', str(fixed), '--out', str(tmp_path / 'replayed')]) == 0
    replay = read_bundle(tmp_path / 'replayed/evidence.json')['payload']
    assert replay['recorded_verdicts_match'] is True
    assert replay['recorded_environment_matches'] is True
    assert main(['replay', str(folder / 'vulnerable/evidence.json'), '--out', str(tmp_path / 'vuln-replayed')]) == 1


def test_check_exit_codes_init_validation_and_export(tmp_path):
    contract = tmp_path / 'contract.json'
    assert main(['init', '--out', str(contract)]) == 0
    assert main(['init', '--out', str(contract)]) == 2
    assert main(['validate', str(contract)]) == 0
    for factory, code in [('breachtwin.lab:create_fixed_app', 0), ('breachtwin.lab:create_vulnerable_app', 1), ('tests.fixtures:create_outage', 2)]:
        assert main(['check', '--contract', str(contract), '--factory', factory, '--out', str(tmp_path / 'check')]) == code
    bad = tmp_path / 'bad.json'
    bad.write_text('{no}')
    assert main(['validate', str(bad)]) == 2


def test_validation_error_does_not_print_input_secrets(tmp_path, capsys):
    data = builtin_contract().model_dump(mode='json')
    data['actors']['alice']['headers']['Authorization'] = 'DO-NOT-PRINT-SECRET'
    path = tmp_path / 'invalid.json'
    path.write_text(json.dumps(data))
    assert main(['validate', str(path)]) == 2
    assert 'DO-NOT-PRINT-SECRET' not in capsys.readouterr().err


def test_documented_custom_integration(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / 'custom'
    assert main(['check', '--contract', str(root / 'examples/contracts/custom.json'), '--factory', 'examples.custom_app:create_app', '--out', str(output)]) == 0
    evidence = read_bundle(output / 'evidence.json')
    assert evidence['payload']['summary']['blocked'] == 1
    assert main(['export-test', str(output / 'evidence.json'), '--factory', 'examples.custom_app:create_app', '--out', str(tmp_path / 'test_custom.py')]) == 0


def test_distributed_lab_contract_stays_in_sync():
    root = Path(__file__).resolve().parents[1]
    example = Contract.model_validate_json((root / 'examples/contracts/lab.json').read_text())
    assert example == builtin_contract()
