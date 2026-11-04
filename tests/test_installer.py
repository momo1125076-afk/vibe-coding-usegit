"""Static installer tests. These do not launch or certify any host application."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

MODULE = Path(__file__).resolve().parents[1] / 'tools' / 'install_skills.py'
spec = importlib.util.spec_from_file_location('usegit_installer', MODULE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='usegit installer 中文 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source' / 'skills'
        self.project = self.root / '客户 project'
        for name in installer.NAMES:
            p = self.source / name
            (p / 'references').mkdir(parents=True)
            (p / 'scripts').mkdir()
            (p / 'SKILL.md').write_text('---\nname: ' + name + '\ndescription: "测试自包含技能"\n---\nUse references/guide.md and scripts/probe.py.\n', encoding='utf-8')
            (p / 'references' / 'guide.md').write_text('本地资源\n', encoding='utf-8')
            (p / 'scripts' / 'probe.py').write_text('from pathlib import Path\nprint((Path(__file__).parent.parent / "references/guide.md").read_text(encoding="utf-8"))\n', encoding='utf-8')

    def args(self, host='codex', *more):
        return installer.parser().parse_args(['--host', host, '--project', str(self.project), '--source', str(self.source), *more])

    def run_install(self, host='codex', *more):
        return installer.execute(self.args(host, *more))

    def target(self, name=None, host='codex'):
        return self.project / installer.target_relative(host, name or installer.NAMES[0])

    def test_default_dry_run_creates_nothing(self):
        result = self.run_install()
        self.assertTrue(result['dry_run'])
        self.assertEqual(len(result['targets']), 9)
        self.assertFalse(self.project.exists())

    def test_five_hosts_nine_independent_packages(self):
        for host in installer.HOSTS:
            with self.subTest(host=host):
                extra = ['--version', '0.2.0', '--author', 'Fixture author'] if host == 'workbuddy' else []
                self.run_install(host, '--apply', *extra)
                target_root = self.project / installer.HOSTS[host]
                self.assertEqual(len(list(target_root.iterdir())), 9)
                for name in installer.NAMES:
                    p = self.target(name, host)
                    if host == 'workbuddy':
                        with zipfile.ZipFile(p) as z:
                            self.assertEqual(set(z.namelist()), {name + '/SKILL.md', name + '/references/guide.md', name + '/scripts/probe.py'})
                            fields, _ = installer.parse_frontmatter(z.read(name + '/SKILL.md').decode())
                            self.assertEqual(set(fields), installer.FIELDS)
                            self.assertEqual(fields['version'], '0.2.0')
                            self.assertEqual(fields['author'], 'Fixture author')
                            self.assertEqual(fields['name'], name)
                    else:
                        self.assertTrue((p / 'SKILL.md').is_file())
                        self.assertEqual((p / 'references/guide.md').read_text(), '本地资源\n')

    def test_installed_resources_run_without_source(self):
        for host in ('codex', 'claude-code', 'deepseek-harness', 'openclaw'):
            self.run_install(host, '--apply')
        moved = self.source.parent / 'hidden'
        self.source.rename(moved)
        for host in ('codex', 'claude-code', 'deepseek-harness', 'openclaw'):
            run = subprocess.run([sys.executable, str(self.target(host=host) / 'scripts/probe.py')], cwd=self.root, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('本地资源', run.stdout)

    def test_repeat_requires_overwrite(self):
        self.run_install('codex', '--apply')
        with self.assertRaisesRegex(installer.InstallError, 'already exists'):
            self.run_install('codex', '--apply')

    def test_overwrite_backup_and_restore(self):
        self.run_install('codex', '--apply')
        original = (self.target() / 'SKILL.md').read_bytes()
        source_file = self.source / installer.NAMES[0] / 'SKILL.md'
        source_file.write_bytes(source_file.read_bytes() + b'\nUpdated.\n')
        result = self.run_install('codex', '--apply', '--overwrite')
        self.assertNotEqual((self.target() / 'SKILL.md').read_bytes(), original)
        self.run_install('codex', '--apply', '--restore', result['backup_id'])
        self.assertEqual((self.target() / 'SKILL.md').read_bytes(), original)

    def test_restore_fresh_install_removes_only_installed_targets(self):
        result = self.run_install('codex', '--apply')
        unrelated = self.target().parent / 'unrelated'
        unrelated.mkdir()
        (unrelated / 'keep').write_text('keep')
        self.run_install('codex', '--apply', '--restore', result['backup_id'])
        self.assertFalse(self.target().exists())
        self.assertTrue((unrelated / 'keep').exists())

    def test_restore_preserves_post_install_edits(self):
        result = self.run_install('codex', '--apply')
        (self.target() / 'SKILL.md').write_text('user edits')
        with self.assertRaisesRegex(installer.InstallError, 'changed since backup'):
            self.run_install('codex', '--apply', '--restore', result['backup_id'])
        self.assertEqual((self.target() / 'SKILL.md').read_text(), 'user edits')

    def test_uninstall_is_dry_run_then_recoverable(self):
        self.run_install('claude-code', '--apply')
        self.run_install('claude-code', '--uninstall')
        self.assertTrue(self.target(host='claude-code').exists())
        result = self.run_install('claude-code', '--uninstall', '--apply')
        self.assertFalse(self.target(host='claude-code').exists())
        self.run_install('claude-code', '--restore', result['backup_id'], '--apply')
        self.assertTrue(self.target(host='claude-code').exists())

    def test_failure_rolls_back_every_changed_target(self):
        self.run_install('codex', '--apply')
        before = {name: installer.fingerprint(self.target(name)) for name in installer.NAMES}
        for name in installer.NAMES:
            (self.source / name / 'references/guide.md').write_text('new')
        replace = installer.os.replace
        calls = 0
        def fail_third(src, dst):
            nonlocal calls
            if Path(dst).name in installer.NAMES:
                calls += 1
                if calls == 3:
                    raise OSError('simulated disk failure')
            return replace(src, dst)
        with mock.patch.object(installer.os, 'replace', side_effect=fail_third):
            with self.assertRaisesRegex(OSError, 'simulated disk failure'):
                self.run_install('codex', '--apply', '--overwrite')
        self.assertEqual(before, {name: installer.fingerprint(self.target(name)) for name in installer.NAMES})

    def test_failed_fresh_install_removes_partial_targets(self):
        replace = installer.os.replace
        def fail(src, dst):
            if Path(dst).name == installer.NAMES[1]:
                raise OSError('disk failure')
            return replace(src, dst)
        with mock.patch.object(installer.os, 'replace', side_effect=fail):
            with self.assertRaises(OSError):
                self.run_install('codex', '--apply')
        for name in installer.NAMES:
            self.assertFalse(self.target(name).exists())

    def test_source_symlink_rejected(self):
        (self.source / installer.NAMES[0] / 'references/link').symlink_to(self.root)
        with self.assertRaisesRegex(installer.InstallError, 'Symlink'):
            self.run_install('codex', '--apply')
        self.assertFalse(self.project.exists())

    def test_broken_symlink_rejected(self):
        (self.source / installer.NAMES[0] / 'references/broken').symlink_to(self.root / 'missing')
        with self.assertRaisesRegex(installer.InstallError, 'Symlink'):
            self.run_install()

    def test_target_ancestor_symlink_rejected(self):
        self.project.mkdir()
        (self.project / '.agents').symlink_to(self.root / 'elsewhere')
        with self.assertRaisesRegex(installer.InstallError, 'Symlink'):
            self.run_install('codex', '--apply')

    def test_target_child_symlink_rejected_before_overwrite(self):
        self.run_install('codex', '--apply')
        (self.target() / 'link').symlink_to(self.root)
        with self.assertRaisesRegex(installer.InstallError, 'Symlink'):
            self.run_install('codex', '--apply', '--overwrite')

    def test_traversal_project_rejected(self):
        args = self.args()
        args.project = str(self.root / 'safe' / '..' / 'escaped')
        with self.assertRaisesRegex(installer.InstallError, 'Unsafe'):
            installer.execute(args)

    def test_zip_relative_paths_reject_escape_and_windows(self):
        for path in ('../file', '/etc/passwd', 'C:\\temp\\evil', 'name/../../evil', 'name\\..\\evil'):
            with self.subTest(path=path), self.assertRaises(installer.InstallError):
                installer.relative_path(path)

    def test_nonportable_resource_name_rejected(self):
        (self.source / installer.NAMES[0] / 'references/C:secret').write_text('bad')
        with self.assertRaisesRegex(installer.InstallError, 'Non-portable'):
            self.run_install()

    def test_private_files_rejected(self):
        for name in ('.env', '.env.local', 'credentials.json'):
            with self.subTest(name=name):
                file = self.source / installer.NAMES[0] / name
                file.write_text('not a real secret')
                with self.assertRaisesRegex(installer.InstallError, 'Private'):
                    self.run_install()
                file.unlink()

    def test_workbuddy_requires_true_author_and_version(self):
        for flags in ([], ['--version', '0.2.0'], ['--author', 'Fixture author'], ['--version', 'bad', '--author', 'Fixture author']):
            with self.subTest(flags=flags), self.assertRaises(installer.InstallError):
                self.run_install('workbuddy', *flags)

    def test_workbuddy_dry_run_no_output(self):
        self.run_install('workbuddy', '--version', '0.2.0', '--author', 'Fixture author')
        self.assertFalse(self.project.exists())

    def test_name_must_match_directory(self):
        p = self.source / installer.NAMES[0] / 'SKILL.md'
        p.write_text('---\nname: other\ndescription: test\n---\n')
        with self.assertRaisesRegex(installer.InstallError, 'match'):
            self.run_install()

    def test_reject_unsupported_yaml_and_permission_fields(self):
        for extra in ('allowed-tools: Bash\n', 'description: |\n  text\n', 'metadata:\n  nested: yes\n', 'name: duplicate\n'):
            text = '---\nname: test\ndescription: safe\n' + extra + '---\nbody\n'
            with self.subTest(extra=extra), self.assertRaises(installer.InstallError):
                installer.parse_frontmatter(text)

    def test_frontmatter_quotes_and_unicode(self):
        fields, body = installer.parse_frontmatter('---\nname: test\ndescription: "中文: quote \\""\n---\nbody\n')
        self.assertEqual(fields['description'], '中文: quote "')
        self.assertEqual(body, 'body\n')

    def test_missing_skill_rejected_before_writes(self):
        (self.source / installer.NAMES[-1] / 'SKILL.md').unlink()
        with self.assertRaisesRegex(installer.InstallError, 'Missing'):
            self.run_install('codex', '--apply')
        self.assertFalse(self.project.exists())

    def test_selected_skill_only(self):
        self.run_install('codex', '--apply', '--skill', installer.NAMES[0])
        self.assertEqual([p.name for p in self.target().parent.iterdir()], [installer.NAMES[0]])

    def test_cache_excluded(self):
        cache = self.source / installer.NAMES[0] / '__pycache__'
        cache.mkdir()
        (cache / 'thing.pyc').write_bytes(b'cache')
        self.run_install('codex', '--apply')
        self.assertFalse((self.target() / '__pycache__').exists())

    def test_concurrent_lock_rejected(self):
        control = self.project / '.usegit-installer'
        control.mkdir(parents=True)
        (control / 'lock').write_text('existing')
        with self.assertRaisesRegex(installer.InstallError, 'locked'):
            self.run_install('codex', '--apply')
        self.assertEqual((control / 'lock').read_text(), 'existing')

    def test_source_destination_overlap_rejected(self):
        args = self.args('openclaw')
        args.project = str(self.source.parent)
        with self.assertRaisesRegex(installer.InstallError, 'separate'):
            installer.execute(args)

    def test_manifest_traversal_rejected(self):
        result = self.run_install('codex', '--apply')
        manifest = self.project / '.usegit-installer/backups' / result['backup_id'] / 'manifest.json'
        doc = json.loads(manifest.read_text())
        doc['entries'][0]['target'] = '../../escaped'
        manifest.write_text(json.dumps(doc))
        with self.assertRaisesRegex(installer.InstallError, 'Invalid backup target'):
            self.run_install('codex', '--restore', result['backup_id'], '--apply')

    def test_backup_id_traversal_rejected(self):
        with self.assertRaisesRegex(installer.InstallError, 'Invalid backup ID'):
            self.run_install('codex', '--restore', '../elsewhere')

    def test_changed_backup_rejected(self):
        self.run_install('codex', '--apply')
        result = self.run_install('codex', '--apply', '--overwrite')
        backup = self.project / '.usegit-installer/backups' / result['backup_id'] / 'original' / installer.NAMES[0]
        (backup / 'SKILL.md').write_text('tampered')
        with self.assertRaisesRegex(installer.InstallError, 'Backup content changed'):
            self.run_install('codex', '--restore', result['backup_id'])

    def test_backup_parent_symlink_rejected(self):
        control = self.project / '.usegit-installer'
        control.mkdir(parents=True)
        outside = self.root / 'outside'
        outside.mkdir()
        (control / 'backups').symlink_to(outside)
        with self.assertRaisesRegex(installer.InstallError, 'Symlink'):
            self.run_install('codex', '--apply')
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse(self.target().exists())

    def test_source_ancestor_symlink_rejected(self):
        linked = self.root / 'linked-source'
        linked.symlink_to(self.source.parent)
        args = self.args()
        args.source = str(linked / 'skills')
        with self.assertRaisesRegex(installer.InstallError, 'Symlink'):
            installer.execute(args)

    def test_staging_failure_leaves_existing_targets(self):
        self.run_install('codex', '--apply')
        before = installer.fingerprint(self.target())
        with mock.patch.object(installer, 'render', side_effect=OSError('staging failure')):
            with self.assertRaisesRegex(OSError, 'staging failure'):
                self.run_install('codex', '--apply', '--overwrite')
        self.assertEqual(installer.fingerprint(self.target()), before)

    def test_restore_wrong_host_rejected(self):
        result = self.run_install('codex', '--apply')
        with self.assertRaisesRegex(installer.InstallError, 'host/status/schema'):
            self.run_install('claude-code', '--restore', result['backup_id'])

    def test_cli_json_exit_codes(self):
        args = ['--host', 'codex', '--source', str(self.source), '--project', str(self.project)]
        p = subprocess.run([sys.executable, str(MODULE), *args], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(json.loads(p.stdout)['dry_run'])
        (self.source / installer.NAMES[0] / 'SKILL.md').unlink()
        p = subprocess.run([sys.executable, str(MODULE), *args], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertFalse(json.loads(p.stderr)['ok'])


if __name__ == '__main__':
    unittest.main()
