"""Pure-Python behavioral checks; these do not validate GNU Radio scheduling."""
import hashlib
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


def load_block(filename):
    class SyncBlock:
        def __init__(self, *args, **kwargs):
            pass
    # Isolate the behavior under test from an unavailable GNU Radio runtime.
    fake = types.ModuleType('gnuradio')
    fake.gr = types.SimpleNamespace(sync_block=SyncBlock)
    spec = importlib.util.spec_from_file_location(filename, ROOT / 'simulation' /
                                               'full_simulation_blocks' / (filename + '.py'))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'gnuradio': fake}):
        spec.loader.exec_module(module)
    return module.blk


Source = load_block('scenario_source')
Logger = load_block('fusion_logger')


class FullSimulationTests(unittest.TestCase):
    def source_run(self, chunk):
        source = Source(segment_samples=20, cycles=2)
        collected = [[], [], []]
        while True:
            outputs = [np.empty(chunk, dtype=t) for t in (np.complex64, np.complex64, np.float32)]
            n = source.work([], outputs)
            if n == -1:
                break
            for out, dest in zip(outputs, collected):
                dest.extend(out[:n])
        return [np.asarray(x) for x in collected]

    def test_source_seed_and_truth_independent_of_scheduler_chunks(self):
        a, b = self.source_run(7), self.source_run(128)
        for x, y in zip(a, b):
            np.testing.assert_array_equal(x, y)
        np.testing.assert_array_equal(a[2], np.tile(np.repeat([0, 1, 0, 1], 20), 2))
        self.assertFalse(np.array_equal(a[0], a[1]))

    def test_source_offband_only_is_not_wanted_occupancy(self):
        source = Source(sample_rate=2000000, segment_samples=20, cycles=1,
                        noise1=0, noise2=0, signal_amplitude=0,
                        interference_amplitude=1)
        outputs = [np.empty(80, dtype=t) for t in (np.complex64, np.complex64, np.float32)]
        self.assertEqual(source.work([], outputs), 80)
        np.testing.assert_allclose(np.abs(outputs[0][:40]), 0)
        np.testing.assert_allclose(np.abs(outputs[0][40:]), 1, atol=1e-7)
        np.testing.assert_array_equal(outputs[2][40:60], 0)

    def logger_run(self, folder, chunk):
        logger = Logger(sample_rate=100, segment_samples=12, window_samples=2,
                        guard_samples=4, threshold1=0.5, threshold2=0.5,
                        output_root=folder, config={'expected_samples': 48})
        truth = np.tile(np.repeat([0, 1, 0, 1], 12), 1).astype(np.float32)
        # RX1 perfect, RX2 always absent; both rules have predictable counts.
        streams = [truth, np.zeros(48, dtype=np.float32), truth, truth, truth]
        logger.start()
        for i in range(0, 48, chunk):
            logger.work([s[i:i+chunk] for s in streams], [])
        logger.stop()
        summary = json.loads((logger.directory / 'summary.json').read_text())
        return logger, summary

    def test_fusion_metrics_transient_guard_and_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            logger, summary = self.logger_run(folder, 7)
            self.assertTrue(summary['completed'])
            self.assertEqual(summary['observations'], 16)
            self.assertEqual(summary['metrics']['OR']['probability_detection'], 1)
            self.assertEqual(summary['metrics']['OR']['probability_false_alarm'], 0)
            self.assertEqual(summary['metrics']['AND']['probability_detection'], 0)
            previous = '0' * 64
            records = [json.loads(s) for s in (logger.directory / 'mock_ledger.jsonl').read_text().splitlines()]
            for i, record in enumerate(records):
                digest = record.pop('hash')
                self.assertEqual(record['sequence'], i)
                self.assertEqual(record['previous_hash'], previous)
                self.assertGreaterEqual(record['sample_index'] % 12, 4)
                self.assertEqual(digest, hashlib.sha256(json.dumps(record, sort_keys=True,
                                                                 separators=(',', ':')).encode()).hexdigest())
                previous = digest
            self.assertEqual(previous, summary['final_mock_hash'])

    def test_logger_chunk_invariance_and_incomplete_run(self):
        with tempfile.TemporaryDirectory() as folder:
            _, a = self.logger_run(folder, 5)
            _, b = self.logger_run(folder, 48)
            self.assertEqual(a, b)
            logger = Logger(output_root=folder, config={'expected_samples': 10})
            logger.start()
            logger.work([np.zeros(5, dtype=np.float32)] * 5, [])
            logger.stop()
            summary = json.loads((logger.directory / 'summary.json').read_text())
            self.assertFalse(summary['completed'])
            self.assertIsNone(summary['metrics']['rx1']['probability_detection'])

    def test_invalid_configurations(self):
        with self.assertRaises(ValueError):
            Logger(fusion_rule='MAJORITY')
        with self.assertRaises(ValueError):
            Logger(guard_samples=20000)
        with self.assertRaises(ValueError):
            Source(tone_offset=1000000)


if __name__ == '__main__':
    unittest.main()
