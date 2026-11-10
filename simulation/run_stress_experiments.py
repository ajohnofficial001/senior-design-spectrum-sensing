#!/usr/bin/env python3
"""Stress the frozen detector; no recalibration, hardware or real blockchain."""
import argparse
import csv
import json
from pathlib import Path
import random
import uuid
import run_calibration_experiments as batch
from run_frozen_confirmation import SETTINGS, validate_settings

SEEDS = (50001, 51001, 52001)
FACTORS = (.5, 1.0, 2.0)
CASES = {
    'control': ({}, (0., 0.)),
    'noise_high': ({'noise_factor': 1.2}, (0., 0.)),
    'noise_step': ({'noise_step': True}, (0., 0.)),
    'block_fading': ({'fading': True}, (0., 0.)),
    'report_loss_20pct': ({}, (.2, .2)),
    'rx1_outage': ({}, (1., 0.)),
    'both_outage': ({}, (1., 1.)),
    'combined': ({'noise_step': True, 'fading': True}, (.2, .2)),
}


def tally_reports(rows, thresholds, losses, seed):
    if any(not 0 <= probability <= 1 for probability in losses):
        raise ValueError('Loss probabilities must be in [0, 1]')
    rng = random.Random(seed + 200000)
    output = {policy: dict(tp=0, fp=0, tn=0, fn=0, no_decision_positive=0,
                           no_decision_negative=0) for policy in ('available_OR', 'require_both_OR')}
    records = []
    for row in rows:
        present = [rng.random() >= p for p in losses]
        votes = [float(row[n + '_filtered']) > thresholds[i] for i, n in enumerate(('rx1', 'rx2'))]
        truth = int(row['truth'])
        record = dict(sample_index=int(row['sample_index']), truth=truth,
                      rx1_available=int(present[0]), rx2_available=int(present[1]),
                      rx1_vote=int(votes[0]) if present[0] else None,
                      rx2_vote=int(votes[1]) if present[1] else None)
        for policy, eligible in [('available_OR', any(present)), ('require_both_OR', all(present))]:
            decision = int(any(v and available for v, available in zip(votes, present))) if eligible else None
            record[policy] = decision
            if decision is None:
                output[policy]['no_decision_positive' if truth else 'no_decision_negative'] += 1
            else:
                output[policy][('tp' if truth else 'fp') if decision else ('fn' if truth else 'tn')] += 1
        records.append(record)
    return output, records


def empty():
    return dict(tp=0, fp=0, tn=0, fn=0, no_decision_positive=0, no_decision_negative=0)


def rates(count):
    positive = count['tp'] + count['fn']
    negative = count['fp'] + count['tn']
    total = positive + negative + count['no_decision_positive'] + count['no_decision_negative']
    return dict(count, decision_coverage=(positive + negative) / total if total else None,
        detection_given_decision=count['tp'] / positive if positive else None,
        false_alarm_given_decision=count['fp'] / negative if negative else None,
        detected_fraction_all_occupied=count['tp'] / (positive + count['no_decision_positive'])
            if positive + count['no_decision_positive'] else None)


