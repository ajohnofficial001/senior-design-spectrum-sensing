import copy
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'simulation'))
from reference_fallback import fallback_features, decide
from noise_aware_detector import observe
from run_reference_confirmation import frozen_settings, fit_fallback, compare


class ReferenceFallbackTests(unittest.TestCase):
    def test_recovers_two_clean_sectors_and_is_scale_invariant(self):
        a = fallback_features(dict(reference_sectors=[1., 1.1, 100., 120.], target_power=2.))
        b = fallback_features(dict(reference_sectors=[10., 11., 1000., 1200.], target_power=20.))
        self.assertTrue(a['reliable'])
        self.assertEqual(a['sectors_used'], 2)
        self.assertAlmostEqual(a['score'], b['score'])

    def test_unusable_reference_causes_abstention(self):
        for refs in ([0., 0., 0., 0.], [1., 8., 64., 512.], [float('nan'), 1., 1., 1.]):
            f = fallback_features(dict(reference_sectors=refs, target_power=1.))
            self.assertFalse(f['reliable'])
            self.assertIsNone(decide(f, 1.5))

    def test_narrowband_contamination_has_matched_comparison(self):
        rng = np.random.default_rng(40)
        x = rng.standard_normal(8000) + 1j * rng.standard_normal(8000)
        x += 30 * np.exp(2j * np.pi * 490000 * np.arange(8000) / 2000000)
        feature = observe(x)
        self.assertFalse(feature['long']['reliable'])
        fallback = fallback_features(feature['long'])
        self.assertTrue(fallback['reliable'])
        self.assertEqual(fallback['sectors_used'], 2)
        result = compare([dict(truth=0, nodes=[feature, feature])],
                         frozen_settings()['thresholds'], [{'threshold': 100.}] * 2)
        self.assertEqual(result['frozen_reference_8000']['decision_coverage'], 0.)
        self.assertEqual(result['fallback_reference_8000']['decision_coverage'], 1.)

    def test_noise_fitting_excludes_signal_and_original_thresholds_stay_fixed(self):
        rng = np.random.default_rng(50)
        rows = []
        for _ in range(100):
            x = rng.standard_normal(8000) + 1j * rng.standard_normal(8000)
            rows.append(dict(scenario=0, truth=0, nodes=[observe(x)] * 2))
        thresholds = copy.deepcopy(frozen_settings()['thresholds'])
        fitted = fit_fallback([rows])
        signal = copy.deepcopy(rows[0])
        signal.update(scenario=1, truth=1)
        signal['nodes'][0]['long']['target_power'] = 1e9
        self.assertEqual(fit_fallback([rows + [signal]]), fitted)
        self.assertEqual(frozen_settings()['thresholds'], thresholds)


if __name__ == '__main__':
    unittest.main()
