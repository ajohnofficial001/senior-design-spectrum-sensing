#!/usr/bin/env python3
"""Compare separately calibrated energy-detector windows on fresh seeds."""
import argparse
import csv
import json
from pathlib import Path
import uuid
import run_calibration_experiments as batch

WINDOWS = (1000, 2000, 4000)
CALIBRATION_SEEDS = (20001, 21001, 22001, 23001, 24001)
EVALUATION_SEEDS = (30001, 31001, 32001)


def collect_result(root, window, directory):
    summary_path = directory / 'study_summary.json'
    report = json.loads(summary_path.read_text())
    if not report['completed'] or report['averaging_window_samples'] != window:
        raise ValueError('Incomplete or mismatched window result')
    return dict(window_samples=window, averaging_span_ms=window / 2000000 * 1000,
                directory=str(directory.relative_to(root)),
                summary_sha256=batch.sha256(summary_path),
                selected_thresholds=report['selected_thresholds'],
                calibration_noise_counts=report['calibration_noise_counts'],
                pooled_by_amplitude=report['pooled_by_amplitude'],
                selected_per_seed=[dict(seed=r['seed'], amplitude_factor=r['amplitude_factor'],
                                        metrics=r['candidates']['0.025']) for r in report['runs']])


def run(output_root, cycles):
    root = Path(output_root) / ('windows_' + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    plan = dict(status='running', windows=WINDOWS, cycles_per_run=cycles,
                calibration_source_seeds=CALIBRATION_SEEDS,
                evaluation_source_seeds=EVALUATION_SEEDS,
                selected_node_target=.025,
                purpose='Window length comparison at a fixed nominal false-alarm budget',
                comparison_policy='Recalibrate each window using training noise only; no test-data tuning')
    batch.write_json(root / 'window_plan.json', plan)
    print('WINDOW STUDY DIRECTORY:', root.resolve(), flush=True)
    results = []
    try:
        for window in WINDOWS:
            print('STARTING WINDOW:', window, flush=True)
            directory = batch.run_study(root / ('window_' + str(window)), cycles,
                window_samples=window, calibration_seeds=CALIBRATION_SEEDS,
                evaluation_seeds=EVALUATION_SEEDS)
            results.append(collect_result(root, window, directory))
            batch.write_json(root / 'window_progress.json', results)
        report = dict(completed=True, cycles_per_run=cycles, results=results,
                      selected_node_target=.025,
                      limitations=['Simulation only; local mock ledger',
                                   'Averaging span is not measured detection latency',
                                   'Same source seeds across windows intentionally pair noise',
                                   'Different windows have different observation counts and settling guards',
                                   'No confidence intervals or statistically independent windows claimed',
                                   'Any operating point chosen after reviewing this study needs fresh confirmation seeds'])
        batch.write_json(root / 'window_summary.json', report)
        with (root / 'window_comparison.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(['window_samples', 'averaging_span_ms', 'amplitude_factor',
                             'detector', 'tp', 'fp', 'tn', 'fn', 'Pd', 'Pfa'])
            for result in results:
                for factor, choices in result['pooled_by_amplitude'].items():
                    for node, metrics in choices['0.025'].items():
                        writer.writerow([result['window_samples'], result['averaging_span_ms'],
                            factor, node, *[metrics[k] for k in ('tp', 'fp', 'tn', 'fn')],
                            metrics['probability_detection'], metrics['probability_false_alarm']])
        plan['status'] = 'completed'
        batch.write_json(root / 'window_plan.json', plan)
        print('COMPLETED. Upload window_summary.json and window_comparison.csv from', root, flush=True)
    except BaseException as exc:
        plan.update(status='incomplete', error=type(exc).__name__ + ': ' + str(exc))
        batch.write_json(root / 'window_plan.json', plan)
        raise
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', default='simulation/generated')
    parser.add_argument('--cycles', type=int, default=100)
    args = parser.parse_args()
    if args.cycles < 5:
        parser.error('--cycles must be at least 5; use default 100 for the actual study')
    run(args.output_root, args.cycles)


if __name__ == '__main__':
    main()
