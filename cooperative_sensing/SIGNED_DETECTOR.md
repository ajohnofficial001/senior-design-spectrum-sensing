# GNU Radio detector to authenticated reports

This adapter replays the existing two-node spectral detector's exported features through real Ed25519 report signing and verification. It uses the frozen original `reference_8000` thresholds, not the separately trained fallback. It preserves the existing policy: OR fusion only when both nodes have valid, timely reports and reliable references; otherwise abstain.

## Windows: next experiment

After checking out this feature branch or its merged changes, open Radioconda Prompt from the repository root:

```sh
python -m pip install -r cooperative_sensing/requirements-trust.txt
python cooperative_sensing/run_signed_detector.py
```

Or run `simulation/RUN_SIGNED_DETECTOR_WINDOWS.bat` after installing the dependency. The launcher expects `%USERPROFILE%\radioconda\python.exe`, matching the prior setup. Otherwise use the prompt command with your GNU Radio Python environment.

By default the runner acquires 20 fresh software-only GNU Radio cycles with seed 150001 using the existing source/collector, then runs five transport cases against the same detector features. No SDR is used. GNU Radio must be installed in that Python environment. Defaults may be overridden with `--cycles` and `--seed`; thresholds remain frozen and this runner performs no calibration.

Existing completed acquisitions can be replayed without GNU Radio:

```sh
python cooperative_sensing/run_signed_detector.py --input-run "simulation/generated/path-to-acquisition"
```

The directory must contain `config.json`, a completed `summary.json`, and `spectral_features.json` from the spectral acquisition runner. The adapter checks the expected number and ordering of frames. Older `observations.csv` files alone do not contain the reference features needed here. A supplied artifact's GNU Radio version is a provenance claim, not a cryptographic attestation.

## Outputs and interpretation

Upload **`signed_detector_summary.json`** from the printed `simulation/generated/signed_detector_*` directory. Keep the entire directory: the summary includes public verification keys, policy and artifact hashes; each case includes signed envelopes, feature evidence, validation reasons, per-frame direct/signed decisions and simulated batch commitments. Private keys remain ephemeral in memory. The acquisition directory is retained separately and its files are hashed in the summary. Keep both directories for reproducibility. File hashes require a trusted saved reference; they do not protect against rewriting every local file and manifest.

| Case | Injection at node 0, every tenth frame starting at sequence 5 | Expected behavior |
| --- | --- | --- |
| Clean | None | Signed decisions exactly match the direct frozen detector, including abstentions |
| Tamper | Flip vote after signing | Invalid signature; affected fusion epoch abstains |
| Replay | Duplicate a correctly signed report | Duplicate rejected; original report still usable |
| Delay | Arrival 20 ms after observation | Stale or out-of-order rejection; affected fusion epoch abstains |
| Drop | Omit report | Affected fusion epoch abstains; no fabricated report |

Do not interpret rejection as improved probability of detection. Report `tp`, `fp`, `tn`, `fn`, `no_decision`, and `changed_from_direct` together. An abstaining system can appear more accurate if unavailable decisions are excluded. The clean path is required to match direct decisions before a run can finish successfully. Attack selection is independent of truth and scenario.

## Evidence and policy bindings

- The original measured spectral score is divided by the appropriate node's frozen threshold for the protocol's `ratio` field. Quality consistency therefore uses a threshold of **1.0**, rather than the earlier synthetic pilot's 1.3. The original score, threshold, target power, noise-reference sectors, reference spread and reliability flag are retained in signed evidence.
- Node IDs remain the original two virtual receiver identities. The five-node pilot's majority helper is not used. No extra independent sensors are invented from the same two observations.
- Evidence includes sample index, method, sample rate and window length; it excludes ground truth and scenario labels. Ground truth enters only after decisions, for metrics. Dataset hashes bind the imported source artifact including its evaluation metadata.
- Observation time is `(sample_index + 1) / 2,000,000`, on a common simulated sample clock. Retained 8,000-sample frames have alternating **4 ms and 6 ms** intervals because each 20,000-sample scenario segment discards its last 4,000 samples. A fixed one-second heartbeat from the earlier synthetic pilot would be inappropriate here.
- Ordinary transport delay is 0.5 ms; the illustrative freshness policy allows 12 ms. Both are simulated design settings, not measured latency or calibrated production deadlines. Strict increasing sequences can reject reordered reports. Processing duration is not measured; its report field is zero and must not be read as an execution-time result.
- The validator checks signature, identity/session/configuration, evidence digest, sequence and freshness. The adapter additionally checks feature/report score, threshold, quality-state and sample-time consistency. It trusts imported feature extraction: it does not recompute the spectrum from raw IQ or prove that a signed measurement is truthful. A compromised authorized signer can fabricate consistent features.
- Ten-second local audit batching preserves the pilot's format; a short default acquisition may yield only one batch. Receipts are simulated, not transactions. No blockchain or live network is used.

## Verification status

Six new integration tests exercise real numerical spectral features, both-node clean equivalence, quality abstention, tamper/replay/delay/drop behavior, truth-label independence, evidence mismatch, complete outputs and incomplete-input rejection. They run without GNU Radio. The broader suite contains 52 tests.

Native GNU Radio acquisition and Windows launcher execution remain pending in the authoring environment, where GNU Radio is unavailable. This adapter is an offline acquired-feature replay, not a live GRC reporting block. No new RF performance or native runtime benchmark is claimed.

## Follow-up after the native run

Review your `signed_detector_summary.json` for clean-path equivalence and complete provenance first. Then vary transport loss/burst delay independently from sensing noise; compare freshness/availability policies against measured benign timing before setting deadlines. A live adapter and a real ledger adapter are separate later gates. The existing [threat model and timing references](TRUST_STUDY.md) still apply.
