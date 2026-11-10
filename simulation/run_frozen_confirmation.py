#!/usr/bin/env python3
"""Independent confirmation of a frozen 4000-sample OR detector; no fitting."""
import argparse
import csv
import json
from pathlib import Path
import uuid
import run_calibration_experiments as batch

SEEDS = (40001, 41001, 42001, 43001, 44001)
FACTORS = (0.5, 1.0, 2.0)
SETTINGS = Path(__file__).resolve().parents[1] / 'experiments/frozen_window_confirmation/frozen_settings.json'


def validate_settings(settings):
    if (settings['window_samples'] != 4000 or settings['fusion_rule'] != 'OR' or
            settings['sample_rate'] != 2000000 or settings['comparator'] != '>'):
        raise ValueError('Unexpected frozen operating point')
    if settings['thresholds'] != [0.04487484693527222, 0.06522393226623535]:
        raise ValueError('Frozen thresholds changed; do not tune during confirmation')
    batch.assert_seed_separation((101, 1001, 2001, 3001, 4001, 5001, 6001,
                                 10001, 11001, 12001, 20001, 21001, 22001,
                                 23001, 24001, 30001, 31001, 32001), SEEDS)


def run(output_root, cycles=100):
    if cycles < 1:
        raise ValueError('cycles must be positive')
    settings = json.loads(SETTINGS.read_text())
    validate_settings(settings)
    root = Path(output_root) / ('confirmation_' + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    frozen_hash = batch.sha256(SETTINGS)
    plan = dict(status='running', cycles_per_run=cycles, seeds=SEEDS, amplitude_factors=FACTORS,
                window_samples=4000, thresholds=settings['thresholds'], frozen_settings_sha256=frozen_hash,
                policy='No calibration or threshold selection in this experiment',
                smoke_test=cycles != 100)
    batch.write_json(root / 'confirmation_plan.json', plan)
    batch.write_json(root / 'frozen_settings.json', settings)
    print('CONFIRMATION DIRECTORY:', root.resolve(), flush=True)
    pooled = {str(f): batch.empty_counts() for f in FACTORS}
    results = []
    try:
        for factor in FACTORS:
            for seed in SEEDS:
                print(f'Confirmation: amplitude={factor}, seed={seed}', flush=True)
                directory, rows = batch.run_flowgraph(root / 'runs', seed, cycles,
                    settings['thresholds'], factor,
                    dict(phase='frozen_confirmation', averaging_window_samples=4000,
                         frozen_settings_sha256=frozen_hash))
                measured = batch.metrics(rows, settings['thresholds'])
                batch.add_counts(pooled[str(factor)], measured)
                results.append(dict(seed=seed, amplitude_factor=factor,
                    directory=str(directory.relative_to(root)), observations=len(rows),
                    config_sha256=batch.sha256(directory / 'config.json'),
                    observations_sha256=batch.sha256(directory / 'observations.csv'),
                    metrics=measured,
                    per_scenario={str(s): batch.metrics([r for r in rows if int(r['scenario']) == s],
                                                       settings['thresholds']) for s in range(4)}))
                batch.write_json(root / 'confirmation_progress.json', results)
        report = dict(completed=True, smoke_test=cycles != 100, cycles_per_run=cycles,
            window_samples=4000, thresholds=settings['thresholds'], seeds=SEEDS,
            frozen_settings_sha256=frozen_hash,
            source_window_summary_sha256=settings['source_window_summary_sha256'],
            reference_or_metrics=settings['reference_metrics'],
            pooled_by_amplitude={f: batch.rates(c) for f, c in pooled.items()},
            runs=results,
            interpretation='Compare confirmation rates with the prior selected setting; no automatic success guarantee',
            limitations=['Five fresh evaluation seeds per amplitude; no refitting',
                         'Same seeds across amplitudes intentionally pair noise',
                         'No independence-based confidence intervals claimed',
                         'Averaging span is not measured end-to-end latency',
                         'Software AWGN/gain model and ideal reports only',
                         'Local mock ledger, not real blockchain'])
        batch.write_json(root / 'confirmation_summary.json', report)
        with (root / 'confirmation_comparison.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(['amplitude_factor', 'detector', 'tp', 'fp', 'tn', 'fn', 'Pd', 'Pfa'])
            for factor, nodes in report['pooled_by_amplitude'].items():
                for node, m in nodes.items():
                    writer.writerow([factor, node, *[m[k] for k in ('tp', 'fp', 'tn', 'fn')],
                                     m['probability_detection'], m['probability_false_alarm']])
        plan['status'] = 'completed'
        batch.write_json(root / 'confirmation_plan.json', plan)
        print('COMPLETED. Upload confirmation_summary.json and confirmation_comparison.csv from', root, flush=True)
    except BaseException as exc:
        plan.update(status='incomplete', error=type(exc).__name__ + ': ' + str(exc))
        batch.write_json(root / 'confirmation_plan.json', plan)
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
