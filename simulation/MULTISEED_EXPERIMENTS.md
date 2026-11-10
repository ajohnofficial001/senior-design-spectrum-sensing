# Broader calibration and independent evaluation

The first independent-seed run showed the threshold tradeoff: calibrated OR fusion detected 98.74% of occupied observations, with 11.37% false alarms. RX2's false-alarm rate improved but its detection rate fell to 35.87%. That motivates broader noise calibration and a range of operating conditions; it does not justify tuning on that same evaluation run.

## Predeclared experiment plan

| Phase | Runs | Purpose |
| --- | --- | --- |
| Calibration | Five source seeds: 2001, 3001, 4001, 5001, 6001 | Pool only settled noise-only observations; fit each node separately |
| Evaluation | Three source seeds: 10001, 11001, 12001 at each of three amplitudes | Compare all fixed candidates on fresh noise |
| Amplitude sweep | 0.5x, 1x, 2x original wanted amplitude | Examine weaker/baseline/stronger signal detection |
| Threshold candidates | Per-node noise targets 1%, 2.5%, 5%, 10%, plus original threshold 0.05 | Show detection/false-alarm tradeoffs |
| Prespecified operating point | 2.5% target per node; OR fusion | Allocate approximately 5% false-alarm budget across two nodes |

Each node's second RNG uses source seed + 1. Both node seeds are disjoint between calibration and evaluation. The previous seeds 101 and 1001 are excluded. At default 100 cycles per run, the five calibration runs provide **9,500 noise-only observations per node**. Each amplitude is evaluated over three runs, with 22,800 total evaluated observations per amplitude (11,400 occupied and 11,400 unoccupied). These are expected counts from the finite schedule, not a claim that runs have already executed.

The 2.5% operating point is selected before seeing new test results. By the union bound, two nodes whose true false-alarm probabilities are each at most 2.5% have OR false-alarm probability at most 5%, without requiring independence. Empirical thresholds only approximate those node probabilities: the study must measure whether that budget holds. Do not claim a 5% guarantee from fitted quantiles.

Amplitude factors correspond to about -6, 0 and +6 dB wanted power relative to the baseline, not absolute SNR. Noise, node gain difference, sample rate, filter and window remain unchanged. The same test seeds are intentionally reused across amplitudes to pair noise realizations; they are not independent trials across amplitudes. Within each amplitude there are three distinct source seeds.

## Run on your Windows laptop

After merging and pulling this change, **close any previous simulation**, then either double-click:

`simulation/RUN_CALIBRATION_EXPERIMENTS_WINDOWS.bat`

The launcher uses `%USERPROFILE%\radioconda\python.exe`, matching the installed location in your GNU Radio logs. If Radioconda is elsewhere, open a Radioconda Prompt and use:

```bat
cd /d C:\Projects\spectrum-sensing\senior-design-spectrum-sensing
python -u simulation\run_calibration_experiments.py
```

This is a batch runner using the same GNU Radio blocks as the GRC. Do not open it as a flowgraph. No SDR, GUI window or browser is needed. It runs 14 finite flowgraphs sequentially and reports progress. There is no wall-clock throttle; runtime depends on the laptop. Each run processes 8,000,000 samples by default; the whole study processes 112,000,000 samples (56 seconds of simulated time, not expected wall-clock duration).

For a quick installation smoke test only, use `--cycles 2`. Short runs provide less calibration data and must not be reported as the full study. The default is 100. Each invocation creates its own uniquely named directory, so smoke tests and full studies are separated.

## Outputs to upload

The console prints a `simulation/generated/multiseed_<id>/` directory. Upload:

- `study_summary.json`: pooled results, seed-by-seed comparisons and per-scenario results for the prespecified operating point.
- `calibration.json`: fitted thresholds, calibration counts, fit rates and source-run hashes.
- `comparison.csv`: compact comparison of all threshold candidates, both local detectors and OR/AND rules at each amplitude.

The study also retains `study_plan.json`, individual run configs, observations, summaries and mock ledgers. Calibration is saved before the first evaluation run and its hash is recorded. Progress is checkpointed after each evaluation. If interrupted, the plan is marked incomplete and no final study summary is emitted. Rerunning starts a fresh study; automatic resume is not implemented.

## Interpretation

Compare detection and false alarms jointly. Pay attention to whether weak-node RX2 contributes useful detections or mostly false alarms. Report per-seed variation and counts, not only pooled percentages. All thresholds see the same fresh observations, enabling fair paired comparisons. Alternative candidates form a diagnostic curve: if you pick a new operating point after seeing it, use another untouched set of test seeds to confirm it.

The model still uses gain differences plus AWGN, ideal synchronized reports and a local mock ledger. No fading/multipath, network loss, RF hardware or real blockchain is added. Do not treat all observations as independent trials for confidence intervals. Native GNU Radio batch execution remains to be verified on your laptop; the authoring environment only supports static and mocked-runtime tests.
