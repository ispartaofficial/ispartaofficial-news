"""Optional Cloudflare backup trigger: contract with research/weather/pharmacy workflows."""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKER = (ROOT/'ops/cron-worker.mjs').read_text(encoding='utf-8')
FLOWS = ROOT/'.github/workflows'


def load(name):
    flow = yaml.safe_load((FLOWS/name).read_text(encoding='utf-8'))
    return flow, flow.get('on', flow.get(True))


def test_worker_behaviour_tests_pass_with_node():
    node = shutil.which('node')
    if node is None:
        if os.environ.get('CI'):
            pytest.fail('Node.js is required in CI for ops/cron-worker.test.mjs')
        pytest.skip('Node.js not installed locally')
    result = subprocess.run([node, '--test', 'ops/cron-worker.test.mjs'], cwd=ROOT,
                            capture_output=True, text=True, encoding='utf-8', timeout=120)
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]


def test_research_accepts_an_input_free_main_dispatch_inside_the_same_cron_span():
    flow, events = load('research.yml')
    assert [r['cron'] for r in events['schedule']] == ['20,50 4-20 * * *']
    inputs = events['workflow_dispatch']['inputs']
    # The worker sends no inputs; every input must stay optional and default to empty.
    assert all(v.get('required') is False and v.get('default') == '' for v in inputs.values())
    assert flow['concurrency'] == {'group': 'isparta-production', 'cancel-in-progress': False}
    assert "github.ref == 'refs/heads/main'" in flow['jobs']['research']['if']
    assert 'DISPATCH_OPEN = 4*60+20, DISPATCH_CLOSE = 20*60+51' in WORKER
    assert "body:JSON.stringify({ref:'main'})" in WORKER
    assert WORKER.count('/dispatches') == 1 and "'/workflows/research.yml/dispatches'" in WORKER


@pytest.mark.parametrize('name,hours', [('weather-story.yml', (4, 5)), ('pharmacy-story.yml', (13, 14))])
def test_story_jobs_follow_a_dispatched_research_run_in_the_worker_window(name, hours):
    flow, events = load(name)
    assert events['workflow_run']['workflows'] == ['Research and prepare Isparta content']
    job = flow['jobs'][name.split('-')[0]]
    condition = job['if']
    # The triggering run's event is not inspected, so a dispatched research counts like a scheduled one.
    assert 'workflow_run.event' not in condition
    for hour in hours:
        assert f"'T{hour:02d}:'" in condition
    assert f"name:'{name.split('-')[0]}', hours:[{hours[0]},{hours[1]}], open:{hours[0]}*60+35" in WORKER


def test_worker_guards_every_workflow_sharing_the_production_queue():
    sharing = sorted(p.name for p in FLOWS.glob('*.yml') if 'isparta-production' in p.read_text(encoding='utf-8'))
    assert sharing == ['pharmacy-story.yml', 'research.yml', 'resolve-uncertain.yml', 'weather-story.yml']
    for name in sharing:
        assert f'.github/workflows/{name}' in WORKER or (name == 'research.yml' and "RESEARCH = '.github/workflows/research.yml'" in WORKER)


def test_worker_has_no_social_or_ai_credentials_and_ships_disabled():
    for forbidden in ('INSTAGRAM', 'META_', 'FACEBOOK', 'CLOUDFLARE_API_TOKEN', 'STATE_WRITE_TOKEN', 'first_post_id', 'inputs'):
        assert forbidden not in WORKER
    assert set(re.findall(r'env\.([A-Z_]+)', WORKER)) == {'CRON_DISPATCH_ENABLED', 'GITHUB_ACTIONS_TOKEN'}
    config = json.loads(re.sub(r'^\s*//.*$', '', (ROOT/'ops/wrangler.jsonc').read_text(encoding='utf-8'), flags=re.M))
    assert config['main'] == 'cron-worker.mjs'
    assert config['vars'] == {'CRON_DISPATCH_ENABLED': 'false'}
    assert config['triggers'] == {'crons': ['12,27,42,57 4-20 * * *']}
    assert 'GITHUB_ACTIONS_TOKEN' not in json.dumps(config['vars'])
