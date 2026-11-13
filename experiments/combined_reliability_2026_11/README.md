# Executed combined reliability results

Team-supplied native GNU Radio software acquisition results, received November 11, 2026. These records document the team environment; they are not a new execution on the documentation authoring host.

Two noise conditions × five reporting profiles × five distinct source seeds = 50 evaluations. Each condition/profile pools 2,000 frames (1,000 occupied, 1,000 unoccupied). The repeated upload used the same seeds and is repeatability evidence, not ten independent seeds. Frames within acquisitions are correlated.

## Pooled counts

Unavailable frames are neither detector misses nor correct negatives.

| Noise | Reporting profile | TP | FN | FP | TN | Unavailable positive | Unavailable negative | Availability |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| normal | clean | 1000 | 0 | 36 | 964 | 0 | 0 | 100.0% |
| normal | loss_20pct | 649 | 0 | 24 | 631 | 351 | 345 | 65.2% |
| normal | burst_delay | 700 | 0 | 32 | 768 | 300 | 200 | 75.0% |
| normal | node_outage | 800 | 0 | 27 | 773 | 200 | 200 | 80.0% |
| normal | combined | 368 | 0 | 18 | 410 | 632 | 572 | 39.8% |
| high_noise | clean | 983 | 17 | 36 | 964 | 0 | 0 | 100.0% |
| high_noise | loss_20pct | 636 | 13 | 24 | 631 | 351 | 345 | 65.2% |
| high_noise | burst_delay | 689 | 11 | 32 | 768 | 300 | 200 | 75.0% |
| high_noise | node_outage | 788 | 12 | 27 | 773 | 200 | 200 | 80.0% |
| high_noise | combined | 361 | 7 | 18 | 410 | 632 | 572 | 39.8% |

High-noise clean reporting: detection = 983/1,000 = 98.3%; false alarms = 36/1,000 = 3.6%. High-noise combined faults: conditional detection = 361/(361+7) = 98.1%; detected fraction of all occupied frames = 361/1,000 = 36.1%. Overall availability = 796/2,000 = 39.8%. There were 632 occupied frames without a decision.

## Provenance and limits

- Original uploaded filenames: `combined_summary(1).json`, `combined_plan(1).json`, `combined_progress(1).json`; copied without editing their contents.
- Five seeds: 160001, 161001, 162001, 163001, 164001. Fifty cycles per acquisition.
- The summary retains per-run acquisition hashes, policies, public keys and original artifact paths. Those local Windows paths are provenance strings, not repository links.
- The full acquisition/audit directories and raw I/Q are not included in this evidence bundle. Summary publication alone does not allow independent cryptographic verification of all reports.
- High noise means 1.2× I/Q standard deviation, not variance or dB. Thresholds are frozen; no evaluation-set retuning.
- Transport, shared timing and local batch receipts are simulated. The 12 ms freshness policy is illustrative; 0.5 ms accepted-report delay is not measured network latency.
- No physical RF validation, deployed blockchain or prediction of future faults is demonstrated.

See [experiment method and reproduction commands](../../cooperative_sensing/COMBINED_RELIABILITY.md).
