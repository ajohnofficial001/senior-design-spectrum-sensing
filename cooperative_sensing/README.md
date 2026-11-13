# Cooperative sensing

Current software status and evidence: [executed 50-evaluation combined reliability study](../experiments/combined_reliability_2026_11/README.md). See the [root README](../README.md) for November 13 status and remaining RF/blockchain work.

**Pending.**

Define a versioned report interface before implementation: node ID, observation time and clock basis, channel/frequency, sample rate, observation window, statistic and units, threshold, decision and configuration reference.

Compare candidate fusion methods using reproducible inputs. Specify missing-node behavior, duplicate handling, latency limits and stale-report policy. Multi-node performance must be measured independently of local simulation performance.

## Executable trust-layer pilot

See [study, results, threat model and run instructions](TRUST_STUDY.md). This adds signed synthetic reports and health monitoring; integration with the existing GNU Radio detector is pending.

## Detector integration

[Run the signed detector experiment](SIGNED_DETECTOR.md) against a fresh GNU Radio acquisition or existing spectral-feature exports. Original two-node OR behavior and reference-quality abstentions are preserved; transport and ledger receipts are simulated.

## Combined reliability

[Combined sensing noise and reporting stress](COMBINED_RELIABILITY.md) uses paired acquisitions and reports detection, false alarms and unavailable decisions separately.
