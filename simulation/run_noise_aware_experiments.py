#!/usr/bin/env python3
"""Native GNU Radio source plus spectral CFAR-style detector evaluation."""
import argparse
import csv
import json
from pathlib import Path
import uuid
import numpy as np
import run_calibration_experiments as batch
from calibrate_thresholds import upper_threshold
from noise_aware_detector import FeatureFrames, decide, METHODS
from run_frozen_confirmation import SETTINGS, validate_settings
from run_stress_experiments import empty, rates

TRAIN = (60001, 61001, 62001, 63001, 64001)
TEST = (70001, 71001, 72001)
CASES = {'control': {}, 'noise_high': {'noise_factor': 1.2},
         'noise_step': {'noise_step': True}, 'fading': {'fading': True},
         'reference_interference': {'reference_tone_amplitude': .002}}


def acquire(root, seed, cycles, factor, channel):
    from gnuradio import gr, blocks, filter
    from gnuradio.filter import firdes
    from full_simulation_blocks.stress_source import blk as Source
    from full_simulation_blocks.fusion_logger import blk as Logger
    settings = json.loads(SETTINGS.read_text())
    validate_settings(settings)

    class Collector(gr.sync_block):
        def __init__(self):
            gr.sync_block.__init__(self, name='Reference-band spectral measurements',
                                   in_sig=[np.complex64, np.complex64, np.float32], out_sig=None)
            self.frames = FeatureFrames()
        @property
        def position(self):
            return self.frames.position
        @property
        def records(self):
            return self.frames.records
        def work(self, inputs, outputs):
            return self.frames.push(inputs)

    fs, segment, window = 2000000, 20000, 4000
    taps = firdes.low_pass(1., fs, 20000, 10000)
    config = dict(expected_samples=4 * segment * cycles, seed=seed, cycles=cycles,
                  signal_amplitude=.0002 * factor, channel_stress=channel,
                  filter_taps=list(taps), method='spectral reference-band comparison',
                  spectral_window='Hann', reference_spread_limit=4,
                  python_version=__import__('sys').version, gnuradio_version=gr.version(),
                  frozen_settings_sha256=batch.sha256(SETTINGS))
    tb = gr.top_block('Noise-aware versus frozen energy detection')
    source = Source(cycles=cycles, signal_amplitude=.0002 * factor, seed=seed, **channel)
    logger = Logger(window_samples=window, guard_samples=len(taps) + window,
                    threshold1=settings['thresholds'][0], threshold2=settings['thresholds'][1],
                    output_root=str(root), config=config)
    collector = Collector()
    processing = []
    for node in range(2):
        fir = filter.freq_xlating_fir_filter_ccc(1, taps, 400000, fs)
        tb.connect((source, node), fir)
        tb.connect((source, node), (collector, node))
        processing.append(fir)
        for branch in range(2):
            mag = blocks.complex_to_mag_squared(1)
            avg = blocks.moving_average_ff(window, 1. / window, 4000, 1)
            scale = blocks.multiply_const_ff(1000000)
            tb.connect((fir, 0) if branch == 0 else (source, node), mag, avg, scale,
                       (logger, node + 2 * branch))
            processing.extend((mag, avg, scale))
    tb.connect((source, 2), (logger, 4))
    tb.connect((source, 2), (collector, 2))
    tb.start()
    try:
        tb.wait()
    except KeyboardInterrupt:
        tb.stop()
        tb.wait()
        raise
    summary = json.loads((logger.directory / 'summary.json').read_text())
    if not summary['completed'] or collector.position != config['expected_samples']:
        raise RuntimeError('Incomplete acquisition')
    batch.write_json(logger.directory / 'spectral_features.json', collector.records)
    return logger.directory, collector.records, summary


def fit(runs):
    result = {}
    for method in METHODS:
        result[method] = []
        for node in range(2):
            values = [r['nodes'][node]['scores'][method] for rows in runs for r in rows
                      if r['scenario'] == 0 and r['truth'] == 0 and r['nodes'][node]['reliable'][method]]
            threshold = upper_threshold(values, .025)
            result[method].append(dict(threshold=threshold, noise_count=len(values),
                                       fit_pfa=sum(v > threshold for v in values) / len(values)))
    return result


