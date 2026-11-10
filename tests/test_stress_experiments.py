import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'simulation'))
import run_stress_experiments as stress


def source_class():
    class Sync:
        def __init__(self, *a, **kw):
            pass
    fake = types.ModuleType('gnuradio')
    fake.gr = types.SimpleNamespace(sync_block=Sync)
    with patch.dict(sys.modules, {'gnuradio': fake}):
        from full_simulation_blocks.stress_source import blk
    return blk


class StressTests(unittest.TestCase):
    def rows(self):
        return [dict(sample_index=i, scenario=str(i), truth=str(i % 2),
                     rx1_filtered=str(i % 2), rx2_filtered=str(i % 2)) for i in range(4)]

    def test_both_outage_is_not_correct_rejection(self):
        counts, records = stress.tally_reports(self.rows(), [.1, .2], [1, 1], 50001)
        for c in counts.values():
            result = stress.rates(c)
            self.assertEqual(result['decision_coverage'], 0)
            self.assertIsNone(result['false_alarm_given_decision'])
            self.assertIsNone(result['detection_given_decision'])
            self.assertEqual(result['detected_fraction_all_occupied'], 0)
            self.assertEqual(c['tn'], 0)
        self.assertTrue(all(r['available_OR'] is None for r in records))

    def test_one_receiver_policy_and_deterministic_masks(self):
        counts, records = stress.tally_reports(self.rows(), [.1, .2], [1, 0], 50001)
        self.assertEqual(stress.rates(counts['available_OR'])['decision_coverage'], 1)
        self.assertEqual(stress.rates(counts['require_both_OR'])['decision_coverage'], 0)
        a = stress.tally_reports(self.rows(), [.1, .2], [.2, .2], 50001)
        b = stress.tally_reports(self.rows(), [.1, .2], [.2, .2], 50001)
        self.assertEqual(a, b)

    def test_stress_source_chunk_invariance_and_noise_step(self):
        Source = source_class()
        def generate(chunk, **kwargs):
            source = Source(segment_samples=20, cycles=2, seed=50001, **kwargs)
            result = [[], [], []]
            while True:
                out = [np.empty(chunk, dtype=t) for t in (np.complex64, np.complex64, np.float32)]
                n = source.work([], out)
                if n == -1:
                    break
                for dest, values in zip(result, out):
                    dest.extend(values[:n])
            return [np.asarray(v) for v in result]
        for a, b in zip(generate(7, fading=True, noise_step=True), generate(200, fading=True, noise_step=True)):
            np.testing.assert_array_equal(a, b)
        # Wanted amplitude zero; inspect noise-only scenario in two cycles.
        baseline = generate(200, signal_amplitude=0)
        stepped = generate(200, signal_amplitude=0, noise_step=True)
        for node in (0, 1):
            np.testing.assert_allclose(stepped[node][:20], .8 * baseline[node][:20], rtol=2e-7)
            np.testing.assert_allclose(stepped[node][80:100], 1.2 * baseline[node][80:100], rtol=2e-7)

    def test_orchestration_reuses_channels_and_retains_abstentions(self):
        calls = []
        def fake(root, seed, cycles, thresholds, factor, metadata):
            calls.append(metadata)
            directory = Path(root) / str(len(calls))
            directory.mkdir(parents=True)
            (directory / 'config.json').write_text('{}')
            (directory / 'observations.csv').write_text('synthetic fixture only')
            return directory, self.rows()
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(stress.batch, 'run_flowgraph', side_effect=fake):
                root = stress.run(folder, 2)
            report = json.loads((root / 'stress_summary.json').read_text())
            self.assertEqual(len(calls), 45)
            self.assertEqual(len(report['runs']), 72)
            self.assertTrue(report['smoke_test'])
            self.assertEqual(report['pooled']['both_outage']['1.0']['available_OR']['decision_coverage'], 0)


if __name__ == '__main__':
    unittest.main()
