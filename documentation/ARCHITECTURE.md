# Intended architecture

| Boundary | Responsibility | State |
| --- | --- | --- |
| Transmitter → RF channel | Controlled stimulus with known configuration | Transmitter files present; RF validation pending |
| Receiver → local detector | Complex samples plus acquisition metadata | Pending |
| Local detector → cooperative fusion | Timestamped statistic, threshold and occupancy decision | Pending reusable interface |
| Fusion → off-chain adapter | Aggregate decision and evidence references | Pending |
| Adapter → blockchain | Submit and verify a persistent sensing record | Pending |

GNU Radio energy-detection simulation has been completed by the team, and its source is now archived in [simulation](../simulation/README.md); independent reproduction remains pending. It is a separate evidence source from the intended hardware pipeline.

Before implementing interfaces, agree on sample representation, frequency and time units, normalization, schema version, identifiers, clock synchronization, error handling and evidence provenance. Add an example report and schema tests with the implementation.

A blockchain record can provide traceability for submitted data; it does not by itself verify RF observations or detector accuracy.
