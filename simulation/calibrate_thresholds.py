#!/usr/bin/env python3
"""Noise-only empirical threshold calibration and independent-seed evaluation.

Uses only Python's standard library. Powers are scaled digital units.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_rows(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError('No observations found')
    for row in rows:
        if int(row['truth']) not in (0, 1) or int(row['scenario']) not in range(4):
            raise ValueError('Invalid truth or scenario')
        for node in ('rx1', 'rx2'):
            value = float(row[node + '_filtered'])
            if not math.isfinite(value) or value < 0:
                raise ValueError('Expected finite nonnegative filtered power')
    return rows


def upper_threshold(values, target):
    if not 0 < target < 1:
        raise ValueError('target_pfa must be between zero and one')
    ordered = sorted(values)
    if len(ordered) < math.ceil(1 / target):
        raise ValueError('Too few noise observations for the requested target')
    # Same as empirical quantile(method="higher"); decisions use strict >.
    return ordered[math.ceil((len(ordered) - 1) * (1 - target))]


def calibrate(rows, config, target=0.05):
    noise = [r for r in rows if int(r['scenario']) == 0 and int(r['truth']) == 0]
    result = dict(method='empirical_quantile_higher', comparator='>',
                  target_node_pfa=target, calibration_seed=config['seed'],
                  noise_observations_per_node=len(noise), calibration_config=config,
                  units='mean squared magnitude multiplied by power_scale',
                  calibration_rates_are_not_heldout_results=True, nodes={})
    for node in ('rx1', 'rx2'):
        values = [float(r[node + '_filtered']) for r in noise]
        threshold = upper_threshold(values, target)
        result['nodes'][node] = dict(threshold=threshold,
                                    calibration_false_alarms=sum(v > threshold for v in values),
                                    calibration_pfa=sum(v > threshold for v in values) / len(values))
    return result


def metrics(rows, thresholds):
    counts = {name: dict(tp=0, fp=0, tn=0, fn=0) for name in ('rx1', 'rx2', 'OR', 'AND')}
    for row in rows:
        truth = int(row['truth'])
        local = [float(row[node + '_filtered']) > thresholds[i]
                 for i, node in enumerate(('rx1', 'rx2'))]
        for name, decision in zip(counts, local + [any(local), all(local)]):
            counts[name][('tp' if truth else 'fp') if decision else ('fn' if truth else 'tn')] += 1
    for count in counts.values():
        count['probability_detection'] = count['tp'] / (count['tp'] + count['fn']) if count['tp'] + count['fn'] else None
        count['probability_false_alarm'] = count['fp'] / (count['fp'] + count['tn']) if count['fp'] + count['tn'] else None
    return counts


def evaluate(rows, config, calibration):
    if config['seed'] in (calibration['calibration_seed'] - 1,
                          calibration['calibration_seed'], calibration['calibration_seed'] + 1):
        raise ValueError('Evaluation must use different node seeds from calibration')
    reference = calibration['calibration_config']
    # Trial count may increase; only seed, thresholds and number of cycles change.
    for key in ('sample_rate', 'segment_samples', 'window_samples', 'guard_samples',
                'tone_offset', 'signal_amplitude', 'interference_offset',
                'interference_amplitude', 'node2_gain', 'noise1', 'noise2',
                'noise_definition', 'power_scale', 'filter_taps', 'scenario_order'):
        if config[key] != reference[key]:
            raise ValueError('Calibration configuration mismatch: ' + key)
    thresholds = [calibration['nodes'][node]['threshold'] for node in ('rx1', 'rx2')]
    if config['thresholds'] != thresholds:
        raise ValueError('Evaluation GRC thresholds differ from calibration')
    if {int(r['scenario']) for r in rows} != set(range(4)):
        raise ValueError('All four evaluation scenarios are required')
    return dict(evaluation_seed=config['seed'], observations=len(rows),
                original_thresholds=reference['thresholds'], calibrated_thresholds=thresholds,
                original_on_fresh_data=metrics(rows, reference['thresholds']),
                calibrated_on_fresh_data=metrics(rows, thresholds),
                per_scenario={str(s): metrics([r for r in rows if int(r['scenario']) == s], thresholds)
                              for s in range(4)},
                limitations=['Simulation only', 'Single independent evaluation seed',
                             '5% target is per node, not a guarantee for OR fusion',
                             'No independent-window confidence interval is claimed'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('calibrate', 'evaluate'))
    parser.add_argument('--observations', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--target-pfa', type=float, default=0.05)
    parser.add_argument('--calibration', help='Calibration JSON required in evaluate mode')
    parser.add_argument('--summary', help='Completed-run summary required in evaluate mode')
    args = parser.parse_args()
    rows = load_rows(args.observations)
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    if args.mode == 'calibrate':
        result = calibrate(rows, config, args.target_pfa)
    else:
        if not args.calibration or not args.summary:
            parser.error('--calibration and --summary are required in evaluate mode')
        summary = json.loads(Path(args.summary).read_text())
        if config.get('calibration_sha256') != digest(args.calibration):
            raise ValueError('Evaluation run calibration hash does not match supplied artifact')
        if (summary.get('completed') is not True or
                summary.get('samples_consumed') != config['expected_samples'] or
                summary.get('observations') != len(rows)):
            raise ValueError('Evaluation run is incomplete or summary does not match observations')
        result = evaluate(rows, config, json.loads(Path(args.calibration).read_text()))
        result['calibration_sha256'] = digest(args.calibration)
        result['input_summary_sha256'] = digest(args.summary)
    result.update(input_observations_sha256=digest(args.observations),
                  input_config_sha256=digest(args.config))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(result.get('nodes', result.get('calibrated_on_fresh_data')), indent=2))


if __name__ == '__main__':
    main()
