import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'simulation'))
spec = importlib.util.spec_from_file_location('confirmation', ROOT / 'simulation/run_frozen_confirmation.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConfirmationTests(unittest.TestCase):
    def test_settings_frozen_and_seeds_untouched(self):
        settings = json.loads(module.SETTINGS.read_text())
        module.validate_settings(settings)
        changed = copy.deepcopy(settings)
        changed['thresholds'][0] += .001
        with self.assertRaises(ValueError):
            module.validate_settings(changed)

    def test_fifteen_run_orchestration_without_refitting(self):
        calls = []
        def fake(root, seed, cycles, thresholds, factor, metadata):
            calls.append((seed, tuple(thresholds), factor))
            directory = Path(root) / (str(seed) + '_' + str(factor))
            directory.mkdir(parents=True)
            (directory / 'config.json').write_text('{}')
            (directory / 'observations.csv').write_text('synthetic fixture only')
            return directory, [dict(scenario=str(s), truth=str(s % 2),
                                    rx1_filtered=str(s % 2), rx2_filtered=str(s % 2)) for s in range(4)]
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(module.batch, 'run_flowgraph', side_effect=fake):
                with patch.object(module.batch, 'fit_thresholds', side_effect=AssertionError('No fitting allowed')):
                    root = module.run(folder, 100)
            report = json.loads((root / 'confirmation_summary.json').read_text())
            self.assertEqual(len(calls), 15)
            self.assertEqual(len({thresholds for _, thresholds, _ in calls}), 1)
            self.assertTrue(report['completed'])
            self.assertFalse(report['smoke_test'])
            self.assertEqual(report['pooled_by_amplitude']['0.5']['OR']['tp'], 10)

    def test_failure_leaves_incomplete_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(module.batch, 'run_flowgraph', side_effect=RuntimeError('fixture')):
                with self.assertRaises(RuntimeError):
                    module.run(folder, 1)
            plan = json.loads(next(Path(folder).glob('*/confirmation_plan.json')).read_text())
            self.assertEqual(plan['status'], 'incomplete')
            self.assertTrue(plan['smoke_test'])
            self.assertFalse(list(Path(folder).glob('*/confirmation_summary.json')))


if __name__ == '__main__':
    unittest.main()
