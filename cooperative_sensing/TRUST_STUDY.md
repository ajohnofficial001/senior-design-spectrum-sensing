# Authenticated report and health-monitoring pilot

Executed November 10, 2026. This is a software protocol experiment with real Ed25519 signatures and synthetic measurements/timestamps. It does not extend the measured detection performance of the GNU Radio experiments and does not constitute RF validation or deployed blockchain integration.

## Research question

Can report authentication, availability monitoring and measurement-quality checks provide distinct evidence without confusing timing anomalies or disagreement with malicious behavior?

We test a frozen phi-style timing monitor against a fixed three-second timeout. We also test whether authenticated majority fusion tolerates one fabricated report and expose its failure when three of five identities collude. This is an engineering pilot, not a claim of a new algorithm or a security proof.

## Run from the repository root

In Windows Radioconda Prompt, macOS or Linux Python environment:

```sh
python -m pip install -r cooperative_sensing/requirements-trust.txt
python cooperative_sensing/run_trust_experiments.py
python -m unittest discover -s tests -p test_trust_protocol.py -v
```

No SDR or GNU Radio runtime is required. Each run prints its unique output directory under `simulation/generated/trust_*`. Keep the entire directory: `trust_plan.json`, progress, `trust_summary.json`, and per-case/per-seed audit envelopes, evidence bytes and simulated batch receipts. Public verification keys and trusted rotation times are in each summary row. Private keys exist only in process memory. Fresh ephemeral keys mean signatures and audit hashes vary across runs; seeded behavior and metrics should reproduce.

The committed [pilot summary](../experiments/trust_protocol_pilot/summary.json) retains compact metrics and runtime metadata, not raw signed logs. Regenerate full logs with the command above. No external archive of the original full logs is claimed.

## Architecture and trust boundaries

1. A sensing node creates a report binding node/key/session IDs, sequence, observation time, processing duration, configuration hash, evidence hash, score, vote and quality state. Ed25519 signs a restricted sorted JSON encoding; this is not a general cross-language JSON canonicalization standard.
2. A trusted central validator verifies the registered key, signature, exact schema, session, configuration, evidence bytes, increasing sequence and a three-second freshness bound. Only valid reports advance replay state. Rotation is a trusted control action; it revokes the old key and preserves sequence history within the session. Timing never determines key material.
3. Quality checks reject an uncertain reference or a vote inconsistent with its stated score. In this pilot, quality is self-reported and the score threshold is a synthetic 1.3. It is not the pair of thresholds calibrated for the earlier GNU Radio study. Self-consistent fabricated evidence can pass.
4. Availability monitoring uses time since the last authenticated report. Reported processing duration above 500 ms produces a separate diagnostic. A node may be alive while its reports are rejected; a warning therefore means missing acceptable reports, not necessarily hardware failure or attack.
5. Fusion accepts at most one vote per identity per epoch, requires three usable reports within two seconds of observation, and takes a strict majority. Ties abstain. Minority disagreement is diagnostic only: no automatic trust penalty or expulsion.
6. Every scored report, including rejected reports, is recorded with its status. Ten-second audit batches bind records with SHA-256 and a previous-batch hash. Confirmation time is simulated. Nothing is submitted to a blockchain.

The registry, configuration, enrollment/session establishment, key custody, validator and common simulated clock are trusted. A signature authenticates a key's message, not the truth of the physical world. A hash detects a change only against a separately trusted commitment; an attacker controlling all local logs can rewrite the whole local hash chain. A future ledger anchors commitments but cannot repair false original observations.

## Protocol and evaluation fixed before the pilot run

