# Combined sensing and reporting reliability study

> November 13 evidence update: the team supplied completed native software acquisition/replay results. See the [executed combined study](../experiments/combined_reliability_2026_11/README.md). Earlier pending statements below describe the authoring-time verification boundary; the authoring host still has not independently run GNU Radio. RF and live blockchain remain pending.


Question: under higher sensing noise and communication problems together, does the system still produce useful decisions, or does apparent accuracy come from abstaining?

## Run on the team Windows laptop

Run `simulation/RUN_COMBINED_RELIABILITY_WINDOWS.bat`, or use these commands in PowerShell from the repository root. These deliberately select the Radioconda installation used for your GNU Radio experiments:

```powershell
& "$env:USERPROFILE\radioconda\python.exe" -m pip install -r cooperative_sensing/requirements-trust.txt
& "$env:USERPROFILE\radioconda\python.exe" -u cooperative_sensing/run_combined_reliability.py
```

In an already activated Radioconda Prompt, `python cooperative_sensing/run_combined_reliability.py` also works. Ordinary PowerShell `python` may select a different environment without GNU Radio.

Default: 50 cycles per acquisition. For a shorter smoke run append `--cycles 5`; label that run as a smoke test. The runner writes the exact cycle count before acquisition. It does not claim unexecuted results.

Upload **`combined_summary.json`** from the final printed directory. Retain that entire `simulation/generated/combined_reliability_*` folder: it contains the plan, progress, ten original acquisitions, signed audit envelopes, public verification keys, policies, decisions and simulated batch commitments. A failed/interrupted run records an incomplete plan and must not be presented as completed. Private keys stay in memory. Do not upload private keys or introduce them into this folder.

## Fixed experiment matrix

Ten sensing acquisitions: two conditions × five fresh seeds (160001, 161001, 162001, 163001, 164001). These seeds are separate from previous detector calibration/confirmation and the single 150001 integration run. There is no retraining or threshold adjustment.

| Sensing condition | Parameters |
| --- | --- |
| Normal | Existing source noise and wanted-signal amplitude |
| High noise | Both nodes' noise I/Q standard deviation multiplied by 1.2; wanted signal unchanged |

Each acquisition uses the existing GNU Radio source and spectral collector. All five reporting profiles replay exactly the same acquired features, giving 50 evaluated combinations. Matching seeds across normal and high noise provide paired source realizations; transport RNG uses a separate seed offset of 1,000,000 and the same schedule across noise conditions.

| Transport profile | Policy |
| --- | --- |
| Clean | All reports arrive after simulated 0.5 ms delay |
| Loss | Each report independently dropped with probability 20% |
| Burst delay | Node 0 delayed 20 ms for frames 10–19 of every 40-frame block |
| Node outage | Node 0 absent for the middle 20% of acquired frames |
| Combined | Union of the same random loss, burst delay and outage schedules; dropped reports take precedence |

Loss probability is per node report, not per fusion epoch. Even with perfect sensing, independent loss alone gives an expected two-report availability near 0.8² = 64%; that is an analytical reference, not a measured outcome or target. Bursts/outages are defined on sample-frame positions, not actual wall-clock network time. They never use truth/scenario labels. Report loss models reporting availability and does not remove samples from sensing acquisition.

## Frozen decision policy

Use the original 8,000-sample reference-band detector and frozen node thresholds `[1.291901545099042, 1.3172280668473808]`. Both nodes must have an authenticated, fresh, usable report; OR combines their votes. Missing, rejected or uncertain-reference reports cause abstention. Do not substitute five-node majority fusion or a single-node fallback in this experiment.

The signed protocol, evidence bindings and limitations are described in [SIGNED_DETECTOR.md](SIGNED_DETECTOR.md). Observation time comes from the 2 MS/s sample clock. The existing illustrative 12 ms freshness limit remains fixed; it has not been calibrated from laptop communication measurements. Strict increasing sequence validation may reject late packets as out of order before the freshness check. Rejection is not a claim of malicious behavior.

## Read the results without hiding abstentions

Every result row includes signed protocol metrics, acquisition hashes, condition, seed, `transport_profile`, and `reliability`. The inherited `case` field is `clean` because this experiment supplies its own delivery schedule instead of the earlier attack injection; group results using `condition` and `transport_profile`.

| Metric | Meaning |
| --- | --- |
| Availability | Decided frames / all evaluated frames |
| Detection given decision | TP / (TP + FN), conditional on a decision |
| False alarm given decision | FP / (FP + TN), conditional on a decision |
| Detected fraction of all positives | TP / all signal-present frames, including unavailable frames in the denominator |
| False-alarm fraction of all negatives | FP / all signal-absent frames; interpret alongside unavailable negatives |
| Unavailable positive/negative fractions | Missing decisions separately for occupied and unoccupied frames |
| Simulated decision delay | Last usable report arrival minus observation time, only for decided epochs; mean and maximum |

The conditional delay may remain near 0.5 ms when delayed packets are rejected. That does not indicate good service: the lost decisions appear in availability and unavailable fractions. It is not a measured processing or network latency. Unavailable frames are recorded separately rather than silently counted as correct negatives or detector misses.

Every clean signed run must match its own direct detector's decisions, including quality abstentions. Compare each stressed profile with that same acquisition's clean row, then summarize variability over the five seeds. Do not treat individual correlated windows as independent trials or claim a narrow confidence interval from their raw count. A high-noise condition can change false alarms and detection; transport rejection can change conditional metrics through selection even though detector thresholds are untouched.

## Verification and remaining gates

The authoring test suite uses actual numerical spectral-feature fixtures to verify the signed adapter. New tests cover seeded paired schedules, combined injection precedence, conditional/unconditional metrics, no-decision handling, invalid delivery schedules, all 50 runner combinations using an explicitly labeled fixture acquisition callback, paired provenance and failure recording. Fixture runner tests are not native GNU Radio experiments. Existing signed-detector tests also verify saved signatures/evidence and local batch records.

GNU Radio is unavailable in the authoring environment. Native acquisition of this combined matrix and Windows launcher execution remain pending on the team laptop. No new detection-performance result is claimed before that run. Sensing is software-only; transport and batch receipts are simulated. No RF hardware, blockchain network, calibrated timing threshold or prediction of future faults is claimed.
