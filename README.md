# Senior Design: Spectrum Sensing

Collaborative engineering repository for GNU Radio spectrum sensing, with planned cooperative sensing and blockchain-backed recording of sensing decisions.

## Project status

Status as of November 10, 2026. A completed simulation is not evidence of RF performance.

| Workstream | Status | Evidence and limitations |
| --- | --- | --- |
| GNU Radio energy-detection simulation | Completed — team reported | [Flowgraph and generated Python](simulation/README.md) imported from the team archive; settings documented. Independent reproduction, labeled plots and run records remain pending. |
| GNU Radio transmitter | Existing implementation preserved | [Flowgraph](transmitter/primary_tx.grc) and [generated Python](transmitter/primary_tx.py); hardware operation has not been validated by this repository update. |
| Receiver and RF validation | Pending | Receiver implementation, calibration, captured RF data and measured detection performance remain to be documented and validated. |
| Standalone detection algorithms | Pending | Extract reusable detector code and compare it with the completed simulation. |
| Cooperative sensing | Software protocol pilot executed | [Signed-report and timing study](cooperative_sensing/TRUST_STUDY.md): five virtual identities, 60 synthetic-trace runs; GNU Radio report integration and RF validation pending. |
| Blockchain integration | Pending | Contracts, off-chain interface, deployment and end-to-end verification are planned. |
| Automated engineering tests | 56 tests passed in authoring environment | Behavioral, experiment-runner and signed-report checks; GNU Radio scheduling/FIR integration and Windows execution remain unverified. |

## Combined reliability experiment

The [combined reliability study](cooperative_sensing/COMBINED_RELIABILITY.md) crosses normal/high noise with clean reporting, random loss, burst delay, a node outage and their combination. Five seeds produce 50 paired evaluations with explicit decision availability. Run `simulation/RUN_COMBINED_RELIABILITY_WINDOWS.bat`; native results remain pending.

## Signed detector integration

The [signed detector adapter](cooperative_sensing/SIGNED_DETECTOR.md) connects exported GNU Radio spectral features to authenticated reports using the frozen original thresholds and two-node OR policy. It compares clean, altered, replayed, delayed and missing reports. Run `simulation/RUN_SIGNED_DETECTOR_WINDOWS.bat` on the team laptop, or follow the prompt commands in the guide. Numerical integration tests pass; native acquisition and Windows execution remain pending.

## Report integrity and health pilot

The [trust-layer study](cooperative_sensing/TRUST_STUDY.md) adds real Ed25519 signatures, replay protection, explicit key rotation, timing warnings, quorum fusion and simulated ten-second audit commitments. The [executed pilot metrics](experiments/trust_protocol_pilot/summary.json) include honest delays and majority collusion. Timing warnings do not prove malicious behavior; authenticated fabricated observations can pass verification. No real blockchain is deployed.

## Full software-only model

A new [full_simulation.grc](simulation/full_simulation.grc) extends the preserved baseline with two noisy sensing nodes, wanted-signal on/off scenarios, out-of-band interference, OR/AND fusion, metrics and a local mock ledger. See the [run guide and limitations](simulation/FULL_SIMULATION.md). Five Python/NumPy behavioral tests pass; GNU Radio compilation and runtime verification remain pending. This model does not constitute RF validation or actual blockchain integration.

## Intended system

The planned pipeline is: controlled transmitter → SDR receiver → local energy detector → cooperative fusion → off-chain submission → blockchain record. The completed simulation covers energy detection in a simulated environment; it does not establish completion of this entire pipeline.

For complex samples, a proposed reusable energy statistic is the mean squared magnitude over a window: E = sum(|x[n]|²) / N. A threshold produces an occupancy decision. The imported flowgraph uses a 1,000-sample moving mean of squared magnitude, scaled by 1,000,000, with threshold 0.05 on the filtered branch. See [simulation settings](simulation/README.md); threshold calibration remains pending. Energy detection indicates occupancy; it does not by itself identify an interferer or prove malicious activity.

## Repository map

| Path | Purpose |
| --- | --- |
| [transmitter/](transmitter/README.md) | Preserved GNU Radio transmitter source and generated Python |
| [receiver/](receiver/README.md) | Planned RF acquisition and receiver flowgraphs |
| [simulation/](simulation/README.md) | Archive and reproduce the completed energy-detection simulation |
| [detection_algorithms/](detection_algorithms/README.md) | Planned reusable detectors, calibration and evaluation |
| [cooperative_sensing/](cooperative_sensing/README.md) | Planned sensing-node messages and fusion |
| [blockchain/](blockchain/README.md) | Planned contracts and off-chain integration |
| [experiments/](experiments/README.md) | Experiment plans, metadata and reviewed results |
| [documentation/](documentation/README.md) | Architecture, setup, decisions and evidence |
| [tests/](tests/README.md) | Verification plan and future automated tests |

## Getting started

1. Clone the repository and enter its directory:
   ```bash
   git clone https://github.com/ajohnofficial001/senior-design-spectrum-sensing.git
   cd senior-design-spectrum-sensing
   ```
2. Read the [setup guide](documentation/SETUP.md) and [validation plan](documentation/VALIDATION.md).
3. For transmitter work, inspect the flowgraph in GNU Radio Companion:
   ```bash
   gnuradio-companion transmitter/primary_tx.grc
   ```
4. Review the device URI and RF configuration before executing it. Running the flowgraph or Python script starts the hardware transmitter. The [transmitter guide](transmitter/README.md) explains dependencies and current settings.

See [simulation run instructions](simulation/README.md) for the imported software-only flowgraph. Independent runtime reproduction is still pending. No hardware receiver, deployed cooperative service or blockchain deployment is available. Behavioral test instructions are in the full simulation guide.

## Reproducible engineering

Every reported result should identify the commit, environment, configuration, input source, run procedure and raw-data reference. Distinguish simulated data from measured RF data. Record detection probability, false-alarm probability and latency only when supported by labeled trials and a defined measurement method. Do not infer RF performance from simulation plots.

Use the [experiment template](experiments/TEMPLATE.md), [contributor guidelines](CONTRIBUTING.md) and [roadmap](ROADMAP.md). Proposed work should enter through an issue and feature-branch pull request. Keep credentials, wallet keys, local device settings and large captures out of Git.

## License

The existing generated transmitter Python file carries an SPDX GPL-3.0 notice, which is preserved. No repository-wide license has been selected; contributors should agree on licensing before redistribution of new project material.


## Development checklist

Before reporting a spectrum-sensing result, record:
- the source of the samples (simulation or measured RF);
- center frequency, sample rate and gain settings;
- detector window length and threshold method;
- the commit or configuration used to produce the result; and
- the metric or observation used to evaluate performance.

This checklist helps keep simulation results, measured RF results and future cooperative-sensing experiments reproducible and clearly separated.
