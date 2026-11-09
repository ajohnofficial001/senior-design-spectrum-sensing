# Validation and evidence plan

## Simulation baseline

The completed simulation source is archived in [simulation](../simulation/README.md), with source-derived settings and an upload manifest. Record a tested environment, actual outputs and an executed experiment record. Reproduce it independently before using it as a regression baseline.

## RF validation — pending

Validate receiver acquisition and noise calibration before detector evaluation. Collect labeled signal-absent and signal-present trials with recorded hardware settings. Define occupied-band criteria, trial counts, detection probability, false-alarm probability and latency boundaries before interpreting results. Include repeatability and limitations.

Use controlled lab RF procedures and document the actual test arrangement and attenuation. A transmitter script's presence is not proof of a validated RF link.

## Cooperative validation — pending

Compare local and fused decisions using shared ground truth. Evaluate stale, missing, duplicated and conflicting reports, clock assumptions and node failures.

## Blockchain and end-to-end validation — pending

Test contract authorization and input validation, off-chain submission failures, retries and duplicates. Verify transaction receipts and evidence references on a development/test network. Then trace one labeled RF observation through detection, fusion and the recorded transaction.

## Evidence rules

A passing static check does not prove a simulation ran. A passing simulation does not prove RF performance. A successful transaction does not prove sensing accuracy. Record commands, configurations, actual outcomes and reviewer conclusions in [experiments](../experiments/README.md).
