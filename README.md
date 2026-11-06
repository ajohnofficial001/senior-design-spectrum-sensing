# Senior Design: Spectrum Sensing

Collaborative engineering repository for GNU Radio spectrum sensing, with planned cooperative sensing and blockchain-backed recording of sensing decisions.

## Project status

Status as of November 6, 2026. A completed simulation is not evidence of RF performance.

| Workstream | Status | Evidence and limitations |
| --- | --- | --- |
| GNU Radio energy-detection simulation | Completed — team reported | Simulation flowgraphs, settings, plots and run records have not yet been committed. Reproduction from this repository is pending. |
| GNU Radio transmitter | Existing implementation preserved | [Flowgraph](transmitter/primary_tx.grc) and [generated Python](transmitter/primary_tx.py); hardware operation has not been validated by this repository update. |
| Receiver and RF validation | Pending | Receiver implementation, calibration, captured RF data and measured detection performance remain to be documented and validated. |
| Standalone detection algorithms | Pending | Extract reusable detector code and compare it with the completed simulation. |
| Cooperative sensing | Pending | Node reports, fusion rules and multi-node evaluation are planned. |
| Blockchain integration | Pending | Contracts, off-chain interface, deployment and end-to-end verification are planned. |
| Automated engineering tests | Pending | Test plan exists; no executable test suite or passing CI is claimed. |

## Intended system

The planned pipeline is: controlled transmitter → SDR receiver → local energy detector → cooperative fusion → off-chain submission → blockchain record. The completed simulation covers energy detection in a simulated environment; it does not establish completion of this entire pipeline.

For complex samples, a proposed reusable energy statistic is the mean squared magnitude over a window: E = sum(|x[n]|²) / N. A threshold produces an occupancy decision. The exact normalization, window length, threshold calibration and units used in the completed simulation must be recorded before comparisons are made. Energy detection indicates occupancy; it does not by itself identify an interferer or prove malicious activity.

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

There is no simulation run command yet: its completed artifacts are not present. There is no receiver, cooperative service, blockchain deployment or automated test runner yet.

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
