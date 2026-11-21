// Optional backup trigger for the main-branch Isparta research workflow.
// It only reads Actions runs and dispatches research.yml on main with no workflow input.
// It never receives Meta/Instagram/Cloudflare AI credentials and never changes
// publication gates, limits or durable state; the workflow keeps all of them.
const ACTIONS = 'https://api.github.com/repos/ispartaofficial/ispartaofficial-news/actions';
const RESEARCH = '.github/workflows/research.yml';
// Every workflow whose jobs share the `isparta-production` concurrency group.
// A new queued run would evict the pending one there, so none may be active.
const PRODUCTION = [RESEARCH, '.github/workflows/weather-story.yml',
                    '.github/workflows/pharmacy-story.yml', '.github/workflows/resolve-uncertain.yml'];
const ACTIVE = ['queued', 'in_progress', 'waiting', 'requested', 'pending'];
const MINUTE = 60000;
// Same span as the GitHub cron '20,50 4-20 * * *' (07:20-23:50 TR). UTC minutes of day.
export const DISPATCH_OPEN = 4*60+20, DISPATCH_CLOSE = 20*60+51;
export const RECENT_MINUTES = 25;
// weather-story/pharmacy-story accept a research run created in these UTC hours and
// publish from 07:35/16:35 TR (waiting for 08:00/17:00). A covering research must finish
// after `open`; dispatching stops at `close` so the story job still starts before 09:00/18:00 TR.
export const STORY_WINDOWS = [
  {name:'weather', hours:[4,5], open:4*60+35, close:5*60+30},
  {name:'pharmacy', hours:[13,14], open:13*60+35, close:14*60+30},
];

const path = run => String(run?.path || '').split('@')[0];

export async function checkResearch(env, fetcher = fetch, now = Date.now()) {
  if (env.CRON_DISPATCH_ENABLED !== 'true' || !env.GITHUB_ACTIONS_TOKEN) return {status:'disabled'};
  const dayStart = Math.floor(now / 86400000) * 86400000;
  const minute = Math.floor((now - dayStart) / MINUTE);
  if (minute < DISPATCH_OPEN || minute >= DISPATCH_CLOSE) return {status:'outside_window'};
  const headers = {'Authorization':'Bearer '+env.GITHUB_ACTIONS_TOKEN, 'Accept':'application/vnd.github+json',
                   'User-Agent':'IspartaOfficialResearchWatch', 'X-GitHub-Api-Version':'2022-11-28'};
  let stage = 'github_fetch';
  try {
    const response = await fetcher(ACTIONS+'/runs?branch=main&per_page=100', {headers, redirect:'manual'});
    if (!response.ok) return {status:'github_unreachable'};
    stage = 'github_parse';
    const body = await response.json();
    if (!Array.isArray(body?.workflow_runs)) return {status:'invalid_runs'};
    const runs = body.workflow_runs.filter(r => r && r.head_branch === 'main');
    if (runs.some(r => PRODUCTION.includes(path(r)) && ACTIVE.includes(r.status))) return {status:'production_busy'};
    const research = runs.filter(r => path(r) === RESEARCH);
    const window = STORY_WINDOWS.find(w => w.open <= minute && minute < w.close);
    const covered = window && research.some(r => {
      const created = Date.parse(r.created_at), finished = Date.parse(r.updated_at);
      return r.conclusion === 'success' && created >= dayStart && window.hours.includes(new Date(created).getUTCHours()) &&
        finished >= dayStart + window.open*MINUTE;
    });
    // Inside a story window without a covering successful research, only an active
    // production run (checked above) may hold the dispatch back.
    if (!window || covered) {
      if (research.some(r => now - Date.parse(r.created_at) < RECENT_MINUTES*MINUTE)) return {status:'recent_run'};
    }
    stage = 'dispatch';
    const dispatch = await fetcher(ACTIONS+'/workflows/research.yml/dispatches', {method:'POST',
      headers:{...headers, 'Content-Type':'application/json'}, body:JSON.stringify({ref:'main'}), redirect:'manual'});
    const ok = dispatch.status === 204 || dispatch.status === 200;
    return {status: ok ? 'dispatched' : 'dispatch_failed', ...(window && !covered ? {window:window.name} : {})};
  } catch (error) {
    const error_type = ['TypeError','SyntaxError','RangeError'].includes(error?.name) ? error.name : 'Error';
    const message = String(error?.message || '').toLowerCase();
    const cause = message.includes('illegal invocation') ? 'fetch_receiver' : message.includes('redirect') ? 'redirect_refused' : 'request_failed';
    return {status:'check_failed', stage, error_type, cause}; // Never log a request, token, provider body or raw exception.
  }
}

export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(checkResearch(env).then(result => console.log(JSON.stringify(result))));
  },
  async fetch() {
    return new Response('IspartaOfficial research check. Scheduled execution only.', {status:200});
  }
};