- Five virtual identities, 200 epochs per run, one expected report per second. Epochs 0–99 warm up validation; 100–199 score integrity and fusion. There are 100 evaluated fusion epochs per run, 50 signal-present and 50 absent.
- Twelve cases × five test seeds (120001, 121001, 122001, 123001, 124001). Cases are defined in the runner before execution. Most injections span epochs 140–159. Key rotation/revocation occurs at receiver time 150.
- Independent calibration seeds 110001–110300 generate positive Gaussian inter-arrival samples (mean 1 s, standard deviation 0.08 s). Frozen normal model: standard deviation floor 0.1 s, acceptable pause 0.2 s, phi threshold 3. This is a phi-inspired frozen model, not a full adaptive implementation or a claim that Gaussian timing fits real networks.
- Health sampling every 0.25 s from time 101 through 199. False-warning fraction = warned healthy node-ticks / all healthy node-ticks. Outage delay is measured from first missed scheduled report at 140, not from the last received report; recovery warnings after time 160 count as false warnings. Tick observations are correlated; they are not independent statistical trials.
- Integrity rejection rates use injected report labels solely for evaluation. Fusion errors compare with synthetic ground truth solely after decisions. Ground truth and attack labels are not inputs to validation or fusion.
- Honest jitter can reorder traffic: strict increasing sequence rejects late older reports. A real deployment may need a bounded reorder buffer rather than dropping every out-of-order report.
- The fixed timeout and phi threshold do not have matched false-warning rates. This pilot illustrates their operating points; it does not establish superiority at equal false-alarm cost. No threshold was tuned after seeing results.

## Observed pilot results

Across five seeds (500 fusion epochs per case):

| Case | Observation |
| --- | --- |
| Tampering, forged signatures, replay | Each rejected 100/100 injected reports; zero honest rejections in these cases |
| Revoked key | Rejected 250/250 injected old-key reports |
| Authorized key rotation | Zero honest report rejections |
| One signed fabricator | 0/100 fabrications rejected by integrity; zero fusion errors; 100 fabricated minority disagreements |
| Three colluding nodes | 0/300 fabrications rejected by integrity; 100/500 fusion errors; 200 honest minority disagreements |
| Honest jitter | One honest out-of-order rejection among 2,500 reports; zero fusion errors |
| Ledger delay | Node-health and fusion metrics unchanged from control; only simulated receipt delay changes |

| Timing scenario | Phi-style false-warning node-ticks | Fixed-timeout false-warning node-ticks |
| --- | ---: | ---: |
| Control | 0% | 0% |
| Honest jitter | 0.6005% | 0% |
| Honest CPU delay | 0.0509% | 0% |

Outage first-warning delays were 0.75 s (phi-style) and 2.25 s (fixed timeout) in each seed, relative to the first missed epoch. Availability was measured using accepted reports; integrity failures can also trigger health warnings. These numbers characterize the synthetic trace only. The attack cases are narrow deterministic checks; perfect rejection here is not a general detection guarantee.

## Research foundation

- Hayashibara, Défago, Yared and Katayama (2004), *The φ Accrual Failure Detector*, JAIST IS-RR-2004-010. [Primary report and PDF](https://hdl.handle.net/10119/4784). Basis for graded timing suspicion, not malicious-intent classification or prediction of future failure.
- [Apache Pekko failure-detector documentation](https://pekko.apache.org/docs/pekko/current/typed/failure-detector.html). Explains timing distributions, phi thresholds and acceptable pauses. This implementation deliberately freezes history to separate calibration and evaluation.
- [PyCA cryptography Ed25519 documentation](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/). The prototype uses real library signing and verification, not mock signatures.

## Next research gates

1. Feed the existing frozen GNU Radio detector's actual per-window score, reference-quality state and evidence digest into this report schema. Derive expected reporting intervals from sample rate, window duration and batching, rather than imposing the pilot's one-second interval. Keep node IDs virtual until RF exists.
2. Fit timing distributions using independent benign traces. Add burst loss, correlated delays, clock skew, restart/session transitions, heterogeneous observation locations, gradual faults and subtle collusion. Compare monitors at matched false-warning rates; report per-run uncertainty and sensitivity to thresholds. Never use test labels to train or auto-promote new baselines.
3. Design independently reviewed baseline versions with dataset/configuration hashes, signatures and explicit promotion approval. New observations cannot silently rewrite the trusted baseline. Allow legitimate environmental changes to produce uncertainty rather than automatic accusations.
4. Add a real ledger adapter only after the signed report interface is stable: off-chain evidence retention, on-chain batch commitments, baseline version and validator decision-policy hash, contract access controls, retries, idempotency, and separately measured submission/confirmation latency. Preserve rejected evidence and reason codes in the audit trail.
5. Evaluate robust fusion under spatially different observations and compromised identities. Majority alone is insufficient; use independently justified references or trusted anchors and state the adversary assumptions. No timing-based key derivation, automatic punishment of minorities, or claim of predictive maintenance is justified by this pilot.
