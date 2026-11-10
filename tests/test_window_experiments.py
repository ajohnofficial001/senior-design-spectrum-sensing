import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'simulation'))
spec = importlib.util.spec_from_file_location('windows', ROOT / 'simulation/run_window_experiments.py')
windows = importlib.util.module_from_spec(spec)
spec.loader.exec_module(windows)


class WindowTests(unittest.TestCase):
    def test_new_seeds_and_expected_observation_counts(self):
        windows.batch.assert_seed_separation(windows.CALIBRATION_SEEDS, windows.EVALUATION_SEEDS)
        self.assertFalse(set(windows.CALIBRATION_SEEDS + windows.EVALUATION_SEEDS) &
                         set(windows.batch.CALIBRATION_SEEDS + windows.batch.EVALUATION_SEEDS))
        for window, expected in [(1000, 9500), (2000, 4500), (4000, 2000)]:
            positions = range(window - 1, 20000, window)
            settled = sum(index >= 481 + window for index in positions)
            self.assertEqual(settled * 100 * 5, expected)

    def test_three_windows_are_separately_run_and_reported(self):
        # Synthetic fixture validates orchestration only, not GNU Radio results.
        calls = []
        def fake_run(root, cycles, window_samples, calibration_seeds, evaluation_seeds):
            calls.append(window_samples)
            root = Path(root) / 'fixture'
            root.mkdir(parents=True)
            metrics = dict(tp=1, fp=0, tn=1, fn=0, probability_detection=1,
                           probability_false_alarm=0)
            report = dict(completed=True, averaging_window_samples=window_samples,
                          selected_thresholds=[.1, .2], calibration_noise_counts={'rx1': 100, 'rx2': 100},
                          pooled_by_amplitude={'0.5': {'0.025': {'OR': metrics}}}, runs=[])
            windows.batch.write_json(root / 'study_summary.json', report)
            return root
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(windows.batch, 'run_study', side_effect=fake_run):
                root = windows.run(folder, 2)
            report = json.loads((root / 'window_summary.json').read_text())
            self.assertEqual(calls, [1000, 2000, 4000])
            self.assertTrue(report['completed'])
            self.assertEqual([r['averaging_span_ms'] for r in report['results']], [.5, 1, 2])
            self.assertTrue((root / 'window_comparison.csv').exists())

    def test_failure_preserves_incomplete_status(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(windows.batch, 'run_study', side_effect=RuntimeError('fixture')):
                with self.assertRaises(RuntimeError):
                    windows.run(folder, 2)
            plan = json.loads(next(Path(folder).glob('*/window_plan.json')).read_text())
            self.assertEqual(plan['status'], 'incomplete')
            self.assertFalse(list(Path(folder).glob('*/window_summary.json')))


if __name__ == '__main__':
    unittest.main()
