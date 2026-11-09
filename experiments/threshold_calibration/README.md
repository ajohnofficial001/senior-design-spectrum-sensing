# Initial noise-only calibration evidence

- `noise_only.csv`: scenario-0, truth-0 subset from the user's first completed run; only sample index, scenario, truth and filtered node powers retained.
- `source_config.json`: original run configuration, including filter taps and seed 101.
- `thresholds.json`: reproducible per-node thresholds and calibration-only statistics, with hashes of the exact input files.
- `provenance.json`: SHA-256 hashes of the originally uploaded observations and summary, and subset selection rule.

Independent evaluation is pending. See [the calibration guide](../../simulation/THRESHOLD_CALIBRATION.md). Original full uploaded observations and summary are not included in this evidence subset.
