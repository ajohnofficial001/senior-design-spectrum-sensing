import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('calibration', ROOT / 'simulation/calibrate_thresholds.py')
cal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cal)


class ThresholdCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.saved = json.loads((ROOT / 'experiments/threshold_calibration/thresholds.json').read_text())
        self.config = self.saved['calibration_config']
        self.rows = cal.load_rows(ROOT / 'experiments/threshold_calibration/noise_only.csv')

    def test_saved_thresholds_reproduce_from_noise_subset(self):
        result = cal.calibrate(self.rows, self.config)
        self.assertEqual(result['nodes'], self.saved['nodes'])
        self.assertEqual(result['noise_observations_per_node'], 190)
        self.assertTrue(all(n['calibration_pfa'] <= .05 for n in result['nodes'].values()))

    def test_signal_and_interference_do_not_leak_into_calibration(self):
        extra = [dict(scenario=str(s), truth=str(s % 2), rx1_filtered='100', rx2_filtered='100')
                 for s in (1, 2, 3)]
        self.assertEqual(cal.calibrate(self.rows + extra, self.config)['nodes'], self.saved['nodes'])

    def test_independent_seed_and_configuration_enforced(self):
        with self.assertRaisesRegex(ValueError, 'different node seeds'):
            cal.evaluate(self.rows, self.config, self.saved)
        changed = dict(self.config, seed=1001, noise2=.1)
        with self.assertRaisesRegex(ValueError, 'noise2'):
            cal.evaluate(self.rows, changed, self.saved)

    def test_target_validation(self):
        for target in (0, 1, -.5):
            with self.assertRaises(ValueError):
                cal.upper_threshold([0] * 100, target)
        with self.assertRaises(ValueError):
            cal.upper_threshold([0], .05)


if __name__ == '__main__':
    unittest.main()
