#!/usr/bin/env python3
"""Confirm frozen noise-aware detector; evaluate independently trained fallback."""
import argparse
import csv
import json
from pathlib import Path
import uuid
import run_calibration_experiments as batch
from run_noise_aware_experiments import acquire, CASES
from noise_aware_detector import decide as frozen_decide
from reference_fallback import fallback_features, decide as fallback_decide
from calibrate_thresholds import upper_threshold
from run_stress_experiments import empty, rates

TRAIN = (80001, 81001, 82001, 83001, 84001)
TEST = (90001, 91001, 92001, 93001, 94001)
ARTIFACT = Path(__file__).resolve().parents[1] / 'experiments/noise_aware_confirmation/frozen_reference.json'


def frozen_settings():
    settings = json.loads(ARTIFACT.read_text())
    if settings['method'] != 'reference_8000' or settings['thresholds'] != [1.291901545099042, 1.3172280668473808]:
        raise ValueError('Frozen original operating point was altered')
    return settings


def fit_fallback(runs):
    output = []
    for node in range(2):
        values = []
        for rows in runs:
            for row in rows:
                if row['scenario'] == 0 and row['truth'] == 0:
                    f = fallback_features(row['nodes'][node]['long'])
                    if f['reliable']:
                        values.append(f['score'])
        threshold = upper_threshold(values, .025)
        output.append(dict(threshold=threshold, noise_observations=len(values),
                           calibration_pfa=sum(v > threshold for v in values) / len(values)))
    return output


def compare(rows, frozen, fallback):
    result = {}
    for method in ('frozen_reference_8000', 'fallback_reference_8000'):
        counts, retained = empty(), [0, 0, 0, 0, 0]
        for row in rows:
            votes = []
            for node in range(2):
                if method == 'frozen_reference_8000':
                    vote = frozen_decide(row['nodes'][node], 'reference_8000', frozen[node])[0]
                else:
                    features = fallback_features(row['nodes'][node]['long'])
                    retained[features['sectors_used']] += 1
                    vote = fallback_decide(features, fallback[node]['threshold'])
                votes.append(vote)
            truth = row['truth']
            if any(v is None for v in votes):
                counts['no_decision_positive' if truth else 'no_decision_negative'] += 1
            else:
                d = any(votes)
                counts[('tp' if truth else 'fp') if d else ('fn' if truth else 'tn')] += 1
        result[method] = dict(rates(counts), reference_sector_count_histogram=retained)
    return result


def run(output_root, cycles=100):
    frozen = frozen_settings()
    batch.assert_seed_separation(TRAIN, TEST)
    # Last experiment used 60001..64001 and 70001..72001; all prior seeds are below 80000.
    if min(TRAIN + TEST) < 80000:
        raise ValueError('Study requires untouched seeds')
    root = Path(output_root) / ('reference_confirmation_' + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    plan = dict(status='running', cycles=cycles, smoke_test=cycles != 100,
                frozen_thresholds=frozen['thresholds'], frozen_artifact_sha256=batch.sha256(ARTIFACT),
                fallback_training_seeds=TRAIN, evaluation_seeds=TEST,
                fallback_policy='Lower-pair anchor; retain sectors within 0.5..2 times anchor; require at least 2 agreeing sectors',
                cases=CASES)
    batch.write_json(root / 'reference_plan.json', plan)
    batch.write_json(root / 'frozen_reference.json', frozen)
    print('REFERENCE STUDY:', root.resolve(), flush=True)
    try:
        training, provenance = [], []
        for seed in TRAIN:
            print('Fallback calibration', seed, flush=True)
            directory, rows, _ = acquire(root / 'calibration', seed, cycles, 1., {})
            training.append(rows)
            provenance.append(dict(seed=seed, features_sha256=batch.sha256(directory / 'spectral_features.json')))
        fallback = fit_fallback(training)
        batch.write_json(root / 'fallback_calibration.json', dict(nodes=fallback, runs=provenance))
        calibration_hash = batch.sha256(root / 'fallback_calibration.json')
        results = []
        pooled = {case: {str(f): {m: empty() for m in ('frozen_reference_8000', 'fallback_reference_8000')}
                         for f in (.5, 1., 2.)} for case in CASES}
        for case, channel in CASES.items():
            for factor in (.5, 1., 2.):
                for seed in TEST:
                    print(case, factor, seed, flush=True)
                    directory, rows, baseline = acquire(root / 'evaluation', seed, cycles, factor, channel)
                    measured = compare(rows, frozen['thresholds'], fallback)
                    for method, values in measured.items():
                        for key in empty():
                            pooled[case][str(factor)][method][key] += values[key]
                    results.append(dict(case=case, amplitude_factor=factor, seed=seed,
                        directory=str(directory.relative_to(root)), observations=len(rows), methods=measured,
                        frozen_fir_baseline=baseline['metrics']['OR'],
                        features_sha256=batch.sha256(directory / 'spectral_features.json'),
                        config_sha256=batch.sha256(directory / 'config.json')))
                    batch.write_json(root / 'reference_progress.json', results)
        report = dict(completed=True, smoke_test=cycles != 100, cycles=cycles,
            frozen_original=frozen, frozen_artifact_sha256=plan['frozen_artifact_sha256'],
            fallback_calibration=fallback, fallback_calibration_sha256=calibration_hash,
            training_seeds=TRAIN, test_seeds=TEST, runs=results,
            pooled={c: {f: {m: rates(v) for m, v in methods.items()} for f, methods in factors.items()}
                    for c, factors in pooled.items()},
            limitations=['Fallback is new design with separate training; original thresholds never refitted',
                         'Lower-sector selection can underestimate nonuniform noise; calibration compensates only for training distribution',
                         'At least two representative clean sectors are assumed, not established by agreement alone',
                         'Target-only colored noise and contamination of all sectors remain unresolved',
                         'Shared 8000-sample frames provide matched original/fallback comparisons',
                         'Same seeds across channel cases intentionally pair noise',
                         'Reference-invalid frames cause abstention for either node',
                         'Software only, no real blockchain or hardware validation'])
        batch.write_json(root / 'reference_summary.json', report)
        with (root / 'reference_comparison.csv').open('w', newline='', encoding='utf-8') as stream:
            fields = ['case', 'amplitude_factor', 'method', *rates(empty()).keys()]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for case, factors in report['pooled'].items():
                for factor, methods in factors.items():
                    for method, values in methods.items():
                        writer.writerow(dict(case=case, amplitude_factor=factor, method=method, **values))
        plan['status'] = 'completed'
        batch.write_json(root / 'reference_plan.json', plan)
        print('COMPLETED: upload reference_summary.json and reference_comparison.csv from', root, flush=True)
    except BaseException as exc:
        plan.update(status='incomplete', error=type(exc).__name__ + ': ' + str(exc))
        batch.write_json(root / 'reference_plan.json', plan)
        raise
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', default='simulation/generated')
    parser.add_argument('--cycles', type=int, default=100)
    args = parser.parse_args()
    if args.cycles < 10:
        parser.error('Use at least 10 cycles; default 100 for the actual study')
    run(args.output_root, args.cycles)
