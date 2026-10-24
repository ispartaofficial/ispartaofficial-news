"""Authorized production entrypoints using the same encrypted credential state."""
import argparse
import json
import os
from pathlib import Path

from .credentials import CredentialError, active, resolve
from news_engine.domain import TZ, now
from news_engine.state_git import persist
from news_engine.store import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('publish', 'pharmacy', 'pharmacy-observe', 'weather', 'check'))
    parser.add_argument('--wait-for-target', action='store_true')
    args = parser.parse_args()
    path = Path('state/platform.sqlite')
    store = Store(path)
    try:
        token, renewal = resolve(store, maintain=args.action in ('publish', 'pharmacy', 'weather'),
                                 checkpoint=lambda: persist(path))
        if target := os.getenv('GITHUB_STEP_SUMMARY'):
            with Path(target).open('a', encoding='utf-8') as out:
                out.write('### Instagram bağlantı sürekliliği\n\n```json\n' + json.dumps(renewal, indent=2) + '\n```\n')
        with active(token):
            if args.action == 'publish':
                from .runtime import publish
                from news_engine.operations import write_job_summary, failed
                result = publish(path, Path('dist'))
                write_job_summary(result)
                from news_engine.delivery_audit import refresh
                observations = refresh(store)
                print(json.dumps({'publication': result, 'observation': observations}))
                if failed(result):
                    raise SystemExit(1)
            elif args.action == 'weather':
                from news_engine.weather import record_result, run_weather
                from news_engine.weather_data import SITE
                result = run_weather(store, SITE, checkpoint=lambda: persist(path),
                                     wait_for_target=args.wait_for_target)
                record_result(store, now().astimezone(TZ).date().isoformat(), result)
                from news_engine.delivery_audit import refresh
                observations = refresh(store)
                print(json.dumps({'weather': result, 'observation': observations}))
                if target := os.getenv('GITHUB_STEP_SUMMARY'):
                    with Path(target).open('a', encoding='utf-8') as out:
                        out.write('### Günlük hava durumu story\n\n```json\n' + json.dumps(result, indent=2) + '\n```\n')
                if result['status'] not in ('published', 'already_published', 'outside_window'):
                    raise SystemExit(1)
            elif args.action == 'check':
                from news_engine.connection_health import main as check
                check()
            else:
                from news_engine.pharmacy import run, observe
                from news_engine.pharmacy_data import profile
                result = (observe(store, now()) if args.action == 'pharmacy-observe' else
                          run(store, profile()['site'], checkpoint=lambda: persist(path), wait_for_target=args.wait_for_target))
                print(json.dumps(result))
                if target := os.getenv('GITHUB_STEP_SUMMARY'):
                    with Path(target).open('a', encoding='utf-8') as out:
                        out.write('### Nöbetçi eczane story\n\n```json\n' + json.dumps(result, indent=2) + '\n```\n')
                if args.action == 'pharmacy' and result['status'] not in ('published', 'already_published', 'outside_window'):
                    raise SystemExit(1)
    except CredentialError as exc:
        raise SystemExit(str(exc)) from None
    finally:
        store.close()


if __name__ == '__main__':
    main()
