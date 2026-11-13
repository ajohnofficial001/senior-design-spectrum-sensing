# 2D experiment animation brief

Status: presentation specification for Claude; no runnable animation or video is included. Use React and SVG, a white background, readable text, no external assets or backend. Title: **Cooperative Spectrum Sensing — Software Validation**. Aim for a 90-second deterministic timeline with play/pause, restart, scene selection, speed controls and a presentation mode.

## Visual layout

A large **GNU Radio — Virtual Radio Simulation** boundary contains a maroon primary transmitter, simulated channel, controlled orange interference source and two blue virtual receivers. Below, a **Python Processing and Validation** boundary contains detection, purple middleware/cooperative sensing and green local audit blocks. Moving waves represent simulated signals; moving packets represent reports. Keep these distinct.

## Six scenes

1. **Controlled scenarios:** Cycle through noise only, wanted signal, interference only, and wanted plus interference. Display ground truth separately: it evaluates the detector and is never an input to its decisions. Caption: “We generate known signal conditions so we can measure when the detector is correct.”
2. **Two observations:** Show different independent noise fluctuations on the receivers' complex I/Q waveforms. Caption: “Both receivers observe the same scenario, but their measurements contain independent noise.”
3. **Noise-aware detection:** Show target and reference frequency bands, their power ratio and a fixed calibrated threshold for each node. Fill an 8,000-sample window: at 2 MS/s this is 4 ms of simulated observation. Raising noise affects both bands. Thresholds stay frozen during evaluation; do not depict online adaptation. Label invented values “Illustrative values.” Caption: “Each node compares target-band power with a noise reference before making its sensing decision.”
4. **Signed reports and faults:** Packets carry node ID, frame ID, vote and Ed25519 signature. Offer clean, loss, burst delay, outage, altered report, replay and combined transport fault modes. Loss removes packets; delay holds them; outage stops one node's reports; alteration fails verification; replay rejects duplicates. Show identity, integrity, sequence, freshness and quality checks with reason codes. Note that valid signatures establish origin/integrity, not truthful measurements. Caption: “We check whether reports are authentic, timely and usable before combining them.”
5. **Cooperative decision:** Require both nodes' usable reports for the same frame. OR yields signal present if either vote is present; two absent votes yield signal absent. Missing/rejected/unusable reports yield **No Decision**. Never turn missing reports into absent votes. Caption: “Our current policy requires both reports. Reporting failures can prevent a decision even when sensing works.”
6. **Audit and evaluation:** Animate hash-linked local records storing observations, validation outcomes and fusion decisions. Label **Local ledger simulation**; no mining, deployed chain or smart-contract receipts. End with the measured high-noise counts below, visually separate from the illustrative animation.

## Recorded results panel

| High-noise occupied frames | Clean | Combined faults |
| --- | ---: | ---: |
| Detected | 983 | 361 |
| Missed | 17 | 7 |
| No decision | 0 | 632 |

Each bar contains 1,000 occupied frames. Clean detection is 98.3%. Combined conditional detection is 361/368 = 98.1%, while the detected fraction of all occupied frames is 361/1,000 = 36.1%. Overall availability, including unoccupied frames, is 796/2,000 = 39.8%. Do not confuse these denominators. Values come from the [published records](../experiments/combined_reliability_2026_11/README.md).

Final caption: “Reliable cooperative sensing requires both accurate measurements and dependable reporting.” Persistent footer: **Software simulation — physical RF and live blockchain validation pending.**

Deliver a runnable browser implementation and recording instructions. Use icons and labels as well as color, nonoverlapping arrows and slow transitions. Keep recorded results separate from interactive illustrative values. Do not imply that reference normalization guarantees detection under arbitrary interference or that timing predicts malicious behavior.
