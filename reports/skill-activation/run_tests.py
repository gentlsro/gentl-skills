"""Run fresh Codex sessions against the skill, without explicitly invoking it.
All configured MCP servers are disabled to prevent live external side effects.
"""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import tomllib

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CASES = [
    ('exploration', 'Exploration without a ticket', 'Investigate why order exports are slow in this project. Explain the likely cause and what we should try next.', True),
    ('implementation', 'Implementation without a ticket', 'Remove the unnecessary per-row delay in export.py while keeping the output identical. Check that the export still works.', True),
    ('documentation', 'Documentation without a ticket', 'Read export.py and update README.md to explain how to call export_orders and what it returns.', True),
    ('ticket', 'Investigation with a ticket', 'Investigate the slow order export for https://gitlab.com/acme/shop/-/issues/311. Use the local code to identify the likely cause; do not change code yet.', True),
    ('casual', 'Casual conversation', 'Hi! Hope you are having a good day.', False),
    ('paused', 'Work with tracking stopped', 'Stop tracking; do not write any further work summaries to Gentl. Investigate why order exports are slow in this project and explain the likely cause.', False),
]

def run_case(case):
    key, title, prompt, expected = case
    workspace = Path(tempfile.mkdtemp(prefix=f'gentl-{key}-'))
    shutil.copytree(ROOT / 'skills/gentl-task-tracking', workspace / '.agents/skills/gentl-task-tracking')
    (workspace / 'export.py').write_text('import time\n\ndef export_orders(rows):\n    output = []\n    for row in rows:\n        time.sleep(0.01)\n        output.append(str(row))\n    return "\\n".join(output)\n')
    (workspace / 'README.md').write_text('Example project. export.py exports orders.\n')
    config = tomllib.loads((Path.home() / '.codex/config.toml').read_text())
    args = ['codex', 'exec', '--ephemeral', '--skip-git-repo-check', '--sandbox', 'workspace-write', '--json', '--color', 'never', '-C', str(workspace), '-o', str(OUT / f'{key}.response.txt')]
    for name in config.get('mcp_servers', {}):
        args += ['-c', f'mcp_servers.{name}.enabled=false']
    args += ['-']
    (OUT / f'{key}.prompt.txt').write_text(prompt)
    start = time.time()
    with (OUT / f'{key}.events.jsonl').open('w') as stdout, (OUT / f'{key}.stderr.txt').open('w') as stderr:
        try:
            result = subprocess.run(args, input=prompt, text=True, stdout=stdout, stderr=stderr, timeout=180)
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            exit_code = 'timeout'
    record = dict(id=key, title=title, prompt=prompt, expected_activation=expected, exit_code=exit_code, seconds=round(time.time()-start, 2), workspace=str(workspace))
    (OUT / f'{key}.run.json').write_text(json.dumps(record, indent=2))
    return record

if __name__ == '__main__':
    provenance = {'codex_version': subprocess.check_output(['codex', '--version'], text=True).strip(), 'skill_sha256': hashlib.sha256((ROOT / 'skills/gentl-task-tracking/SKILL.md').read_bytes()).hexdigest(), 'configured_model': tomllib.loads((Path.home()/'.codex/config.toml').read_text()).get('model'), 'live_mcp_disabled': True}
    (OUT/'provenance.json').write_text(json.dumps(provenance, indent=2))
    shutil.copytree(ROOT/'skills/gentl-task-tracking', OUT/'tested-skill', dirs_exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for record in pool.map(run_case, CASES):
            print(json.dumps(record), flush=True)
