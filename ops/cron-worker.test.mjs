import test from 'node:test';
import assert from 'node:assert/strict';
import worker, {checkResearch, STORY_WINDOWS} from './cron-worker.mjs';

const env = {CRON_DISPATCH_ENABLED:'true', GITHUB_ACTIONS_TOKEN:'PRIVATE_FAKE_TEST_VALUE'};
const at = hhmm => Date.parse(`2026-11-21T${hhmm}:00Z`);
const iso = ms => new Date(ms).toISOString();
const run = (file, fields) => ({head_branch:'main', path:`.github/workflows/${file}`, status:'completed', conclusion:'success', ...fields});
const research = (created, finished, fields = {}) => run('research.yml', {created_at:iso(created), updated_at:iso(finished), ...fields});
const listed = runs => ({ok:true, json:async () => ({workflow_runs:runs})});

function recorder(runs, dispatchStatus = 204) {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({url, options});
    return calls.length === 1 ? listed(runs) : {status:dispatchStatus};
  };
  return {calls, fetcher};
}

test('disabled or tokenless worker makes no request', async () => {
  const never = () => assert.fail('Unexpected fetch');
  assert.equal((await checkResearch({}, never, at('10:00'))).status, 'disabled');
  assert.equal((await checkResearch({CRON_DISPATCH_ENABLED:'true'}, never, at('10:00'))).status, 'disabled');
  assert.equal((await checkResearch({GITHUB_ACTIONS_TOKEN:'x', CRON_DISPATCH_ENABLED:'false'}, never, at('10:00'))).status, 'disabled');
});

test('never dispatches outside the GitHub research cron span 04:20-20:50 UTC', async () => {
  const never = () => assert.fail('Unexpected fetch');
  for (const hhmm of ['00:12', '03:57', '04:12', '04:19', '20:57', '21:12', '23:57']) {
    assert.equal((await checkResearch(env, never, at(hhmm))).status, 'outside_window', hhmm);
  }
  const {calls, fetcher} = recorder([]);
  assert.equal((await checkResearch(env, fetcher, at('04:27'))).status, 'dispatched');
  assert.equal((await checkResearch(env, recorder([]).fetcher, at('20:42'))).status, 'dispatched');
  assert.equal(calls.length, 2);
});

test('stale research dispatches only research.yml on main, without inputs, token only in header', async () => {
  const now = at('10:42');
  const {calls, fetcher} = recorder([research(now-70*60000, now-55*60000)]);
  assert.deepEqual(await checkResearch(env, fetcher, now), {status:'dispatched'});
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, 'https://api.github.com/repos/ispartaofficial/ispartaofficial-news/actions/runs?branch=main&per_page=100');
  assert.equal(calls[0].options.method, undefined);
  assert.equal(calls[1].url, 'https://api.github.com/repos/ispartaofficial/ispartaofficial-news/actions/workflows/research.yml/dispatches');
  assert.equal(calls[1].options.method, 'POST');
  assert.deepEqual(JSON.parse(calls[1].options.body), {ref:'main'});
  assert.ok(calls.every(c => c.options.redirect === 'manual'));
  assert.ok(calls.every(c => c.options.headers.Authorization === 'Bearer '+env.GITHUB_ACTIONS_TOKEN));
  assert.ok(calls.every(c => !c.url.includes(env.GITHUB_ACTIONS_TOKEN) && !String(c.options.body || '').includes(env.GITHUB_ACTIONS_TOKEN)));
});

test('a research started in the last 25 minutes holds the dispatch, whatever its result', async () => {
  const now = at('10:42');
  for (const conclusion of ['success', 'failure', 'cancelled']) {
    const {calls, fetcher} = recorder([research(now-20*60000, now-6*60000, {conclusion})]);
    assert.equal((await checkResearch(env, fetcher, now)).status, 'recent_run');
    assert.equal(calls.length, 1);
  }
  const {fetcher} = recorder([research(now-26*60000, now-12*60000)]);
  assert.equal((await checkResearch(env, fetcher, now)).status, 'dispatched');
});

test('any active production run blocks dispatch so the shared queue never evicts a pending job', async () => {
  const now = at('10:42');
  for (const file of ['research.yml', 'weather-story.yml', 'pharmacy-story.yml', 'resolve-uncertain.yml']) {
    for (const status of ['queued', 'in_progress', 'waiting', 'requested', 'pending']) {
      const {calls, fetcher} = recorder([run(file, {status, conclusion:null, created_at:iso(now-90*60000)})]);
      assert.equal((await checkResearch(env, fetcher, now)).status, 'production_busy', `${file} ${status}`);
      assert.equal(calls.length, 1);
    }
  }
  // Unrelated or non-main runs do not count.
  const {fetcher} = recorder([run('ci.yml', {status:'in_progress'}), run('research.yml', {status:'queued', head_branch:'feature'}),
                              run('operations-watch.yml', {status:'in_progress'})]);
  assert.equal((await checkResearch(env, fetcher, now)).status, 'dispatched');
});

