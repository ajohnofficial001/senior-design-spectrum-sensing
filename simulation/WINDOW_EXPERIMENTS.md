# Experiment: longer energy-averaging windows

The previous multiseed study achieved 95.61% baseline detection and 4.61% false alarms with OR fusion, but only 25.50% weak-signal detection. This experiment tests whether longer averaging improves weak-signal detection while retaining the same nominal false-alarm budget.

| Window | Averaging span at 2 MS/s | Expected pooled calibration noise observations per node |
| --- | --- | --- |
| 1,000 samples | 0.5 ms | 9,500 |
| 2,000 samples | 1 ms | 4,500 |
| 4,000 samples | 2 ms | 2,000 |

Each window gets its own thresholds, fitted from five training seeds (20001, 21001, 22001, 23001, 24001). Three different evaluation seeds (30001, 31001, 32001) test wanted amplitudes 0.5x, 1x and 2x. Node 2 uses source seed + 1; all phase seed pairs are disjoint. These seeds exclude every previous study's seeds.

The same seeds are used across window settings for paired comparisons, not independent repetitions across windows. Sample rate, filter, noise, channel gain, interference, scenario durations and cycle counts remain unchanged. All original GRC files remain unchanged. The runner uses the same native GNU Radio DSP blocks without generating another GRC.

Recalibrate every window separately. The prespecified point is 2.5% target false alarms per node with OR fusion, approximately allocating a 5% combined budget. The previous four candidate targets and OR/AND comparisons remain available inside each window's sub-study; no candidate is automatically chosen from evaluation results.

## Run

Merge/pull the change, close previous simulations, and double-click:

`simulation/RUN_WINDOW_EXPERIMENTS_WINDOWS.bat`

Or, from the repository root in Radioconda Prompt:

```bat
python -u simulation\run_window_experiments.py
```

The script runs 42 finite flowgraphs (three windows, each with five calibration and nine evaluation runs). At the default 100 cycles it processes 336 million samples total. Runtime depends on the laptop. There is no GUI or SDR requirement. A quick installation smoke test can use `--cycles 5`; do not report that as the full 100-cycle experiment.

Upload `window_summary.json` and `window_comparison.csv` from the printed `simulation/generated/windows_<id>/` directory. The summary includes per-seed metrics, thresholds, counts and all candidate pooled results for each window. Individual run configs, observations, summaries and mock ledgers are retained underneath it. Progress is saved after each completed window; failed/interrupted studies are marked incomplete. Restarting starts a new study; resume is not implemented.

## Interpretation and limits

Compare weak-signal detection, measured false alarms, baseline detection and per-seed variation together. Longer windows also give fewer observations and require a longer settling exclusion. Each scenario is 20,000 samples; the guard is FIR tap count + averaging-window length. Observations are taken at window ends, so evaluation positions and counts differ across window lengths. Compare rates with their denominators, not raw counts alone.

The averaging span is not measured end-to-end detection latency. A real latency experiment would need transition-aware timing and explicit report/decision definitions; the present guard deliberately excludes transitions. More averaging may improve sensitivity but is not guaranteed to do so. No confidence interval based on independent observations is claimed.

GNU Radio batch execution must still be performed on the team laptop. Software tests cover report orchestration and parameter handling, not native scheduler/FIR operation. This remains an AWGN/gain simulation with ideal reports and a local mock ledger; physical RF and real blockchain validation are pending.
