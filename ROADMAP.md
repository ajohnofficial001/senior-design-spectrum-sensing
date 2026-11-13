# Project roadmap through April 2027

The official hardware-validation topic remains unchanged. This semester establishes a software baseline; the next semester evaluates the physical system. Dates below are proposed milestones, dependent on lab access and integration progress.

## Fall 2026 — software baseline

- [x] Preserve GNU Radio transmitter and imported energy-detection baseline.
- [x] Implement two-node software acquisition and reference-band detection.
- [x] Calibrate and freeze detector thresholds before held-out evaluation.
- [x] Implement signed reports, validation and two-node fusion.
- [x] Execute the native software combined reliability matrix: 50 evaluations across five source seeds.
- [x] Publish summaries, denominator-aware metrics, architecture diagrams and presentation materials.
- [x] Specify a 2D animation for presenting the experiments.
- [ ] Implement and verify the animation; insert final diagrams into the progress-deck placeholders.
- [ ] Independently reproduce from a fresh checkout; archive complete acquisitions/audits and environment manifest.

Evidence: [executed study](experiments/combined_reliability_2026_11/README.md). The same-seed rerun demonstrates repeatability, not additional independent trials.

## January 2027 — hardware setup and calibration

- [ ] Reconnect/discover SDRs and document receiver acquisition.
- [ ] Measure noise, gains, sample-clock behavior and benign report timing.
- [ ] Establish RF calibration and traceable labeled captures.

## February — controlled RF evaluation

- [ ] Run repeatable signal ON/OFF and controlled interference trials.
- [ ] Evaluate detection, false alarms, sensitivity and limitations over repeated runs.
- [ ] Compare RF results with software assumptions; retain separate evidence labels.

## March — cooperative RF and ledger integration

- [ ] Compare the strict two-report policy with explicitly specified alternatives; use fresh evaluation seeds/data.
- [ ] Measure missing/delayed reports and availability, not only conditional detection.
- [ ] Select blockchain platform and record schema; implement permissions, duplicate handling and retry behavior.
- [ ] Deploy to a development network and verify stored commitments against transaction receipts and off-chain evidence.

## April — integrated validation and handoff

- [ ] Evaluate the physical RF → detection → signed reporting → fusion → ledger path.
- [ ] Report accuracy, availability, measured latency and uncertainties.
- [ ] Document signed fabrication/collusion risks and limits of timing-based warnings.
- [ ] Finalize presentation, report, reproducible demo and reviewed release.

Hardware RF performance, calibrated timing, deployed blockchain and future-fault prediction remain unvalidated. Update this roadmap through feature branches and pull requests; never infer completed milestones from planned dates.
