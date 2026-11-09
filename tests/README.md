# Tests

[test_full_simulation.py](test_full_simulation.py) contains five Python/NumPy behavioral tests for the software simulation blocks. Run `python3 -m unittest discover -s tests -p test_full_simulation.py -v` from the repository root. These use a substitute block base and do not validate GNU Radio scheduling, native FIR behavior, RF hardware or a blockchain network. See the [simulation guide](../simulation/FULL_SIMULATION.md). The broader verification plan follows.

| Layer | Planned coverage |
| --- | --- |
| Detector unit tests | Known complex vectors, noise-only and signal-present cases, threshold boundary, normalization and invalid inputs |
| Simulation regression | Reproduce archived GNU Radio baseline with recorded settings and tolerances |
| Receiver / RF | Opt-in hardware acquisition and labeled RF trials; never run implicitly |
| Cooperative sensing | Fusion decisions, missing/stale/duplicate reports and clock assumptions |
| Blockchain | Access control, valid/invalid submissions, retries and receipt verification |
| End-to-end | Trace observation and decision to its ledger evidence |

Add integration checks and tested GNU Radio dependency versions when the flowgraph is run on the team environment. Do not report the broader plan as completed tests. See [validation](../documentation/VALIDATION.md).
