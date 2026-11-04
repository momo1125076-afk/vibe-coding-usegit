#!/usr/bin/env python3
"""Evidence-backed UseGit workflow controller. Python 3.10+, standard library only.

Only this controller writes .usegit/state.json. Reports and evidence are supplied
by the agent; validation establishes consistency, not the truth of human claims.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qsl

MAX_JSON = 4 * 1024 * 1024
STAGES = ('discover', 'find-skills', 'find-repos', 'evaluate', 'run', 'adapt', 'deploy', 'verify')
MODES = ('plan', 'local', 'preview', 'release')
STATUSES = ('pending', 'complete', 'blocked', 'failed', 'skipped', 'not-required', 'stale')
DEPENDENCIES = {'discover': [], 'find-skills': ['discover'], 'find-repos': ['discover'],
                'evaluate': ['find-skills', 'find-repos'], 'run': ['evaluate'],
                'adapt': ['run'], 'deploy': ['adapt'], 'verify': ['adapt']}
RISK_ACTIONS = {'preview-deploy', 'production-deploy', 'store-submit', 'paid-resource', 'public-publish', 'destructive'}


class WorkflowError(Exception):
    """Expected input, dependency, evidence or authorization error."""


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    try:
        with Path(path).open('rb') as handle:
            raw = handle.read(MAX_JSON + 1)
        if len(raw) > MAX_JSON:
            raise WorkflowError(f'JSON exceeds 4 MiB: {path}')
        return json.loads(raw.decode('utf-8'))
    except (OSError, ValueError, UnicodeError) as exc:
        raise WorkflowError(f'Cannot read JSON {path}: {exc}') from exc


def atomic_json(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(data) > MAX_JSON:
        raise WorkflowError('JSON exceeds 4 MiB; original file retained')
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise WorkflowError(f'{label} must be a nonempty string')


class Workflow:
    def __init__(self, project):
        self.root = Path(project).expanduser().resolve()
        self.directory = self.root / '.usegit'
        self.state_path = self.directory / 'state.json'

    def check_control(self):
        if self.directory.is_symlink() or (self.directory.exists() and not self.directory.is_dir()):
            raise WorkflowError('.usegit must be a real directory')
        for name in ('artifacts', 'evidence'):
            child = self.directory / name
            if child.is_symlink() or (child.exists() and not child.is_dir()):
                raise WorkflowError(f'.usegit/{name} must be a real directory')
        if self.state_path.is_symlink():
            raise WorkflowError('state.json cannot be a symlink')

    @contextmanager
    def locked(self):
        self.check_control()
        if not self.directory.is_dir():
            raise WorkflowError('Project is not initialized; use init')
        lock = self.directory / 'state.lock'
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise WorkflowError('Workflow locked; check the owning process before manually removing state.lock') from exc
        try:
            with os.fdopen(fd, 'w') as handle:
                handle.write(json.dumps({'pid': os.getpid(), 'created_at': now()}))
            yield
        finally:
            lock.unlink(missing_ok=True)

    def safe_artifact_location(self, candidate):
        if not candidate.is_relative_to(self.root):
            return False
        if candidate.is_relative_to(self.directory):
            return any(candidate.is_relative_to(self.directory / name) for name in ('artifacts', 'evidence'))
        return True

    def path(self, value):
        nonempty(value, 'path')
        relative = Path(value)
        if relative.is_absolute() or '..' in relative.parts or '\\' in value:
            raise WorkflowError(f'Unsafe project-relative path: {value}')
        candidate = (self.root / relative).resolve()
        if not self.safe_artifact_location(candidate):
            raise WorkflowError(f'Path escapes project or references workflow state: {value}')
        if not candidate.is_file():
            raise WorkflowError(f'Evidence/output does not exist as a file: {value}')
        return candidate

    def digest(self, value):
        path = self.path(value)
        hasher = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def load(self):
        state = read_json(self.state_path)
        if not isinstance(state, dict) or state.get('schema_version') != 1 or state.get('mode') not in MODES:
            raise WorkflowError('Invalid state schema')
        if set(state.get('stages', {})) != set(STAGES):
            raise WorkflowError('Invalid state stages')
        if not isinstance(state.get('authorizations'), list):
            raise WorkflowError('Invalid authorization registry')
        for entry in state['stages'].values():
            if not isinstance(entry, dict) or entry.get('status') not in STATUSES or not isinstance(entry.get('hashes', {}), dict):
                raise WorkflowError('Invalid stage state')
        return state

    def save(self, state):
        state['updated_at'] = now()
        atomic_json(self.state_path, state)

    def required(self, mode):
        if mode == 'plan':
            return STAGES[:4]
        if mode == 'local':
            return tuple(stage for stage in STAGES if stage != 'deploy')
        return STAGES

    def dependencies(self, stage, mode):
        return ['deploy'] if stage == 'verify' and mode in ('preview', 'release') else DEPENDENCIES[stage]

    def descendants(self, stage, mode):
        result = set()
        for candidate in STAGES:
            if stage in self.dependencies(candidate, mode) or any(parent in result for parent in self.dependencies(candidate, mode)):
                result.add(candidate)
        return result

    def stale(self, state, stages, reason):
        for stage in stages:
            entry = state['stages'][stage]
            if entry['status'] != 'not-required':
                entry['status'] = 'stale'
                entry['stale_reason'] = reason

    def audit_state(self, state):
        changed = []
        for stage in STAGES:
            entry = state['stages'][stage]
            if entry['status'] not in ('complete', 'skipped'):
                continue
            for relative, expected in entry.get('hashes', {}).items():
                try:
                    actual = self.digest(relative)
                except (WorkflowError, OSError):
                    actual = None
                if actual != expected:
                    changed.append({'stage': stage, 'path': relative})
                    self.stale(state, {stage} | self.descendants(stage, state['mode']), f'Changed or missing: {relative}')
                    break
        return changed

    def snapshot(self, state):
        required = self.required(state['mode'])
        ready = [stage for stage in required if state['stages'][stage]['status'] not in ('complete', 'skipped')
                 and all(state['stages'][dep]['status'] in ('complete', 'skipped') for dep in self.dependencies(stage, state['mode']))]
        return {'schema_version': 1, 'mode': state['mode'],
                'complete_for_mode': all(state['stages'][stage]['status'] in ('complete', 'skipped') for stage in required),
                'next': ready, 'stages': {stage: state['stages'][stage]['status'] for stage in STAGES}}

    def init(self, mode='local', name=None, idea=None, platforms=None):
        if mode not in MODES:
            raise WorkflowError('Unknown mode')
        self.check_control()
        self.root.mkdir(parents=True, exist_ok=True)
        self.directory.mkdir(exist_ok=True)
        with self.locked():
            if self.state_path.exists():
                raise WorkflowError('Already initialized; existing state retained')
            for folder in ('artifacts', 'evidence'):
                (self.directory / folder).mkdir(exist_ok=True)
            state = {'schema_version': 1, 'mode': mode,
                     'project': {'name': name or self.root.name, 'idea': idea or '', 'platforms': list(dict.fromkeys(platforms or []))}, 'created_at': now(), 'authorizations': [], 'requirements': [],
                     'stages': {stage: {'status': 'pending' if stage in self.required(mode) else 'not-required', 'hashes': {}} for stage in STAGES}}
            ignore = self.directory / '.gitignore'
            if ignore.is_symlink():
                raise WorkflowError('.usegit/.gitignore cannot be a symlink')
            if not ignore.exists():
                ignore.write_text('*\n!.gitignore\n', encoding='utf-8')
            self.save(state)
            return self.snapshot(state)

    def template(self, stage):
        report = {'schema_version': 1, 'stage': stage, 'status': 'blocked', 'summary': 'Describe the result; this template is not completion evidence.',
                  'outputs': [], 'evidence': [], 'checks': [], 'blockers': [{'reason': 'Not executed', 'next_action': 'Collect real evidence and complete this report'}], 'executed_actions': []}
        if stage == 'discover':
            report['requirements'] = [{'id': 'REQ-001', 'priority': 'must', 'text': 'Replace with customer need', 'acceptance': 'Replace with observable acceptance condition'}]
        return report

    def validate_report(self, state, stage, report, relative):
        if not isinstance(report, dict):
            raise WorkflowError('Report must be an object')
        for key in ('schema_version', 'stage', 'status', 'summary', 'outputs', 'evidence', 'checks', 'blockers', 'executed_actions'):
            if key not in report:
                raise WorkflowError(f'Missing report field: {key}')
        if report['schema_version'] != 1 or report['stage'] != stage:
            raise WorkflowError('Report schema/stage mismatch')
        status = report['status']
        if status not in ('complete', 'blocked', 'failed', 'skipped'):
            raise WorkflowError('Report status must be complete, blocked, failed or skipped')
        if status == 'skipped' and stage not in ('find-skills', 'adapt'):
            raise WorkflowError('Only find-skills and adapt may be skipped')
        if stage not in self.required(state['mode']):
            raise WorkflowError('Stage is not required in the selected mode')
        nonempty(report['summary'], 'summary')
        for key in ('outputs', 'evidence', 'checks', 'blockers', 'executed_actions'):
            if not isinstance(report[key], list):
                raise WorkflowError(f'{key} must be an array')
        if status in ('complete', 'skipped'):
            for dependency in self.dependencies(stage, state['mode']):
                if state['stages'][dependency]['status'] not in ('complete', 'skipped'):
                    raise WorkflowError(f'Dependency not complete: {dependency}')
            if report['blockers']:
                raise WorkflowError('A completed stage cannot have blockers')
        for blocker in report['blockers']:
            if not isinstance(blocker, dict):
                raise WorkflowError('Blocker must be an object')
            for field in ('reason', 'next_action'):
                nonempty(blocker.get(field), f'blocker.{field}')
        hashes = {relative: self.digest(relative)}
        for output in report['outputs']:
            if isinstance(output, dict):
                nonempty(output.get('description'), 'output.description')
                output = output.get('path')
            digest = self.digest(output)
            hashes[output] = digest
        observed_success = False
        evidence_by_id = {}
        for evidence in report['evidence']:
            if not isinstance(evidence, dict) or evidence.get('kind') not in ('file', 'command', 'url', 'manual'):
                raise WorkflowError('Evidence kind must be file, command, url or manual')
            for field in ('id', 'claim'):
                nonempty(evidence.get(field), f'evidence.{field}')
            if evidence['id'] in evidence_by_id:
                raise WorkflowError('Evidence IDs must be unique')
            evidence_by_id[evidence['id']] = evidence
            if evidence.get('verification') not in ('observed', 'simulated', 'not-run'):
                raise WorkflowError('Evidence verification must be observed, simulated or not-run')
            if evidence['kind'] in ('file', 'command', 'manual') or 'path' in evidence:
                path = evidence.get('path')
                digest = self.digest(path)
                hashes[path] = digest
            if evidence['kind'] in ('command', 'manual', 'url'):
                for key in ('environment', 'observed_at'):
                    nonempty(evidence.get(key), f'evidence.{key}')
            if evidence['kind'] == 'url':
                nonempty(evidence.get('url'), 'evidence.url')
                url = urlsplit(evidence['url'])
                sensitive_keys = ('token', 'secret', 'password', 'signature', 'credential', 'api_key', 'apikey', 'authorization')
                query_keys = [key.lower() for key, _ in parse_qsl(url.query, keep_blank_values=True)]
                if (url.scheme not in ('https', 'http') or not url.netloc or url.username or url.password
                        or any(part in key for key in query_keys for part in sensitive_keys)):
                    raise WorkflowError('Evidence URL must be HTTP(S) without embedded credentials or secret query parameters')
            if evidence['kind'] == 'command':
                nonempty(evidence.get('command'), 'evidence.command')
                if type(evidence.get('exit_code')) is not int:
                    raise WorkflowError('Command exit_code must be an integer')
                if 'commit' in evidence and not isinstance(evidence['commit'], str):
                    raise WorkflowError('Command commit must be a string')
                observed_success |= evidence['verification'] == 'observed' and evidence['exit_code'] == 0
        if status in ('complete', 'skipped') and not any(item['verification'] == 'observed' for item in report['evidence']):
            raise WorkflowError('Complete/skipped requires observed evidence')
        if stage == 'run' and status == 'complete' and not observed_success:
            raise WorkflowError('Run requires a real observed command with exit_code 0')
        requirements = state['requirements']
        if stage == 'discover':
            requirements = report.get('requirements', [])
            if not isinstance(requirements, list) or (status == 'complete' and not requirements):
                raise WorkflowError('Discover requires requirements')
            seen = set()
            for requirement in requirements:
                if not isinstance(requirement, dict):
                    raise WorkflowError('Requirement must be an object')
                for field in ('id', 'text', 'acceptance'):
                    nonempty(requirement.get(field), f'requirement.{field}')
                if requirement['id'] in seen or requirement.get('priority') not in ('must', 'should', 'could'):
                    raise WorkflowError('Requirement IDs must be unique; priority must be must/should/could')
                seen.add(requirement['id'])
        requirement_ids = {item['id'] for item in requirements}
        for check in report['checks']:
            if not isinstance(check, dict) or check.get('result') not in ('pass', 'fail', 'not-run', 'blocked', 'not-applicable'):
                raise WorkflowError('Invalid check result')
            nonempty(check.get('requirement_id'), 'check.requirement_id')
            if check['requirement_id'] not in requirement_ids:
                raise WorkflowError('Unknown requirement check')
            ids = check.get('evidence_ids')
            if not isinstance(ids, list) or any(not isinstance(item, str) or item not in evidence_by_id for item in ids):
                raise WorkflowError('Check evidence_ids must reference report evidence')
            if status in ('complete', 'skipped') and check['result'] in ('fail', 'blocked', 'not-run'):
                raise WorkflowError('Complete/skipped cannot contain failed, blocked or untested checks')
            if check['result'] == 'pass':
                if not ids or any(evidence_by_id[item]['verification'] != 'observed' or
                                  (evidence_by_id[item]['kind'] == 'command' and evidence_by_id[item]['exit_code'] != 0)
                                  for item in ids):
                    raise WorkflowError('A pass requires observed evidence, without failed commands')
        if stage == 'verify' and status == 'complete':
            for requirement in requirements:
                matching = [check for check in report['checks'] if check['requirement_id'] == requirement['id']]
                if requirement['priority'] == 'must' and not any(check['result'] == 'pass' for check in matching):
                    raise WorkflowError(f"Must requirement needs observed pass: {requirement['id']}")
        for action in report['executed_actions']:
            if not isinstance(action, dict):
                raise WorkflowError('Executed action must be an object')
            for key in ('action', 'target'):
                nonempty(action.get(key), f'executed action.{key}')
            if action['action'] not in RISK_ACTIONS:
                raise WorkflowError('Unknown executed action')
            if action['action'] in RISK_ACTIONS:
                if not any(auth['action'] == action['action'] and auth['target'] == action['target'] for auth in state['authorizations']):
                    raise WorkflowError(f"Missing specific authorization: {action['action']} -> {action['target']}")
        if stage == 'deploy' and status == 'complete':
            if not any(action['action'] in ('preview-deploy', 'production-deploy', 'public-publish', 'store-submit') for action in report['executed_actions']):
                raise WorkflowError('Deploy requires an authorized deployment action and exact target')
        return hashes, requirements

    def record(self, state, stage, relative):
        report = read_json(self.path(relative))
        hashes, requirements = self.validate_report(state, stage, report, relative)
        old = state['stages'][stage]
        changed = old.get('hashes') != hashes or old['status'] != report['status']
        state['stages'][stage] = {'status': report['status'], 'report': relative, 'hashes': hashes, 'recorded_at': now()}
        if stage == 'discover':
            state['requirements'] = requirements
        if changed:
            self.stale(state, self.descendants(stage, state['mode']), f'{stage} report changed')
        return {'recorded': stage, **self.snapshot(state)}

    def execute(self, args):
        if args.command == 'init':
            return self.init(args.mode, args.name, args.idea, args.platform), 0
        if args.command == 'template':
            report = self.template(args.stage)
            if args.output:
                self.check_control()
                target = Path(args.output)
                if target.is_absolute() or '..' in target.parts or '\\' in args.output:
                    raise WorkflowError('Template output must be project-relative')
                target = (self.root / target).resolve()
                if not self.safe_artifact_location(target):
                    raise WorkflowError('Unsafe template output')
                if target.exists():
                    raise WorkflowError('Template output already exists')
                target.parent.mkdir(parents=True, exist_ok=True)
                atomic_json(target, report)
            return report, 0
        if args.command == 'doctor':
            return {'python': {'status': 'ready', 'version': sys.version.split()[0]},
                    'tools': {tool: {'status': 'untested' if shutil.which(tool) else 'unavailable', 'path': shutil.which(tool)}
                              for tool in ('git', 'gh', 'node', 'npm', 'docker', 'flutter', 'xcodebuild')},
                    'credential_variables': {name: bool(os.environ.get(name)) for name in ('GH_TOKEN', 'GITHUB_TOKEN', 'GITEE_TOKEN')},
                    'authentication': 'untested', 'note': 'Executable presence is not login or platform readiness.'}, 0
        with self.locked():
            state = self.load()
            changed = self.audit_state(state)
            if changed:
                self.save(state)
            if args.command in ('status', 'next', 'audit'):
                result = self.snapshot(state)
                result['changes'] = changed
                return result, 2 if changed and args.command == 'audit' else 0
            if args.command == 'record':
                result = self.record(state, args.stage, args.artifact or args.report)
            elif args.command == 'authorize':
                args.action = args.action_option or args.action
                if args.action not in RISK_ACTIONS:
                    raise WorkflowError('Unknown authorization action')
                for key in ('action', 'target', 'source'):
                    nonempty(getattr(args, key), key)
                authorization = {'action': args.action, 'target': args.target, 'source': args.source, 'recorded_at': now()}
                if not any(all(item[key] == authorization[key] for key in ('action', 'target', 'source')) for item in state['authorizations']):
                    state['authorizations'].append(authorization)
                result = {'registered': authorization, 'note': 'Records received permission only; does not create permission.'}
            elif args.command == 'invalidate':
                self.stale(state, {args.stage} | self.descendants(args.stage, state['mode']), args.reason)
                result = self.snapshot(state)
            elif args.command == 'set-mode':
                previous = state['mode']
                args.mode = args.mode_option or args.mode
                if args.mode not in MODES:
                    raise WorkflowError('set-mode requires a mode')
                state['mode'] = args.mode
                state['mode_source'] = args.source
                for stage in STAGES:
                    if stage not in self.required(args.mode):
                        state['stages'][stage] = {'status': 'not-required', 'hashes': {}}
                    elif state['stages'][stage]['status'] == 'not-required':
                        state['stages'][stage] = {'status': 'pending', 'hashes': {}}
                if previous != args.mode:
                    self.stale(state, {'deploy', 'verify'}, 'Mode changed; deployment/verification must be reviewed')
                result = self.snapshot(state)
            else:
                raise WorkflowError('Unknown command')
            self.save(state)
            return result, 0


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--project', default='.', help='Customer project root (default: current directory)')
    sub = result.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='Initialize isolated workflow state')
    init.add_argument('--mode', choices=MODES, default='local')
    init.add_argument('--name', help='Customer project name')
    init.add_argument('--idea', help='Customer idea and scope summary')
    init.add_argument('--platform', action='append', default=[], help='Target platform ID; repeat for multiple platforms')
    for command in ('doctor', 'status', 'next', 'audit'):
        sub.add_parser(command)
    template = sub.add_parser('template')
    template.add_argument('stage', choices=STAGES)
    template.add_argument('--output', '--out', help='New project-relative report file')
    record = sub.add_parser('record')
    record.add_argument('stage', choices=STAGES)
    record.add_argument('report', nargs='?', help='Existing project-relative report JSON')
    record.add_argument('--artifact')
    authorize = sub.add_parser('authorize', help='Register specific permission already received; never grants permission itself')
    authorize.add_argument('action', nargs='?')
    authorize.add_argument('--action', dest='action_option')
    for name in ('target', 'source'):
        authorize.add_argument('--' + name, required=True)
    invalidate = sub.add_parser('invalidate')
    invalidate.add_argument('stage', choices=STAGES)
    invalidate.add_argument('--reason', default='Explicitly invalidated')
    mode = sub.add_parser('set-mode')
    mode.add_argument('mode', nargs='?', choices=MODES)
    mode.add_argument('--mode', dest='mode_option', choices=MODES)
    mode.add_argument('--source', default='Explicit CLI request')
    for command_parser in sub.choices.values():
        command_parser.add_argument('--project', default=argparse.SUPPRESS, help='Customer project root')
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result, code = Workflow(args.project).execute(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (WorkflowError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
