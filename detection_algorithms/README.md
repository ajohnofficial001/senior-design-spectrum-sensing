# Detection algorithms

Current software status and evidence: [executed 50-evaluation combined reliability study](../experiments/combined_reliability_2026_11/README.md). See the [root README](../README.md) for November 13 status and remaining RF/blockchain work.

**Reusable implementation pending.** The team's completed GNU Radio energy-detection simulation is tracked separately in [simulation](../simulation/README.md).

Future modules should accept documented sample formats and return a statistic, threshold and decision with explicit units and normalization. Define window length, overlap, threshold calibration, numerical tolerances and invalid-input behavior.

Verify against known vectors and the archived simulation before using measured RF data. Keep signal processing separate from device access, GUI, fusion and blockchain code.
