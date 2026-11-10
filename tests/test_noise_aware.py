import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'simulation'))
from noise_aware_detector import FeatureFrames, observe, spectral_features, decide, METHODS
from run_noise_aware_experiments import fit, score


class NoiseAwareTests(unittest.TestCase):
    def test_streaming_frames_preserve_boundaries_and_chunk_invariance(self):
        rng = np.random.default_rng(10)
        signal = (rng.standard_normal(40000) + 1j * rng.standard_normal(40000)).astype(np.complex64)
        truth = np.repeat([0., 1.], 20000)
        results = []
        for chunk in (137, 40000):
            frames = FeatureFrames()
            for start in range(0, 40000, chunk):
                frames.push([signal[start:start+chunk], signal[start:start+chunk], truth[start:start+chunk]])
            self.assertEqual(frames.position, 40000)
            self.assertEqual([r['sample_index'] for r in frames.records], [7999, 15999, 27999, 35999])
            self.assertEqual([r['truth'] for r in frames.records], [0, 0, 1, 1])
            results.append(frames.records)
        self.assertEqual(*results)

    def noise(self, seed=1):
        rng = np.random.default_rng(seed)
        return rng.standard_normal(8000) + 1j * rng.standard_normal(8000)

    def test_noise_scale_invariance(self):
        a, b = observe(self.noise()), observe(20 * self.noise())
        for method in METHODS:
            self.assertAlmostEqual(a['scores'][method], b['scores'][method], places=12)
        self.assertAlmostEqual(b['long']['noise_reference'] / a['long']['noise_reference'], 400)

    def test_reference_contamination_is_flagged(self):
        n = np.arange(8000)
        contaminated = self.noise() + 30 * np.exp(2j * np.pi * 490000 * n / 2000000)
        f = observe(contaminated)
        self.assertFalse(f['long']['reliable'])
        self.assertIsNone(decide(f, 'reference_8000', 2)[0])

    def test_strong_target_and_two_look_early_exit(self):
        n = np.arange(8000)
        f = observe(self.noise() + 5 * np.exp(2j * np.pi * 400000 * n / 2000000))
        self.assertEqual(decide(f, 'two_look', 2), (1, 4000))
        self.assertEqual(decide(observe(np.zeros(8000)), 'two_look', 2), (None, 8000))

    def test_noise_fit_does_not_use_signal_examples(self):
        rows = [dict(scenario=0, truth=0, nodes=[observe(self.noise(i)), observe(self.noise(i+1000))])
                for i in range(100)]
        fitted = fit([rows])
        poisoned = rows + [dict(scenario=1, truth=1, nodes=[observe(self.noise()*100)]*2)]
        self.assertEqual(fit([poisoned]), fitted)
        for method in METHODS:
            self.assertEqual(fitted[method][0]['noise_count'], 100)
        result = score(rows, fitted)
        for method in METHODS:
            # Fusion OR has two opportunities to false-alarm: node budgets sum.
            self.assertLessEqual(result[method]['false_alarm_given_decision'], .05)

    def test_inputs_and_window_lengths(self):
        with self.assertRaises(ValueError):
            spectral_features(np.ones(10))
        with self.assertRaises(ValueError):
            observe(np.ones(4000))
        with self.assertRaises(ValueError):
            decide(observe(self.noise()), 'unknown', 1)


if __name__ == '__main__':
    unittest.main()