def run(output_root, cycles=100):
    settings = json.loads(SETTINGS.read_text())
    validate_settings(settings)
    batch.assert_seed_separation((101, 1001, 2001, 3001, 4001, 5001, 6001,
        10001, 11001, 12001, 20001, 21001, 22001, 23001, 24001, 30001, 31001,
        32001, 40001, 41001, 42001, 43001, 44001), SEEDS)
    root = Path(output_root) / ('stress_' + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    plan = dict(status='running', cycles_per_run=cycles, seeds=SEEDS, factors=FACTORS,
                cases=CASES, frozen_settings_sha256=batch.sha256(SETTINGS),
                window_samples=4000, thresholds=settings['thresholds'], no_recalibration=True,
                smoke_test=cycles != 100)
    batch.write_json(root / 'stress_plan.json', plan)
    batch.write_json(root / 'frozen_settings.json', settings)
    print('STRESS DIRECTORY:', root.resolve(), flush=True)
    results, cache, pooled = [], {}, {}
    try:
        for case, (channel, losses) in CASES.items():
            pooled[case] = {str(f): {p: empty() for p in ('available_OR', 'require_both_OR')} for f in FACTORS}
            for factor in FACTORS:
                for seed in SEEDS:
                    print(f'{case}: amplitude={factor}, seed={seed}', flush=True)
                    key = (json.dumps(channel, sort_keys=True), factor, seed)
                    if key not in cache:
                        cache[key] = batch.run_flowgraph(root / 'native_runs', seed, cycles,
                            settings['thresholds'], factor, dict(phase='frozen_stress',
                                averaging_window_samples=4000, channel_stress=channel,
                                frozen_settings_sha256=plan['frozen_settings_sha256']))
                    directory, rows = cache[key]
                    counts, records = tally_reports(rows, settings['thresholds'], losses, seed)
                    loss_directory = root / 'report_trials' / case
                    loss_directory.mkdir(parents=True, exist_ok=True)
                    record_path = loss_directory / f'{factor}_{seed}.csv'
                    with record_path.open('w', newline='', encoding='utf-8') as stream:
                        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
                        writer.writeheader()
                        writer.writerows(records)
                    for policy in counts:
                        for k, value in counts[policy].items():
                            pooled[case][str(factor)][policy][k] += value
                    results.append(dict(case=case, amplitude_factor=factor, seed=seed,
                        source_directory=str(directory.relative_to(root)), observations=len(rows),
                        observations_sha256=batch.sha256(directory / 'observations.csv'),
                        config_sha256=batch.sha256(directory / 'config.json'),
                        report_records_sha256=batch.sha256(record_path),
                        local_before_report_loss=batch.metrics(rows, settings['thresholds']),
                        policies={policy: rates(c) for policy, c in counts.items()}))
                    batch.write_json(root / 'stress_progress.json', results)
        report = dict(completed=True, smoke_test=cycles != 100, window_samples=4000,
            thresholds=settings['thresholds'], seeds=SEEDS, cycles_per_run=cycles,
            frozen_settings_sha256=plan['frozen_settings_sha256'], native_runs=len(cache),
            pooled={case: {factor: {policy: rates(c) for policy, c in policies.items()}
                           for factor, policies in factors.items()} for case, factors in pooled.items()},
            runs=results, limitations=[
                'No-decision is abstention, not an absent-signal decision',
                'Report loss is an offline seeded Bernoulli model; no real network or delay model',
                'Native mock ledgers contain ideal pre-loss decisions, not loss-aware decisions',
                'Channel fading is constant per scenario segment and independent by node/segment',
                'All channel cases use paired source seeds; case outcomes are not independent',
                'Noise factors scale I/Q amplitude, not power',
                'No confidence intervals claimed; software only, no real blockchain'])
        batch.write_json(root / 'stress_summary.json', report)
        with (root / 'stress_comparison.csv').open('w', newline='', encoding='utf-8') as stream:
            fields = ['case', 'amplitude_factor', 'policy', *rates(empty()).keys()]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for case, factors in report['pooled'].items():
                for factor, policies in factors.items():
                    for policy, m in policies.items():
                        writer.writerow(dict(case=case, amplitude_factor=factor, policy=policy, **m))
        plan['status'] = 'completed'
        batch.write_json(root / 'stress_plan.json', plan)
        print('COMPLETED. Upload stress_summary.json and stress_comparison.csv from', root, flush=True)
    except BaseException as exc:
        plan.update(status='incomplete', error=type(exc).__name__ + ': ' + str(exc))
        batch.write_json(root / 'stress_plan.json', plan)
        raise
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', default='simulation/generated')
    parser.add_argument('--cycles', type=int, default=100)
    args = parser.parse_args()
    if args.cycles < 1:
        parser.error('--cycles must be positive')
    run(args.output_root, args.cycles)


if __name__ == '__main__':
    main()
