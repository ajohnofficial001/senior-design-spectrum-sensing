# Frozen detector stress tests

Keep the confirmed 4,000-sample window, RX1 threshold 0.04487484693527222, RX2 threshold 0.06522393226623535, and OR decision rule fixed. **No recalibration occurs.** The archived frozen settings from the confirmation experiment remain the source of truth.

| Case | Changed condition |
| --- | --- |
| control | Original gain/AWGN model, no report loss |
| noise_high | I/Q noise amplitude multiplied by 1.2 (noise power multiplied by 1.44) |
| noise_step | Noise amplitude alternates 0.8x / 1.2x by complete four-scenario cycle |
| block_fading | Independent unit-mean-power complex Rayleigh coefficients per node and 20,000-sample scenario segment |
| report_loss_20pct | Each node's report independently dropped with probability 0.2 |
| rx1_outage | All RX1 reports missing; RX2 reports available |
| both_outage | Both reports missing: deliberate no-decision check |
| combined | Alternating noise, block fading and 20% report loss per node |

Fading multiplies wanted signal and interferer before receiver noise is added. It is constant within a segment; it does not model multipath, Doppler or a calibrated physical link. Noise/fading changes occur on scenario boundaries, where the existing FIR/window guard excludes transients. Noise alternates by complete cycles so both noise levels see all occupancy/interference scenarios. It changes during the simulation, but no transition-detection latency is measured.

Three fresh source seeds (50001, 51001, 52001; node 2 uses +1) evaluate weak/baseline/strong wanted amplitudes. Channel RNG uses seed + 100000; offline report-loss RNG uses seed + 200000. Source seeds are checked against previous training, selection and confirmation node seeds. The same seeds are deliberately paired across cases and amplitudes; results across cases are not independent trials.

## Missing reports

Two OR policies are evaluated with the same detector settings:

- `available_OR`: OR the reports actually received. If neither arrives, abstain.
- `require_both_OR`: decide only when both reports arrive. Otherwise abstain.

Reports are dropped after local detector observations have been produced, using a deterministic offline Bernoulli model. No network sockets, packet delays, stale messages or real transport are simulated. Loss-mask draws are paired across cases. Native mock ledgers describe ideal **pre-loss** fusion; the separately saved report-trial CSVs describe availability and loss-aware decisions. Do not claim the ledger verifies post-loss decisions.

Read these metrics together:

- `decision_coverage`: fraction of observations receiving a decision.
- `detection_given_decision` and `false_alarm_given_decision`: conditional rates among decisions, with separate truth denominators.
- `detected_fraction_all_occupied`: positive detections divided by all occupied observations, including those with no decision.
- `no_decision_positive` / `no_decision_negative`: abstentions by ground truth.

For both-outage, coverage is zero, conditional rates are null, and detected fraction is zero. Missing information must never count as correct rejection. The strict-both policy is a reporting-availability comparison, not a change to OR into AND.

## Run on Windows

After merging and pulling, close earlier experiments and double-click `simulation/RUN_STRESS_EXPERIMENTS_WINDOWS.bat`, or run from Radioconda Prompt in the repository root:

```bat
python -u simulation\run_stress_experiments.py
```

Default: 100 cycles, 72 case/seed/amplitude trials. Cases sharing identical channel conditions reuse the exact native observations, so only 45 unique GNU Radio runs execute (360 million samples). Saved case-specific CSVs contain the simulated report availability and decisions. A smoke test can use `--cycles 2`; any nondefault cycle count is flagged as a smoke test.

Upload `stress_summary.json` and `stress_comparison.csv` from the printed `simulation/generated/stress_<id>/` directory. Individual runs/configurations, local pre-loss mock ledgers, report masks, hashes and progress records are retained. Failures mark the plan incomplete; restarting creates a new study rather than resuming.

This experiment measures where the **fixed** detector degrades. It does not promise the 5% false-alarm target under changed noise. Any later adaptation should be a separate design with fresh evaluation data. No real RF hardware, actual blockchain, or independence-based confidence intervals are included. Native GNU Radio execution remains to be performed on the team laptop.