test('weather window guarantees one successful research after 07:35 TR', async () => {
  // A research that finished before 04:35 UTC cannot publish the 08:00 TR story.
  const early = research(at('04:21'), at('04:34'));
  let r = recorder([early]);
  assert.deepEqual(await checkResearch(env, r.fetcher, at('04:42')), {status:'dispatched', window:'weather'});
  // Outside story windows the same run would hold the dispatch.
  r = recorder([research(at('10:21'), at('10:34'))]);
  assert.equal((await checkResearch(env, r.fetcher, at('10:42'))).status, 'recent_run');
  // Covered: a successful T04/T05 run finished after the window opened.
  const covering = research(at('04:27'), at('04:41'));
  r = recorder([covering]);
  assert.equal((await checkResearch(env, r.fetcher, at('04:42'))).status, 'recent_run');
  r = recorder([covering]);
  assert.deepEqual(await checkResearch(env, r.fetcher, at('05:12')), {status:'dispatched'});
  // A failed run inside the window does not cover it.
  r = recorder([research(at('04:42'), at('04:55'), {conclusion:'failure'})]);
  assert.deepEqual(await checkResearch(env, r.fetcher, at('04:57')), {status:'dispatched', window:'weather'});
  // Yesterday's run never covers today's window.
  r = recorder([research(at('05:00')-86400000, at('05:14')-86400000)]);
  assert.deepEqual(await checkResearch(env, r.fetcher, at('04:42')), {status:'dispatched', window:'weather'});
  // Even inside the window an active production run wins.
  r = recorder([run('weather-story.yml', {status:'in_progress', conclusion:null, created_at:iso(at('04:40'))})]);
  assert.equal((await checkResearch(env, r.fetcher, at('04:57'))).status, 'production_busy');
});

test('pharmacy window guarantees one successful research after 16:35 TR', async () => {
  let r = recorder([research(at('13:20'), at('13:33'))]);
  assert.deepEqual(await checkResearch(env, r.fetcher, at('13:42')), {status:'dispatched', window:'pharmacy'});
  r = recorder([research(at('13:40'), at('13:53'))]);
  assert.equal((await checkResearch(env, r.fetcher, at('13:57'))).status, 'recent_run');
  // After the window closes the normal 25-minute rule applies again.
  r = recorder([research(at('14:20'), at('14:31'), {conclusion:'failure'})]);
  assert.equal((await checkResearch(env, r.fetcher, at('14:42'))).status, 'recent_run');
});

test('story windows match the workflow_run hours and leave time before 09:00/18:00 TR', () => {
  assert.deepEqual(STORY_WINDOWS.map(w => [w.name, w.hours]), [['weather', [4, 5]], ['pharmacy', [13, 14]]]);
  for (const w of STORY_WINDOWS) {
    assert.equal(w.open, w.hours[0]*60+35);  // --wait-for-target starts 25 minutes before the target.
    assert.ok(w.close <= w.hours[1]*60+30);  // ~15 min research + story job start before the hour ends.
  }
});

test('provider failures and redirects never reveal the credential and never dispatch', async () => {
  const now = at('10:42');
  let result = await checkResearch(env, async () => { throw new Error(env.GITHUB_ACTIONS_TOKEN); }, now);
  assert.deepEqual(result, {status:'check_failed', stage:'github_fetch', error_type:'Error', cause:'request_failed'});
  let calls = 0;
  result = await checkResearch(env, async (url, options) => {
    calls++; assert.equal(options.redirect, 'manual');
    return {ok:false, status:302, headers:{get:() => 'https://untrusted.invalid/'}};
  }, now);
  assert.equal(result.status, 'github_unreachable'); assert.equal(calls, 1);
  result = await checkResearch(env, async () => ({ok:true, json:async () => { throw new SyntaxError(env.GITHUB_ACTIONS_TOKEN); }}), now);
  assert.deepEqual(result, {status:'check_failed', stage:'github_parse', error_type:'SyntaxError', cause:'request_failed'});
  for (const body of [{}, {workflow_runs:'x'}, null]) {
    calls = 0;
    result = await checkResearch(env, async () => { calls++; return {ok:true, json:async () => body}; }, now);
    assert.equal(result.status, 'invalid_runs'); assert.equal(calls, 1);
  }
  const {fetcher} = recorder([], 422);
  assert.deepEqual(await checkResearch(env, fetcher, now), {status:'dispatch_failed'});
  assert.ok(!JSON.stringify(result).includes(env.GITHUB_ACTIONS_TOKEN));
});

test('public fetch handler does nothing but describe itself', async () => {
  const response = await worker.fetch();
  assert.equal(response.status, 200);
  assert.match(await response.text(), /Scheduled execution only/);
});
