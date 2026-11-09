# Per-node threshold calibration

The first uploaded GNU Radio run completed 800,000 samples. At a common threshold of 0.05 it reported RX1 false alarms of 6.58%, RX2 false alarms of 56.32%, and OR-fusion false alarms of 59.47%. These are initial-run results, not results of the new calibration.

## Calibration performed

Use only the first run's 190 settled noise-only observations per node (scenario 0, truth 0). Select the empirical 95th percentile using the higher order statistic and a strict `power > threshold` decision, targeting a 5% per-node false-alarm rate.

| Node | Original threshold | Calibrated threshold | False alarms on calibration noise |
| --- | --- | --- | --- |
| RX1 | 0.05 | 0.04954833164811134 | 9/190 = 4.74% |
| RX2 | 0.05 | 0.07464989274740219 | 9/190 = 4.74% |

These 4.74% rates are calibration fit statistics, not independent performance estimates. RX1's threshold decreases slightly; this is expected because calibration targets 5% on pure noise, whereas the initial overall false-alarm statistic also included the interferer-only scenario. RX2's threshold increases. A higher threshold may reduce both false alarms and detection.

The noise subset, original configuration, computed thresholds and provenance hashes are committed under [experiments/threshold_calibration/](../experiments/threshold_calibration/README.md). These are small simulation records, not RF captures. No signal-present data was used for threshold selection. With only 190 noise samples per node and shared filter memory, the target is approximate; no confidence interval is claimed.

## Run the independent evaluation

1. Open `simulation/full_simulation_calibrated.grc` in GNU Radio Companion 3.10.12.0.
2. Generate and Execute. This new file uses thresholds above, seeds **1001/1002**, and **100 cycles** (8,000,000 samples, 4 seconds of simulated time). The original baseline/full simulation is preserved. The new file is self-contained with embedded Python blocks; regenerating it creates `full_simulation_calibrated.py`.
3. Find the newly printed `simulation/generated/full_sim_<id>/` output directory. Use that run's files, not the original seed-101 run. Confirm `completed: true` in its summary.
4. From the repository root, compare original and calibrated thresholds on the same fresh observations:

```bash
python simulation/calibrate_thresholds.py evaluate --observations "PATH_TO_NEW_RUN/observations.csv" --config "PATH_TO_NEW_RUN/config.json" --summary "PATH_TO_NEW_RUN/summary.json" --calibration experiments/threshold_calibration/thresholds.json --output "PATH_TO_NEW_RUN/threshold_evaluation.json"
```

Replace `PATH_TO_NEW_RUN` with the actual directory. This evaluation uses only the standard library, verifies an independent source seed, matching signal/noise/filter settings, calibrated thresholds and a completed summary, then recomputes both original-threshold and calibrated-threshold decisions on fresh data. It reports RX1, RX2, OR and AND rates plus per-scenario calibrated results.

Upload the new run's config, summary, observations and `threshold_evaluation.json` to review measured simulation performance. **This independent GNU Radio run has not yet been executed in the authoring environment.**

## Reproduce calibration

```bash
python simulation/calibrate_thresholds.py calibrate --observations experiments/threshold_calibration/noise_only.csv --config experiments/threshold_calibration/source_config.json --output simulation/generated/recomputed_thresholds.json
```

Do not overwrite thresholds using evaluation observations. Further tuning requires a separate calibration set and fresh evaluation seeds. The 5% target is per node, not for OR fusion; two imperfect decisions can produce an OR false-alarm rate above 5%. AND reduces false alarms at the cost of missed signals. This remains software sensing with ideal reports and a mock ledger, not RF validation or real blockchain integration.
