import unittest
from ci_changes import classify


class ChangeSelectionTests(unittest.TestCase):
    def test_unknown_diff_runs_everything(self):
        for paths in [None, []]:
            self.assertTrue(all(classify(paths, 'pull_request', 'website').values()))

    def test_docs_skip_code_but_keep_documentation(self):
        result = classify(['README.md', 'docs/guide.md'], 'pull_request', 'toolkit')
        self.assertFalse(result['code'])
        self.assertTrue(result['docs'])

    def test_source_markdown_and_dependency_text_are_code(self):
        for path in ['src/index.md', 'requirements.txt', '.github/workflows/ci.yml',
                     'tests/test_app.py', 'scripts/check.py', 'package-lock.json']:
            self.assertTrue(classify([path], 'pull_request', 'website')['code'], path)

    def test_push_always_runs_full_validation(self):
        self.assertTrue(all(classify(['README.md'], 'push', 'toolkit').values()))

    def test_schedule_keeps_security_and_skips_application(self):
        result = classify(None, 'schedule', 'incorporation')
        self.assertTrue(result['code'])
        self.assertFalse(result['app'])

    def test_bookkeeping_files_do_not_trigger_application_tests(self):
        self.assertFalse(classify(['tenue-de-livre/transactions.xlsx'], 'pull_request', 'incorporation')['app'])
        self.assertTrue(classify(['tenue-de-livre/generateur-de-facture/template.xlsx'], 'pull_request', 'incorporation')['app'])

    def test_unknown_configuration_fails_open(self):
        self.assertTrue(classify(['config/settings.yaml'], 'pull_request', 'incorporation')['app'])


if __name__ == '__main__':
    unittest.main()
