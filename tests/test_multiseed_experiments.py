import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'simulation'))
spec = importlib.util.spec_from_file_location('batch', ROOT / 'simulation/run_calibration_experiments.py')
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


def rows():
    return [dict(scenario=str(s), truth=str(s % 2),
                 rx1_filtered=str(i / 100 if s == 0 else 5),
                 rx2_filtered=str(2 * i / 100 if s == 0 else 10))
            for s in range(4) for i in range(100)]


class MultiseedTests(unittest.TestCase):
    def test_phase_seeds_are_disjoint_including_second_node(self):
        batch.assert_seed_separation(batch.CALIBRATION_SEEDS, batch.EVALUATION_SEEDS)
        with self.assertRaises(ValueError):
            batch.assert_seed_separation([101], [102])
        with self.assertRaises(ValueError):
            batch.assert_seed_separation([101, 102], [201])

    def test_pooling_fits_only_noise_and_uses_per_node_scale(self):
        fitted = batch.fit_thresholds([rows(), rows()])
        selected = fitted['0.025']
        self.assertEqual(selected['rx1']['noise_observations'], 200)
        self.assertEqual(selected['rx2']['threshold'], 2 * selected['rx1']['threshold'])
        self.assertLessEqual(selected['rx1']['calibration_pfa'], .025)
        self.assertLess(selected['rx1']['threshold'], 1)

    def test_comparison_does_not_refit_and_pooled_counts_equal_sum(self):
        fitted = batch.fit_thresholds([rows()])
        comparison = batch.evaluate_candidates(rows(), fitted)
        counts = batch.empty_counts()
        batch.add_counts(counts, comparison['0.025'])
        batch.add_counts(counts, comparison['0.025'])
        aggregate = batch.rates(counts)
        for name in aggregate:
            self.assertEqual(aggregate[name]['tp'], 2 * comparison['0.025'][name]['tp'])
            self.assertEqual(aggregate[name]['probability_detection'], comparison['0.025'][name]['probability_detection'])

    def test_batch_orchestration_writes_complete_report_with_mocked_runtime(self):
        # Synthetic orchestration fixture; not a GNU Radio simulation result.
        def fake_runtime(root, seed, cycles, thresholds, factor, metadata):
            directory = Path(root) / (str(seed) + '_' + str(factor))
            directory.mkdir(parents=True)
            (directory / 'config.json').write_text(json.dumps(metadata))
            (directory / 'observations.csv').write_text('synthetic fixture only')
            return directory, rows()
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(batch, 'run_flowgraph', side_effect=fake_runtime):
                root = batch.run_study(folder, 1)
            report = json.loads((root / 'study_summary.json').read_text())
            self.assertTrue(report['completed'])
            self.assertEqual(len(report['runs']), 9)
            self.assertEqual(report['calibration_noise_counts']['rx1'], 500)
            self.assertEqual(set(report['pooled_by_amplitude']), {'0.5', '1.0', '2.0'})
            self.assertEqual(json.loads((root / 'study_plan.json').read_text())['status'], 'completed')

    def test_failed_runtime_keeps_incomplete_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(batch, 'run_flowgraph', side_effect=RuntimeError('fixture failure')):
                with self.assertRaises(RuntimeError):
                    batch.run_study(folder, 1)
            plan = json.loads(next(Path(folder).glob('*/study_plan.json')).read_text())
            self.assertEqual(plan['status'], 'incomplete')
            self.assertFalse(list(Path(folder).glob('*/study_summary.json')))


if __name__ == '__main__':
    unittest.main()
