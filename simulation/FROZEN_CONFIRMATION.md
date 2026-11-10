# Confirm the selected 4,000-sample operating point

The window study selected 4,000 samples after observing 66.54% weak-signal detection, 100% baseline/strong detection and 4.63% false alarms with OR fusion. Because that setting was selected after comparing windows, confirm it on untouched data before treating it as the final operating point.

This study **does not calibrate or tune anything**. It freezes the window at 4,000 samples, RX1 threshold at 0.04487484693527222 and RX2 threshold at 0.06522393226623535. The original rates, settings and source report hash are archived in [frozen_settings.json](../experiments/frozen_window_confirmation/frozen_settings.json). The runner rejects altered operating-point values.

Five new source seeds (40001, 41001, 42001, 43001, 44001; node 2 uses seed + 1) evaluate amplitudes 0.5x, 1x and 2x. These seeds do not overlap any previous training or test node seeds. The same seeds are intentionally reused across amplitudes for paired noise comparisons.

At default 100 cycles, this runs 15 finite GNU Radio flowgraphs: 120 million samples total. Per amplitude, expect 8,000 observations: 4,000 occupied and 4,000 unoccupied. No hardware, GUI, browser or GRC editing is required. The signal/noise/filter/scenario model remains unchanged. The averaging span is 2 ms; actual end-to-end latency is not measured.

## Run on Windows

After merging/pulling, close older experiments and double-click:

`simulation/RUN_CONFIRMATION_WINDOWS.bat`

Or run from the repository root in Radioconda Prompt:

```bat
python -u simulation\run_frozen_confirmation.py
```

For an installation smoke test only, use `--cycles 1`. Nondefault cycle counts are explicitly flagged as smoke tests. Use the default 100-cycle run for the actual confirmation experiment.

Upload `confirmation_summary.json` and `confirmation_comparison.csv` from the printed `simulation/generated/confirmation_<id>/` directory. Individual runs, provenance hashes, a frozen settings copy and progress checkpoints are retained. Interrupted or failed experiments are marked incomplete; there is no automatic resume.

Compare detection/false-alarm rates and seed variation with the window study. Rates need not match exactly. The false-alarm target is not a guarantee. Do not retune thresholds based on confirmation data; if a redesign is needed, reserve a new confirmation set. This remains a software model with ideal reporting and a local mock ledger. Native GNU Radio execution must still be performed on the team laptop; authoring tests do not establish new performance results.
