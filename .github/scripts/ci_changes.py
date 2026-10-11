#!/usr/bin/env python3
"""Select CI work without skipping required jobs; fail open on uncertain diffs."""
import json
import os
from pathlib import PurePosixPath
import subprocess


def classify(paths, event, profile):
    if event != 'pull_request':
        return {'code': True, 'docs': True, 'app': event != 'schedule'}
    if not paths:
        return {'code': True, 'docs': True, 'app': True}
    def documentation(path):
        p = PurePosixPath(path)
        return p.parts[0] == 'docs' or (len(p.parts) == 1 and
               (p.suffix.lower() in {'.md', '.rst'} or p.name in {'LICENSE', 'LICENSE.md'}))
    code = any(not documentation(p) for p in paths)
    app = code
    if profile == 'incorporation':
        app = any(p.startswith(('tenue-de-livre/generateur-de-facture/',
                                'tenue-de-livre/declaration-tps-tvq/', '.github/'))
                  or (not documentation(p) and PurePosixPath(p).suffix.lower() not in
                      {'.csv', '.xlsx', '.xls', '.ods', '.pdf', '.docx', '.png', '.jpg', '.jpeg'})
                  for p in paths)
    return {'code': code, 'docs': True, 'app': app}


def main():
    event_name = os.environ['GITHUB_EVENT_NAME']
    profile = os.environ.get('CI_PROFILE', '')
    paths = None
    if event_name == 'pull_request':
        try:
            event = json.loads(open(os.environ['GITHUB_EVENT_PATH']).read())
            pr = event['pull_request']
            base, head = pr['base']['sha'], pr['head']['sha']
            data = subprocess.check_output(['git', 'diff', '--name-only', '-z',
                                            f'{base}...{head}', '--'])
            paths = [p.decode('utf-8', errors='strict') for p in data.split(b'\0') if p]
        except (OSError, ValueError, KeyError, subprocess.CalledProcessError):
            print('Cannot determine changed files; running all checks.')
    result = classify(paths, event_name, profile)
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        for key, value in result.items():
            output.write(f'{key}={str(value).lower()}\n')


if __name__ == '__main__':
    main()
