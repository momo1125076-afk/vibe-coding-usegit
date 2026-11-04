"""Local, isolated workflow tests; never deploy or make network requests."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'tools' / 'usegit.py'
spec = importlib.util.spec_from_file_location('usegit_workflow', SCRIPT)
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='UseGit 中文 space ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.w = u.Workflow(self.root)
        self.w.init()
        (self.root / 'evidence.txt').write_text('real test fixture\n', encoding='utf-8')

    def cli(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = u.main(['--project', str(self.root), *args])
        return code, json.loads(stdout.getvalue() or stderr.getvalue())

    def report(self, stage, status='complete'):
        result = self.w.template(stage)
        result.update(status=status, summary='Test report', blockers=[], outputs=[{'path': 'evidence.txt', 'description': 'Fixture'}],
                      evidence=[{'id': 'E-001', 'kind': 'file', 'verification': 'observed', 'claim': 'Fixture inspected', 'path': 'evidence.txt'}])
        if stage in ('run', 'deploy'):
            result['evidence'] = [{'id': 'E-001', 'kind': 'command', 'verification': 'observed', 'claim': 'Test command', 'command': 'python -V',
                                   'environment': 'isolated unittest fixture', 'observed_at': u.now(), 'exit_code': 0,
                                   'path': 'evidence.txt', 'commit': 'unversioned fixture'}]
        if stage == 'verify':
            result['checks'] = [{'requirement_id': 'REQ-001', 'result': 'pass', 'evidence_ids': ['E-001']}]
        return result

    def write_report(self, stage, report=None):
        name = stage + '.json'
        (self.root / name).write_text(json.dumps(report or self.report(stage)), encoding='utf-8')
        return name

    def record(self, stage, report=None):
        return self.cli('record', stage, '--artifact', self.write_report(stage, report))

    def through(self, last):
        for stage in ('discover', 'find-skills', 'find-repos', 'evaluate', 'run', 'adapt', 'verify'):
            code, result = self.record(stage)
            self.assertEqual(code, 0, result)
            if stage == last:
                return

    def test_init_defaults_and_ignore(self):
        state = self.w.load()
        self.assertEqual(state['mode'], 'local')
        self.assertEqual(state['stages']['deploy']['status'], 'not-required')
        self.assertIn('*', (self.root / '.usegit/.gitignore').read_text())

    def test_repeat_init_preserves_original(self):
        original = self.w.state_path.read_bytes()
        self.assertEqual(self.cli('init')[0], 2)
        self.assertEqual(original, self.w.state_path.read_bytes())

    def test_complete_local(self):
        self.through('verify')
        self.assertTrue(self.cli('status')[1]['complete_for_mode'])

    def test_complete_plan(self):
        self.assertEqual(self.cli('set-mode', '--mode', 'plan', '--source', 'user request')[0], 0)
        self.through('evaluate')
        self.assertTrue(self.cli('status')[1]['complete_for_mode'])
        self.assertEqual(self.record('run')[0], 2)

    def test_dependencies(self):
        self.assertEqual(self.record('evaluate')[0], 2)
        self.assertEqual(self.record('run')[0], 2)
        self.assertEqual(self.cli('next')[1]['next'], ['discover'])

    def test_parallel_search_dependencies(self):
        self.record('discover')
        self.assertEqual(self.cli('next')[1]['next'], ['find-skills', 'find-repos'])
        self.record('find-repos')
        self.assertEqual(self.record('evaluate')[0], 2)

    def test_only_allowed_skips(self):
        self.record('discover')
        self.assertEqual(self.record('find-skills', self.report('find-skills', 'skipped'))[0], 0)
        self.assertEqual(self.record('find-repos', self.report('find-repos', 'skipped'))[0], 2)

    def test_blockers_prevent_completion(self):
        report = self.report('discover')
        report['blockers'] = ['missing scope']
        self.assertEqual(self.record('discover', report)[0], 2)

    def test_failed_report_allowed(self):
        report = self.report('discover', 'failed')
        report['blockers'] = [{'reason': 'Needs input', 'next_action': 'Ask user'}]
        self.assertEqual(self.record('discover', report)[0], 0)
        self.assertFalse(self.cli('status')[1]['complete_for_mode'])

    def test_duplicate_requirement_ids(self):
        report = self.report('discover')
        report['requirements'] *= 2
        self.assertEqual(self.record('discover', report)[0], 2)

    def test_requirement_acceptance_required(self):
        report = self.report('discover')
        del report['requirements'][0]['acceptance']
        self.assertEqual(self.record('discover', report)[0], 2)

    def test_complete_needs_evidence(self):
        report = self.report('discover')
        report['evidence'] = []
        self.assertEqual(self.record('discover', report)[0], 2)

    def test_invalid_evidence_class(self):
        report = self.report('discover')
        report['evidence'][0]['kind'] = 'probably-real'
        self.assertEqual(self.record('discover', report)[0], 2)

    def test_run_requires_observed_success(self):
        self.through('evaluate')
        for field, value in [('verification', 'simulated'), ('verification', 'not-run'), ('exit_code', 1), ('exit_code', True)]:
            with self.subTest(field=field, value=value):
                report = self.report('run')
                report['evidence'][0][field] = value
                self.assertEqual(self.record('run', report)[0], 2)

    def test_run_command_metadata_required(self):
        self.through('evaluate')
        for field in ('environment', 'observed_at', 'path'):
            report = self.report('run')
            del report['evidence'][0][field]
            self.assertEqual(self.record('run', report)[0], 2)

    def test_verify_must_observed_pass(self):
        self.through('adapt')
        for status in ('not-applicable', 'not-run', 'fail'):
            report = self.report('verify')
            report['checks'][0]['result'] = status
            self.assertEqual(self.record('verify', report)[0], 2)
        report = self.report('verify')
        report['evidence'][0]['verification'] = 'simulated'
        self.assertEqual(self.record('verify', report)[0], 2)

    def test_verify_missing_must(self):
        self.through('adapt')
        report = self.report('verify')
        report['checks'] = []
        self.assertEqual(self.record('verify', report)[0], 2)

    def test_path_escape(self):
        for path in ('../outside.txt', '/etc/passwd', 'sub/../../outside', 'sub\\outside'):
            report = self.report('discover')
            report['outputs'] = [path]
            self.assertEqual(self.record('discover', report)[0], 2)

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / 'secret.txt'
            external.write_text('not read')
            (self.root / 'escape.txt').symlink_to(external)
            report = self.report('discover')
            report['outputs'] = ['escape.txt']
            self.assertEqual(self.record('discover', report)[0], 2)

    def test_state_not_business_evidence(self):
        report = self.report('discover')
        report['outputs'] = ['.usegit/state.json']
        self.assertEqual(self.record('discover', report)[0], 2)
        (self.root / 'alias.json').symlink_to(self.w.state_path)
        report['outputs'] = ['alias.json']
        self.assertEqual(self.record('discover', report)[0], 2)

    def test_output_missing(self):
        report = self.report('discover')
        report['outputs'] = ['missing.txt']
        self.assertEqual(self.record('discover', report)[0], 2)

    def test_hash_mutation_audit(self):
        self.through('verify')
        (self.root / 'evidence.txt').write_text('changed')
        code, report = self.cli('audit')
        self.assertEqual(code, 2)
        self.assertEqual(report['stages']['discover'], 'stale')
        self.assertEqual(report['stages']['verify'], 'stale')
        self.assertFalse(report['complete_for_mode'])

    def test_deleted_evidence_audit(self):
        self.record('discover')
        (self.root / 'evidence.txt').unlink()
        self.assertEqual(self.cli('audit')[0], 2)

    def test_report_mutation_status(self):
        self.record('discover')
        path = self.root / 'discover.json'
        path.write_text(path.read_text() + '\n')
        self.assertEqual(self.cli('status')[1]['stages']['discover'], 'stale')

    def test_invalidate_descendants(self):
        self.through('verify')
        self.cli('invalidate', 'run', '--reason', 'source updated')
        statuses = self.cli('status')[1]['stages']
        self.assertEqual(statuses['evaluate'], 'complete')
        self.assertEqual(statuses['verify'], 'stale')

    def test_mode_does_not_authorize(self):
        self.through('adapt')
        self.cli('set-mode', 'release')
        report = self.report('deploy')
        report['executed_actions'] = [{'action': 'preview-deploy', 'target': 'test.example'}]
        self.assertEqual(self.record('deploy', report)[0], 2)
        self.assertEqual(self.w.load()['authorizations'], [])

    def test_authorization_exact_target(self):
        self.through('adapt')
        self.cli('set-mode', 'preview')
        self.assertEqual(self.cli('authorize', 'preview-deploy', '--target', 'preview.example', '--source', 'user message 123')[0], 0)
        report = self.report('deploy')
        report['executed_actions'] = [{'action': 'preview-deploy', 'target': 'production.example'}]
        self.assertEqual(self.record('deploy', report)[0], 2)
        report['executed_actions'][0]['target'] = 'preview.example'
        self.assertEqual(self.record('deploy', report)[0], 0)
        self.assertEqual(self.record('verify')[0], 0)
        self.assertTrue(self.cli('status')[1]['complete_for_mode'])

    def test_deploy_screenshot_not_sufficient(self):
        self.through('adapt')
        self.cli('set-mode', 'preview')
        report = self.report('deploy')
        report['evidence'] = self.report('discover')['evidence']
        self.assertEqual(self.record('deploy', report)[0], 2)

    def test_lock_no_state_mutation(self):
        before = self.w.state_path.read_bytes()
        with self.w.locked():
            self.assertEqual(self.cli('invalidate', 'discover')[0], 2)
        self.assertEqual(before, self.w.state_path.read_bytes())
        self.assertFalse((self.w.directory / 'state.lock').exists())

    def test_lock_released_on_error(self):
        self.assertEqual(self.record('verify')[0], 2)
        self.assertFalse((self.w.directory / 'state.lock').exists())

    def test_oversize_read_preserves_state(self):
        before = self.w.state_path.read_bytes()
        (self.root / 'large.json').write_text(' ' * (u.MAX_JSON + 1))
        self.assertEqual(self.cli('record', 'discover', 'large.json')[0], 2)
        self.assertEqual(before, self.w.state_path.read_bytes())

    def test_oversize_write_preserves_original(self):
        before = self.w.state_path.read_bytes()
        with self.assertRaises(u.WorkflowError):
            u.atomic_json(self.w.state_path, {'huge': 'x' * u.MAX_JSON})
        self.assertEqual(before, self.w.state_path.read_bytes())

    def test_atomic_replace_failure_preserves_original(self):
        before = self.w.state_path.read_bytes()
        with patch.object(u.os, 'replace', side_effect=OSError('injected failure')):
            self.assertEqual(self.cli('invalidate', 'discover')[0], 2)
        self.assertEqual(before, self.w.state_path.read_bytes())
        self.assertFalse(list(self.w.directory.glob('.state.json.*')))

    def test_template_does_not_overwrite(self):
        self.assertEqual(self.cli('template', 'discover', '--out', 'reports/需求.json')[0], 0)
        self.assertEqual(self.cli('template', 'discover', '--out', 'reports/需求.json')[0], 2)
        self.assertEqual(self.cli('record', 'discover', 'reports/需求.json')[0], 0)
        self.assertFalse(self.cli('status')[1]['complete_for_mode'])

    def test_template_escape_rejected(self):
        self.assertEqual(self.cli('template', 'discover', '--out', '../outside.json')[0], 2)
        self.assertEqual(self.cli('template', 'discover', '--out', '.usegit/state.json')[0], 2)

    def test_doctor_does_not_claim_auth(self):
        code, result = self.cli('doctor')
        self.assertEqual(code, 0)
        self.assertEqual(result['authentication'], 'untested')
        self.assertTrue(all(x['status'] in ('untested', 'unavailable') for x in result['tools'].values()))

    def test_project_after_command_subprocess(self):
        result = subprocess.run([sys.executable, str(SCRIPT), 'status', '--project', str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['mode'], 'local')

    def test_malformed_json_and_missing_report(self):
        (self.root / 'bad.json').write_text('{')
        self.assertEqual(self.cli('record', 'discover', 'bad.json')[0], 2)
        self.assertEqual(self.cli('record', 'discover')[0], 2)

    def test_duplicate_evidence_ids_rejected(self):
        report = self.report('discover')
        report['evidence'] *= 2
        self.assertEqual(self.record('discover', report)[0], 2)

    def test_checks_reference_existing_evidence(self):
        self.through('adapt')
        report = self.report('verify')
        report['checks'][0]['evidence_ids'] = ['not-present']
        self.assertEqual(self.record('verify', report)[0], 2)

    def test_failed_command_cannot_support_pass(self):
        self.through('adapt')
        report = self.report('verify')
        report['evidence'] = self.report('run')['evidence']
        report['evidence'][0]['exit_code'] = 1
        self.assertEqual(self.record('verify', report)[0], 2)

    def test_complete_cannot_have_untested_check(self):
        report = self.report('discover')
        report['checks'] = [{'requirement_id': 'REQ-001', 'result': 'not-run', 'evidence_ids': []}]
        self.assertEqual(self.record('discover', report)[0], 2)

    def test_skipped_requires_observed_evidence(self):
        self.record('discover')
        report = self.report('find-skills', 'skipped')
        report['evidence'][0]['verification'] = 'simulated'
        self.assertEqual(self.record('find-skills', report)[0], 2)

    def test_unknown_action_cannot_evade_authorization(self):
        report = self.report('discover')
        report['executed_actions'] = [{'action': 'anything', 'target': 'production'}]
        self.assertEqual(self.record('discover', report)[0], 2)

    def test_url_cannot_embed_credentials(self):
        report = self.report('discover')
        report['evidence'] = [{'id': 'URL-1', 'kind': 'url', 'claim': 'Observed page', 'verification': 'observed',
                               'url': 'https://user:secret@example.org', 'environment': 'test', 'observed_at': u.now()}]
        self.assertEqual(self.record('discover', report)[0], 2)

    def test_standalone_script_copy(self):
        standalone = self.root / 'standalone.py'
        standalone.write_bytes(SCRIPT.read_bytes())
        result = subprocess.run([sys.executable, str(standalone), 'status', '--project', str(self.root)],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['next'], ['discover'])

    def test_lock_across_processes(self):
        with self.w.locked():
            result = subprocess.run([sys.executable, str(SCRIPT), 'invalidate', 'discover', '--project', str(self.root)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('locked', json.loads(result.stderr)['error'])

    def test_next_refreshes_integrity(self):
        self.record('discover')
        (self.root / 'evidence.txt').write_text('new content')
        self.assertEqual(self.cli('next')[1]['next'], ['discover'])

    def test_authorization_alias_and_duplicate(self):
        args = ('authorize', '--action', 'preview-deploy', '--target', 'exact preview', '--source', 'message 1')
        self.assertEqual(self.cli(*args)[0], 0)
        self.assertEqual(self.cli(*args)[0], 0)
        self.assertEqual(len(self.w.load()['authorizations']), 1)

    def test_mode_change_invalidates_verification(self):
        self.through('verify')
        self.cli('set-mode', '--mode', 'release')
        result = self.cli('status')[1]
        self.assertFalse(result['complete_for_mode'])
        self.assertEqual(result['stages']['verify'], 'stale')
        self.assertEqual(result['next'], ['deploy'])

    def test_readme_full_init_and_stage_commands(self):
        project = self.root / '客户 项目'
        args = ['init', '--project', str(project), '--name', 'booking', '--idea', '微信预约与网页后台，首版不支付',
                '--platform', 'wechat-miniprogram', '--platform', 'web', '--platform', 'backend', '--mode', 'plan']
        result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        workflow = u.Workflow(project)
        self.assertEqual(workflow.load()['project'], {'name': 'booking', 'idea': '微信预约与网页后台，首版不支付',
                                                     'platforms': ['wechat-miniprogram', 'web', 'backend']})
        self.assertTrue((project / '.usegit/artifacts').is_dir())
        self.assertTrue((project / '.usegit/evidence').is_dir())
        for args in [('next',), ('template', 'discover', '--out', '.usegit/artifacts/discover.json'),
                     ('record', 'discover', '--artifact', '.usegit/artifacts/discover.json')]:
            result = subprocess.run([sys.executable, str(SCRIPT), *args, '--project', str(project)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(workflow.load()['stages']['discover']['status'], 'blocked')

    def test_internal_artifact_and_evidence_paths(self):
        evidence = self.root / '.usegit/evidence/interview.txt'
        evidence.write_text('Customer confirmed requirements')
        report = self.report('discover')
        report['outputs'][0]['path'] = '.usegit/evidence/interview.txt'
        report['evidence'][0]['path'] = '.usegit/evidence/interview.txt'
        (self.root / '.usegit/artifacts/discover.json').write_text(json.dumps(report))
        self.assertEqual(self.cli('record', 'discover', '--artifact', '.usegit/artifacts/discover.json')[0], 0)
        evidence.write_text('changed requirements')
        self.assertEqual(self.cli('audit')[0], 2)

    def test_artifact_symlink_to_state_rejected(self):
        alias = self.root / '.usegit/artifacts/state-alias.json'
        alias.symlink_to(self.w.state_path)
        report = self.report('discover')
        report['outputs'] = [str(alias.relative_to(self.root))]
        self.assertEqual(self.record('discover', report)[0], 2)

    def test_internal_artifact_directory_symlink_rejected(self):
        artifacts = self.root / '.usegit/artifacts'
        artifacts.rmdir()
        artifacts.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(self.cli('template', 'discover', '--out', '.usegit/artifacts/test.json')[0], 2)
        self.assertEqual(self.cli('status')[0], 2)

    def test_deploy_observed_connector_receipt_without_command(self):
        self.through('adapt')
        self.cli('set-mode', 'preview')
        self.cli('authorize', 'preview-deploy', '--target', 'preview.example', '--source', 'message 123')
        report = self.report('deploy')
        report['evidence'] = [{'id': 'D-001', 'kind': 'url', 'claim': 'Connector confirmed preview deployed',
                               'verification': 'observed', 'url': 'https://preview.example/build/123',
                               'environment': 'connected deployment tool', 'observed_at': u.now()}]
        report['executed_actions'] = [{'action': 'preview-deploy', 'target': 'preview.example'}]
        self.assertEqual(self.record('deploy', report)[0], 0)

    def test_multiple_checks_for_one_requirement(self):
        self.through('adapt')
        report = self.report('verify')
        report['checks'].append(copy.deepcopy(report['checks'][0]))
        report['checks'][1]['notes'] = 'Second acceptance scenario'
        self.assertEqual(self.record('verify', report)[0], 0)
        report['checks'][1]['result'] = 'fail'
        self.assertEqual(self.record('verify', report)[0], 2)

    def test_secret_url_query_rejected(self):
        for key in ('token', 'access_token', 'client_secret', 'password', 'X-Amz-Signature', 'api_key'):
            report = self.report('discover')
            report['evidence'] = [{'id': 'URL-1', 'kind': 'url', 'claim': 'Observed page', 'verification': 'observed',
                                   'url': 'https://example.org/?' + key + '=placeholder', 'environment': 'test', 'observed_at': u.now()}]
            self.assertEqual(self.record('discover', report)[0], 2)

    def test_control_directory_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '.usegit').symlink_to(self.w.directory, target_is_directory=True)
            with self.assertRaises(u.WorkflowError):
                u.Workflow(root).init()


if __name__ == '__main__':
    unittest.main()
