#!/usr/bin/env python3
"""Batch GNU Radio calibration/evaluation; no SDRs or GUI needed.

Run from a Radioconda environment: python simulation/run_calibration_experiments.py
Math/report functions can be tested without GNU Radio; actual experiments require it.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import uuid

from calibrate_thresholds import load_rows, metrics, upper_threshold

CALIBRATION_SEEDS = (2001, 3001, 4001, 5001, 6001)
EVALUATION_SEEDS = (10001, 11001, 12001)
NODE_TARGETS = (0.01, 0.025, 0.05, 0.10)
SELECTED_NODE_TARGET = 0.025
AMPLITUDE_FACTORS = (0.5, 1.0, 2.0)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assert_seed_separation(training, testing):
    training_nodes = {s + n for s in training for n in (0, 1)}
    testing_nodes = {s + n for s in testing for n in (0, 1)}
    if training_nodes & testing_nodes:
        raise ValueError('Calibration and evaluation node seeds overlap')
    if len(training_nodes) != 2 * len(training) or len(testing_nodes) != 2 * len(testing):
        raise ValueError('Node seeds overlap within a study phase')


def fit_thresholds(calibration_runs, node_targets=NODE_TARGETS):
    """Fit only scenario-0/truth-0; all signal-present observations are ignored."""
    powers = {node: [] for node in ('rx1', 'rx2')}
    for rows in calibration_runs:
        for row in rows:
            if int(row['scenario']) == 0 and int(row['truth']) == 0:
                for node in powers:
                    powers[node].append(float(row[node + '_filtered']))
    fitted = {}
    for target in node_targets:
        fitted[str(target)] = {}
        for node, values in powers.items():
            threshold = upper_threshold(values, target)
            fitted[str(target)][node] = dict(threshold=threshold, noise_observations=len(values),
                calibration_pfa=sum(v > threshold for v in values) / len(values))
    return fitted


def add_counts(accumulator, result):
    for node in accumulator:
        for key in ('tp', 'fp', 'tn', 'fn'):
            accumulator[node][key] += result[node][key]


def empty_counts():
    return {node: dict(tp=0, fp=0, tn=0, fn=0) for node in ('rx1', 'rx2', 'OR', 'AND')}


def rates(counts):
    output = {}
    for node, count in counts.items():
        positives, negatives = count['tp'] + count['fn'], count['fp'] + count['tn']
        output[node] = dict(count,
                            probability_detection=count['tp'] / positives if positives else None,
                            probability_false_alarm=count['fp'] / negatives if negatives else None)
    return output


def evaluate_candidates(rows, candidates):
    # All candidates see identical held-out power samples, with no refitting.
    return {label: metrics(rows, [nodes[n]['threshold'] for n in ('rx1', 'rx2')])
            for label, nodes in candidates.items()}


def run_flowgraph(output_root, seed, cycles, thresholds, amplitude_factor, metadata):
    # Keep imports lazy: importing this file for unit tests must not require GNU Radio.
    from gnuradio import gr, blocks, filter
    from gnuradio.filter import firdes
    from full_simulation_blocks.scenario_source import blk as ScenarioSource
    from full_simulation_blocks.fusion_logger import blk as FusionLogger

    fs, segment, power_scale = 2000000, 20000, 1000000
    window = int(metadata.get("averaging_window_samples", 1000))
    if window not in (1000, 2000, 4000):
        raise ValueError("Supported study windows: 1000, 2000, 4000")
    taps = firdes.low_pass(1.0, fs, 20000, 10000)
    amplitude = 0.0002 * amplitude_factor
    config = dict(expected_samples=4 * segment * cycles, cycles=cycles,
                  tone_offset=400000, signal_amplitude=amplitude,
                  interference_offset=600000, interference_amplitude=0.002,
                  node2_gain=0.65, noise1=0.001, noise2=0.0012, seed=seed,
                  power_scale=power_scale, filter_taps=list(taps),
                  noise_definition='independent I/Q standard deviation',
                  scenario_order=['noise_only', 'wanted', 'interferer_only', 'wanted_and_interferer'],
                  python_version=sys.version, gnuradio_version=gr.version(), **metadata)
    tb = gr.top_block('Multiseed software-only calibration experiment')
    source = ScenarioSource(sample_rate=fs, segment_samples=segment, cycles=cycles,
                            signal_amplitude=amplitude, seed=seed)
    logger = FusionLogger(sample_rate=fs, segment_samples=segment, window_samples=window,
                          guard_samples=len(taps) + window, threshold1=thresholds[0],
                          threshold2=thresholds[1], output_root=str(output_root), config=config)
    processing = []
    for node in range(2):
        band_filter = filter.freq_xlating_fir_filter_ccc(1, taps, 400000, fs)
        tb.connect((source, node), band_filter)
        processing.append(band_filter)
        for branch in range(2):
            mag = blocks.complex_to_mag_squared(1)
            average = blocks.moving_average_ff(window, 1.0 / window, 4000, 1)
            scale = blocks.multiply_const_ff(power_scale)
            origin = (band_filter, 0) if branch == 0 else (source, node)
            tb.connect(origin, mag, average, scale, (logger, node + 2 * branch))
            processing.extend((mag, average, scale))
    tb.connect((source, 2), (logger, 4))
    tb.start()
    try:
        tb.wait()
    except KeyboardInterrupt:
        tb.stop()
        tb.wait()
        raise
    if logger.directory is None:
        raise RuntimeError('Logger did not start')
    summary = json.loads((logger.directory / 'summary.json').read_text())
    if not summary.get('completed') or summary['samples_consumed'] != config['expected_samples']:
        raise RuntimeError('Incomplete run: ' + str(logger.directory))
    rows = load_rows(logger.directory / 'observations.csv')
    if len(rows) != summary['observations']:
        raise RuntimeError('Observation count differs from run summary')
    return logger.directory, rows


def run_study(output_root, cycles, window_samples=1000,
              calibration_seeds=CALIBRATION_SEEDS, evaluation_seeds=EVALUATION_SEEDS):
    assert_seed_separation(calibration_seeds, evaluation_seeds)
    study_id = 'multiseed_' + uuid.uuid4().hex
    root = Path(output_root) / study_id
    root.mkdir(parents=True, exist_ok=False)
    plan = dict(study_id=study_id, cycles_per_run=cycles, averaging_window_samples=window_samples,
                calibration_source_seeds=calibration_seeds,
                evaluation_source_seeds=evaluation_seeds,
                node_targets=NODE_TARGETS, selected_node_target=SELECTED_NODE_TARGET,
                amplitude_factors=AMPLITUDE_FACTORS,
                baseline_signal_amplitude=0.0002,
                target_or_pfa=0.05,
                target_rationale='2.5% per node gives an approximate 5% OR budget by union bound; empirical calibration is not a guarantee',
                evaluation_policy='All candidates are predeclared; no automatic winner is chosen from test data',
                source_commit='Record the Git commit used when archiving this study',
                status='running')
    write_json(root / 'study_plan.json', plan)
    print('STUDY DIRECTORY:', root.resolve(), flush=True)
    calibration_runs, calibration_provenance = [], []
    try:
        for index, seed in enumerate(calibration_seeds, 1):
            print(f'Calibration {index}/5: seed={seed}', flush=True)
            directory, rows = run_flowgraph(root / 'calibration', seed, cycles, (.05, .05), 1.0,
                                            dict(study_id=study_id, phase='calibration', averaging_window_samples=window_samples))
            calibration_runs.append(rows)
            calibration_provenance.append(dict(seed=seed, directory=str(directory.relative_to(root)),
                                                config_sha256=sha256(directory / 'config.json'),
                                                observations_sha256=sha256(directory / 'observations.csv')))
        fitted = fit_thresholds(calibration_runs)
        artifact = dict(study_id=study_id, calibration_runs=calibration_provenance,
                        selected_node_target=SELECTED_NODE_TARGET,
                        candidates=fitted, comparator='>', calibration_only=True)
        write_json(root / 'calibration.json', artifact)
        artifact_hash = sha256(root / 'calibration.json')
        candidates = dict(fitted)
        candidates['original_0.05'] = {n: dict(threshold=.05) for n in ('rx1', 'rx2')}
        selected = [fitted[str(SELECTED_NODE_TARGET)][n]['threshold'] for n in ('rx1', 'rx2')]
        results = []
        pooled = {str(factor): {label: empty_counts() for label in candidates}
                  for factor in AMPLITUDE_FACTORS}
        for factor in AMPLITUDE_FACTORS:
            for seed in evaluation_seeds:
                print(f'Evaluation: amplitude factor={factor}, seed={seed}', flush=True)
                directory, rows = run_flowgraph(root / 'evaluation', seed, cycles, selected, factor,
                    dict(study_id=study_id, phase='evaluation', averaging_window_samples=window_samples, calibration_sha256=artifact_hash))
                comparison = evaluate_candidates(rows, candidates)
                for label, counts in comparison.items():
                    add_counts(pooled[str(factor)][label], counts)
                result = dict(seed=seed, amplitude_factor=factor,
                              directory=str(directory.relative_to(root)), observations=len(rows),
                              config_sha256=sha256(directory / 'config.json'),
                              observations_sha256=sha256(directory / 'observations.csv'),
                              candidates=comparison,
                              per_scenario_selected={str(s): metrics(
                                  [row for row in rows if int(row['scenario']) == s], selected)
                                  for s in range(4)})
                results.append(result)
                write_json(root / 'evaluation_progress.json', results)
        report = dict(study_id=study_id, completed=True, averaging_window_samples=window_samples, calibration_sha256=artifact_hash,
                      selected_node_target=SELECTED_NODE_TARGET, selected_thresholds=selected,
                      calibration_noise_counts={n: fitted[str(SELECTED_NODE_TARGET)][n]['noise_observations']
                                                for n in ('rx1', 'rx2')},
                      amplitude_factor_definition='Voltage/complex amplitude; factors 0.5/1/2 correspond to about -6/0/+6 dB wanted power relative to baseline, not absolute SNR',
                      pooled_by_amplitude={factor: {label: rates(counts) for label, counts in choices.items()}
                                           for factor, choices in pooled.items()},
                      runs=results,
                      limitations=['Simulation only; no hardware RF validation',
                                   'Local mock ledger; no blockchain integration',
                                   'Three independent evaluation seeds per amplitude',
                                   'Same evaluation seeds across amplitudes intentionally pair noise realizations',
                                   'Observations within a run are not asserted statistically independent',
                                   'No confidence intervals or deployment accuracy claim',
                                   'Do not retune on evaluation data; use fresh test seeds for subsequent tuning'])
        write_json(root / 'study_summary.json', report)
        with (root / 'comparison.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(['amplitude_factor', 'node_target_or_original', 'detector',
                             'tp', 'fp', 'tn', 'fn', 'Pd', 'Pfa'])
            for factor, choices in report['pooled_by_amplitude'].items():
                for label, nodes in choices.items():
                    for node, m in nodes.items():
                        writer.writerow([factor, label, node, *[m[k] for k in ('tp', 'fp', 'tn', 'fn')],
                                         m['probability_detection'], m['probability_false_alarm']])
        plan['status'] = 'completed'
        write_json(root / 'study_plan.json', plan)
        print('COMPLETED. Upload:', root / 'study_summary.json', 'and', root / 'calibration.json', flush=True)
    except BaseException as exc:
        plan.update(status='incomplete', error=type(exc).__name__ + ': ' + str(exc))
        write_json(root / 'study_plan.json', plan)
        raise
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', default='simulation/generated')
    parser.add_argument('--cycles', type=int, default=100,
                        help='Cycles per run; default 100. Lower values are only smoke tests.')
    args = parser.parse_args()
    if args.cycles < 1:
        parser.error('--cycles must be positive')
    run_study(args.output_root, args.cycles)


if __name__ == '__main__':
    main()
