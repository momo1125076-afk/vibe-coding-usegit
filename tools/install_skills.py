#!/usr/bin/env python3
"""Project-scoped skill installer. Python 3.10+, standard library only.

Frontmatter is intentionally a small schema of flat single-line string scalars,
not a general YAML parser. No CLI installation, credentials, or host configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import uuid
import zipfile
from contextlib import contextmanager

NAMES = (
    'vibe-coding-usegit', 'usegit-discover', 'usegit-find-skills',
    'usegit-find-repos', 'usegit-evaluate', 'usegit-run', 'usegit-adapt',
    'usegit-deploy', 'usegit-verify',
)
HOSTS = {
    'codex': '.agents/skills', 'claude-code': '.claude/skills',
    'deepseek-harness': '.dsh/skills', 'openclaw': 'skills',
    'workbuddy': 'dist/workbuddy', 'hermes': '.hermes/skills',
}
FIELDS = {'name', 'description', 'display_name', 'display_name_en',
          'description_zh', 'description_en', 'version', 'author'}
SKIP = {'__pycache__'}
PRIVATE = {'.git', '.usegit', '.ssh', '.aws', '.env', '.npmrc', '.pypirc',
           'credentials.json', 'credentials', 'id_rsa', 'id_ed25519'}
ENGLISH = {
    'vibe-coding-usegit': ('Vibe Coding UseGit', 'Coordinate requirements, open-source selection, implementation and verified delivery.'),
    'usegit-discover': ('Discover requirements', 'Turn product ideas into scoped, testable requirements.'),
    'usegit-find-skills': ('Find capabilities', 'Find and verify optional skills, tools and integrations.'),
    'usegit-find-repos': ('Find repositories', 'Search GitHub and Gitee for reusable open-source projects.'),
    'usegit-evaluate': ('Evaluate candidates', 'Evaluate platform fit, licenses and implementation costs.'),
    'usegit-run': ('Run a project', 'Reproduce a selected project and retain real execution evidence.'),
    'usegit-adapt': ('Adapt a project', 'Implement requirement-linked changes in small verified steps.'),
    'usegit-deploy': ('Prepare delivery', 'Build, preview or deploy within explicitly authorized scope.'),
    'usegit-verify': ('Verify outcomes', 'Verify requirements and distinguish observed from simulated evidence.'),
}
CHINESE = {
    'vibe-coding-usegit': '开源产品交付调度', 'usegit-discover': '需求发现',
    'usegit-find-skills': '能力发现', 'usegit-find-repos': '开源检索',
    'usegit-evaluate': '候选评估', 'usegit-run': '首次运行',
    'usegit-adapt': '产品改造', 'usegit-deploy': '构建交付', 'usegit-verify': '验收验证',
}


class InstallError(ValueError):
    pass


def safe_path(value: str | Path) -> Path:
    """Reject traversal and all existing symlink ancestors before resolving."""
    p = Path(value).expanduser()
    if '..' in p.parts or (os.name != 'nt' and '\\' in str(p)):
        raise InstallError(f'Unsafe path: {value}')
    p = Path(os.path.abspath(p))
    for part in [p, *p.parents]:
        if part.is_symlink():
            raise InstallError(f'Symlink not allowed: {part}')
    return p


def relative_path(value: str) -> Path:
    p = Path(value)
    if not value or p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise InstallError(f'Unsafe relative path: {value}')
    return p


def tree_files(root: Path):
    """Enumerate only regular files; reject symlinks, private files and devices."""
    safe_path(root)
    if not root.is_dir():
        raise InstallError(f'Not a directory: {root}')
    result = []
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in list(dirs) + files:
            item = Path(base) / name
            if item.is_symlink():
                raise InstallError(f'Symlink not allowed: {item}')
            if name in PRIVATE or name.startswith('.env'):
                raise InstallError(f'Private file/directory is not distributable: {item}')
            if '\\' in name or ':' in name:
                raise InstallError(f'Non-portable path: {item}')
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        for name in sorted(files):
            p = Path(base) / name
            if not stat.S_ISREG(p.stat().st_mode):
                raise InstallError(f'Not a regular file: {p}')
            if not name.endswith(('.pyc', '.pyo')):
                result.append(p)
    return sorted(result)


def parse_frontmatter(text: str):
    lines = text.splitlines()
    if not lines or lines[0] != '---':
        raise InstallError('SKILL.md must begin with ---')
    try:
        end = lines.index('---', 1)
    except ValueError as exc:
        raise InstallError('Unclosed frontmatter') from exc
    fields = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        match = re.fullmatch(r'([a-z][a-z_]*):\s*(.+)', line)
        if not match:
            raise InstallError('Only flat single-line frontmatter string scalars are supported')
        key, value = match.groups()
        if key not in FIELDS or key in fields:
            raise InstallError(f'Unsupported or duplicate frontmatter key: {key}')
        if value.startswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise InstallError('Double-quoted scalars must use JSON string escaping') from exc
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("''", "'")
        elif value[0] in '|>{[&*!%@`' or ': ' in value or ' #' in value:
            raise InstallError('Unsupported YAML scalar; use a JSON-quoted string')
        if not isinstance(value, str) or not value.strip():
            raise InstallError(f'Empty or non-string field: {key}')
        fields[key] = value
    if not fields.get('name') or not fields.get('description'):
        raise InstallError('name and description are required')
    return fields, '\n'.join(lines[end + 1:]) + '\n'


def validate_source(source: Path, names):
    safe_path(source)
    for name in names:
        root = source / name
        files = tree_files(root)
        skill = root / 'SKILL.md'
        if skill not in files:
            raise InstallError(f'Missing {skill}')
        fields, _ = parse_frontmatter(skill.read_text(encoding='utf-8'))
        if fields['name'] != name:
            raise InstallError(f'name does not match directory: {name}')


def target_relative(host, name):
    return HOSTS[host] + '/' + name + ('.zip' if host == 'workbuddy' else '')


def fingerprint(path: Path):
    safe_path(path)
    if not path.exists():
        return None
    h = hashlib.sha256()
    if path.is_file():
        h.update(b'file\0')
        h.update(path.read_bytes())
    elif path.is_dir():
        for file in tree_files(path):
            name = file.relative_to(path).as_posix().encode()
            data = file.read_bytes()
            h.update(len(name).to_bytes(8, 'big'))
            h.update(name)
            h.update(len(data).to_bytes(8, 'big'))
            h.update(data)
    else:
        raise InstallError(f'Invalid target: {path}')
    return h.hexdigest()


def remove(path):
    safe_path(path)
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def copy_item(source, target):
    safe_path(source)
    safe_path(target)
    if source.is_dir():
        target.mkdir(parents=True, exist_ok=False)
        for file in tree_files(source):
            dest = target / file.relative_to(source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def render(source, target, name, host, version, author):
    if host != 'workbuddy':
        copy_item(source / name, target)
        return
    fields, body = parse_frontmatter((source / name / 'SKILL.md').read_text(encoding='utf-8'))
    fields.update(display_name=CHINESE[name], display_name_en=ENGLISH[name][0],
                  description_zh=fields['description'], description_en=ENGLISH[name][1],
                  version=version, author=author)
    content = '---\n' + ''.join(f'{k}: {json.dumps(v, ensure_ascii=False)}\n' for k, v in fields.items()) + '---\n' + body
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in tree_files(source / name):
            rel = file.relative_to(source / name).as_posix()
            entry = name + '/' + rel
            relative_path(entry)
            archive.writestr(entry, content if rel == 'SKILL.md' else file.read_bytes())


def write_json(path, value):
    temp = path.with_suffix('.tmp')
    safe_path(temp)
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


@contextmanager
def lock(project):
    control = project / '.usegit-installer'
    safe_path(control)
    control.mkdir(parents=True, exist_ok=True)
    lockfile = control / 'lock'
    safe_path(lockfile)
    try:
        fd = os.open(lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise InstallError('Installer is locked; do not remove a live process lock') from exc
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(str(os.getpid()))
        yield control
    finally:
        lockfile.unlink()


def validate_backup(project, backup_id, host):
    if not re.fullmatch(r'[a-f0-9]{32}', backup_id):
        raise InstallError('Invalid backup ID')
    backup = safe_path(project / '.usegit-installer' / 'backups' / backup_id)
    manifest_path = safe_path(backup / 'manifest.json')
    try:
        doc = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError('Backup manifest is missing or invalid') from exc
    if not isinstance(doc, dict):
        raise InstallError('Invalid backup manifest object')
    if doc.get('schema_version') != 1 or doc.get('host') != host or doc.get('status') != 'completed':
        raise InstallError('Backup host/status/schema mismatch; incomplete transactions require manual review')
    entries = doc.get('entries')
    if not isinstance(entries, list) or not entries:
        raise InstallError('Invalid backup entries')
    seen = set()
    for e in entries:
        if not isinstance(e, dict):
            raise InstallError('Invalid backup entry')
        name = e.get('name')
        if name not in NAMES or name in seen or e.get('target') != target_relative(host, name):
            raise InstallError('Invalid backup target')
        seen.add(name)
        actual = fingerprint(project / e['target'])
        if actual != e.get('after'):
            raise InstallError(f'Target changed since backup; preserve edits before restoring: {name}')
        original = backup / 'original' / name
        if fingerprint(original) != e.get('before'):
            raise InstallError(f'Backup content changed: {name}')
    return backup, doc


def transact(project, host, names, desired, overwrite=False):
    """desired(name, staged_path) builds a replacement, or leaves it absent."""
    with lock(project) as control:
        # Revalidate after locking, then stage without touching live skill paths.
        entries = []
        for name in names:
            target = project / target_relative(host, name)
            before = fingerprint(target)
            if before is not None and not overwrite:
                raise InstallError(f'Target already exists: {target}; use --overwrite')
            entries.append({'name': name, 'target': target_relative(host, name), 'before': before})
        with tempfile.TemporaryDirectory(prefix='stage-', dir=control) as tmp:
            stage = Path(tmp)
            for e in entries:
                desired(e['name'], stage / e['name'])
                e['after'] = fingerprint(stage / e['name'])
            backup_id = uuid.uuid4().hex
            backup = safe_path(control / 'backups' / backup_id)
            backup.mkdir(parents=True)
            for e in entries:
                if e['before'] is not None:
                    copy_item(project / e['target'], backup / 'original' / e['name'])
            doc = {'schema_version': 1, 'host': host, 'status': 'prepared', 'entries': entries}
            write_json(backup / 'manifest.json', doc)
            touched = []
            try:
                for e in entries:
                    target = safe_path(project / e['target'])
                    if fingerprint(target) != e['before']:
                        raise InstallError(f'Target changed during install: {target}')
                    touched.append(e)
                    remove(target)
                    staged = stage / e['name']
                    if staged.exists():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(staged, target)
                doc['status'] = 'completed'
                write_json(backup / 'manifest.json', doc)
            except Exception:
                for e in reversed(touched):
                    target = project / e['target']
                    remove(target)
                    if e['before'] is not None:
                        copy_item(backup / 'original' / e['name'], target)
                doc['status'] = 'rolled-back'
                write_json(backup / 'manifest.json', doc)
                raise
            return backup_id


def execute(args):
    project = safe_path(args.project)
    source = safe_path(args.source)
    names = args.skill or list(NAMES)
    if len(names) != len(set(names)):
        raise InstallError('Duplicate skill selection')
    if project == Path.home() or project == Path(project.anchor):
        raise InstallError('Choose an isolated project, not a home or filesystem root')
    destination = project / HOSTS[args.host]
    safe_path(destination)
    if source == destination or source in destination.parents or destination in source.parents:
        raise InstallError('Source and destination must be separate trees')
    restoring = None
    if args.restore:
        restoring = validate_backup(project, args.restore, args.host)
        names = [e['name'] for e in restoring[1]['entries']]
    elif not args.uninstall:
        validate_source(source, names)
        if args.host == 'workbuddy':
            if not args.author or not args.version:
                raise InstallError('WorkBuddy requires explicit --author and --version')
            if not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?', args.version):
                raise InstallError('Use a semantic version such as 0.2.0')
            if not args.author.strip() or '\n' in args.author:
                raise InstallError('Author must be a nonempty single-line attribution')
    targets = []
    for name in names:
        target = project / target_relative(args.host, name)
        existing = fingerprint(target)
        if existing is not None and not (args.overwrite or args.uninstall or args.restore):
            raise InstallError(f'Target already exists: {target}; use --overwrite')
        targets.append({'name': name, 'path': str(target), 'exists': existing is not None})
    result = {'host': args.host, 'operation': 'restore' if args.restore else 'uninstall' if args.uninstall else 'install',
              'dry_run': not args.apply, 'targets': targets}
    if args.host == 'hermes':
        result['warnings'] = [
            'Hermes discovers project skills at the nearest .git ancestor. '
            'Set --project to that Git project root; this installer does not initialize Git.',
            'Hermes requires explicit project trust. Review the installed skills, then '
            'run hermes skills trust yourself from the project. This installer never '
            'runs trust or changes host configuration.',
        ]
    if not args.apply:
        return result
    if restoring:
        backup, doc = restoring
        def desired(name, dest):
            # Validate again under lock before each file is copied.
            validate_backup(project, args.restore, args.host)
            old = backup / 'original' / name
            if old.exists():
                copy_item(old, dest)
    elif args.uninstall:
        def desired(name, dest):
            pass
    else:
        def desired(name, dest):
            render(source, dest, name, args.host, args.version, args.author)
    result['backup_id'] = transact(project, args.host, names, desired,
                                    args.overwrite or args.uninstall or bool(args.restore))
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host', required=True, choices=HOSTS)
    p.add_argument('--project', required=True, help='Isolated project / OpenClaw workspace / package output root')
    p.add_argument('--source', default=str(Path(__file__).resolve().parents[1] / 'skills'))
    p.add_argument('--skill', action='append', choices=NAMES, help='Repeat to select skills; default: all nine')
    p.add_argument('--apply', action='store_true', help='Write changes (default is read-only dry-run)')
    p.add_argument('--overwrite', action='store_true', help='Back up conflicting targets before replacing')
    p.add_argument('--version', help='Explicit WorkBuddy package semantic version')
    p.add_argument('--author', help='Explicit true author attribution; never inferred from host vendor')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--uninstall', action='store_true', help='Remove selected targets with recoverable backup')
    mode.add_argument('--restore', metavar='BACKUP_ID', help='Restore an unchanged completed transaction')
    return p


def main(argv=None):
    try:
        result = execute(parser().parse_args(argv))
    except (InstallError, OSError, UnicodeError, KeyError, TypeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({'ok': True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
