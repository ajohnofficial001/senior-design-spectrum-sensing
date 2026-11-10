# Frozen noise-aware confirmation and reference-sector fallback

Two distinct goals:

1. Confirm the original `reference_8000` algorithm on untouched seeds, using its existing thresholds **1.291901545099042 / 1.3172280668473808** with no refitting.
2. Evaluate a separately trained fallback that can use a consistent subset when some reference sectors contain narrowband interference.

The source report and calibration hashes are preserved in [frozen_reference.json](../experiments/noise_aware_confirmation/frozen_reference.json). Adding sector powers and target power to recorded spectral features does not change the original score, threshold, validity rule or decision. Original and fallback decisions are scored on the **same 8,000-sample frames**, so their counts, positions and truth match.

## Fallback policy, fixed before testing

Sort the four reference-sector powers. Their lower-pair mean seeds a candidate noise cluster. Keep sectors within 0.5 to 2 times that anchor. Require at least two survivors with max/min <=2. Normalize target energy by the median retained power and compare against separately calibrated ratio thresholds. If either node has no reliable estimate, OR fusion abstains; this is counted as unavailable service, not correct rejection.

Selecting lower sectors introduces downward bias. Therefore the fallback must have its own calibration; it cannot inherit the original ratio thresholds. Five new seeds (80001, 81001, 82001, 83001, 84001; node 2 uses +1) fit fallback thresholds from scenario-0 noise only, targeting 2.5% false alarms per node. The original thresholds remain unchanged.

Five untouched test seeds (90001, 91001, 92001, 93001, 94001) evaluate control noise, 1.2x noise, alternating noise, block fading and a +490 kHz reference interferer at weak/baseline/strong amplitudes. Default 100 cycles: **80 finite GNU Radio acquisitions**, including five calibration and 75 evaluation runs; 640 million source samples total. Expected spectral observations per case/amplitude: 4,000 (2,000 occupied and 2,000 unoccupied). Cases/amplitudes intentionally share seeds for paired comparisons, not independence.

## Run

Merge/pull, close older experiments, then double-click `simulation/RUN_REFERENCE_CONFIRMATION_WINDOWS.bat` or run from Radioconda Prompt in the repository root:

```bat
python -u simulation\run_reference_confirmation.py
```

Use `--cycles 10` only as an installation smoke test. Upload `reference_summary.json` and `reference_comparison.csv` from the printed `simulation/generated/reference_confirmation_<id>/` directory. The runner retains frozen settings, fallback calibration, per-run features/config hashes, progress and native frozen-FIR baseline outputs. Failures mark the plan incomplete; restart creates a new directory.

## Assessing the results

For the original detector, check whether the previous high-noise result (98.83% baseline detection, 3.75% false alarms) reproduces. For the fallback, examine false alarms, detection, decision coverage, detections over all occupied observations and retained-sector histograms together. Recovery from total abstention is useful only if the recovered decisions are accurate.

Do not interpret agreement as proof that sectors are clean. The fallback assumes at least two representative noise sectors; similarly contaminated sectors, broad spectral shaping and target-band-only colored noise can defeat it. Lower-cluster selection can also mistake a noise notch for the true noise floor. The current test covers one narrowband contaminant, not every interference pattern. Any fallback selection after reviewing these results needs a later untouched confirmation set.

No actual network loss, real blockchain, RF hardware or independently sampled confidence intervals are included. Native mock ledgers still record the original frozen FIR detector, not the spectral fallback. Software tests are not a substitute for running GNU Radio on the team laptop.