def score(rows, calibration):
    result = {}
    for method in METHODS:
        counts, listening, invalid_nodes = empty(), 0, 0
        for row in rows:
            local = [decide(row['nodes'][node], method, calibration[method][node]['threshold'])
                     for node in range(2)]
            listening += max(length for _, length in local)
            invalid_nodes += sum(vote is None for vote, _ in local)
            # Reliability policy: require both references valid; otherwise abstain.
            truth = row['truth']
            if any(vote is None for vote, _ in local):
                counts['no_decision_positive' if truth else 'no_decision_negative'] += 1
            else:
                decision = any(vote for vote, _ in local)
                counts[('tp' if truth else 'fp') if decision else ('fn' if truth else 'tn')] += 1
        result[method] = dict(rates(counts), mean_nominal_listening_samples=listening / len(rows),
                              invalid_node_reference_count=invalid_nodes)
    return result


def run(output_root, cycles=100):
    batch.assert_seed_separation(TRAIN, TEST)
    batch.assert_seed_separation((101, 1001, 2001, 3001, 4001, 5001, 6001,
        10001, 11001, 12001, 20001, 21001, 22001, 23001, 24001, 30001, 31001,
        32001, 40001, 41001, 42001, 43001, 44001, 50001, 51001, 52001), TRAIN + TEST)
    root = Path(output_root) / ('noise_aware_' + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    plan = dict(status='running', cycles=cycles, calibration_seeds=TRAIN, evaluation_seeds=TEST,
        cases=CASES, node_target=.025, methods=METHODS, smoke_test=cycles != 100,
        detector_truth_policy='Ground truth used for training-noise selection and scoring only')
    batch.write_json(root / 'noise_aware_plan.json', plan)
    print('NOISE-AWARE STUDY:', root.resolve(), flush=True)
    try:
        training, provenance = [], []
        for seed in TRAIN:
            print('Calibration seed', seed, flush=True)
            directory, rows, _ = acquire(root / 'calibration', seed, cycles, 1., {})
            training.append(rows)
            provenance.append(dict(seed=seed, features_sha256=batch.sha256(directory / 'spectral_features.json')))
        calibration = fit(training)
        batch.write_json(root / 'noise_aware_calibration.json', dict(methods=calibration, runs=provenance))
        calibration_hash = batch.sha256(root / 'noise_aware_calibration.json')
        runs = []
        for case, channel in CASES.items():
            for factor in (.5, 1., 2.):
                for seed in TEST:
                    print(case, factor, seed, flush=True)
                    directory, rows, baseline = acquire(root / 'evaluation', seed, cycles, factor, channel)
                    runs.append(dict(case=case, amplitude_factor=factor, seed=seed,
                        directory=str(directory.relative_to(root)), spectral_observations=len(rows),
                        spectral_features_sha256=batch.sha256(directory / 'spectral_features.json'),
                        methods=score(rows, calibration), frozen_baseline=baseline['metrics']['OR'],
                        frozen_observations=baseline['observations']))
                    batch.write_json(root / 'noise_aware_progress.json', runs)
        report = dict(completed=True, smoke_test=cycles != 100, cycles=cycles,
            calibration=calibration, calibration_sha256=calibration_hash, runs=runs,
            limitations=['Reference bands assumed representative of target-band broadband noise',
                         'Reference disagreement may detect narrowband contamination, not all colored noise',
                         'All references corrupted similarly can defeat the reliability check',
                         'Spectral target integration and Hann window differ from frozen FIR detector',
                         'Different evaluation positions/counts: native frozen FIR versus 8000-sample FFT frames',
                         'Two-look max score is calibrated jointly, not two independent tests',
                         'Two-look listening lengths are nominal sample costs, not measured latency',
                         'No report loss in this study; invalid references cause abstention',
                         'Native mock ledger records frozen detector only; no adaptive blockchain claim',
                         'Software only; no confidence intervals or guaranteed accuracy'])
        batch.write_json(root / 'noise_aware_summary.json', report)
        with (root / 'noise_aware_comparison.csv').open('w', newline='', encoding='utf-8') as stream:
            fields = ['case', 'amplitude_factor', 'seed', 'method', *next(iter(runs[0]['methods'].values())).keys()]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for r in runs:
                for method, m in r['methods'].items():
                    writer.writerow(dict(case=r['case'], amplitude_factor=r['amplitude_factor'], seed=r['seed'], method=method, **m))
        plan['status'] = 'completed'
        batch.write_json(root / 'noise_aware_plan.json', plan)
        print('COMPLETED: upload noise_aware_summary.json and noise_aware_comparison.csv from', root, flush=True)
    except BaseException as exc:
        plan.update(status='incomplete', error=type(exc).__name__ + ': ' + str(exc))
        batch.write_json(root / 'noise_aware_plan.json', plan)
        raise
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', default='simulation/generated')
    parser.add_argument('--cycles', type=int, default=100)
    args = parser.parse_args()
    if args.cycles < 10:
        parser.error('Use at least 10 cycles for sufficient training noise; default 100')
    run(args.output_root, args.cycles)
