# Full software-only simulation

> November 13 evidence update: the team supplied completed native software acquisition/replay results. See the [executed combined study](../experiments/combined_reliability_2026_11/README.md). Earlier pending statements below describe the authoring-time verification boundary; the authoring host still has not independently run GNU Radio. RF and live blockchain remain pending.


Open [full_simulation.grc](full_simulation.grc) in GNU Radio Companion 3.10.12.0. This is a new finite simulation based on [senior_flowchart.grc](senior_flowchart.grc); the original baseline and transmitter remain unchanged.

## What is simulated

One software source produces the same wanted signal and out-of-band interferer at two nodes, with separate seeded Gaussian noise streams and different receive gains. Each node has the baseline's full-band and filtered energy branches. The filtered powers enter a fusion/evaluation sink with ideal ground truth.

| Stage | Implementation |
| --- | --- |
| Wanted transmitter | Complex tone at +400 kHz; amplitude 0.0002 when active |
| Channel/node differences | RX1 gain 1; RX2 gain 0.65; independent complex AWGN |
| Noise | I and Q standard deviations 0.001 / 0.0012 at RX1 / RX2; seeds 101 / 102 |
| Interference | +600 kHz tone, amplitude 0.002 when active; outside the sensed band |
| Two local detectors | Frequency-translating FIR, magnitude squared, 1,000-sample moving mean, scale 1e6 |
| Filter | Same firdes.low_pass(1, 2e6, 20e3, 10e3) as the baseline; translation +400 kHz |
| Local decision | Filtered scaled power > per-node threshold; both default to 0.05 |
| Cooperation | Both OR and AND evaluated; fusion_rule chooses the mock-ledger decision |
| Reporting | Ideal synchronized, lossless streams; no network delays or packet loss |
| Ledger | Local JSONL hash chain only; no smart contract, consensus, network or deployment |

With two nodes, AND requires both votes; OR requires either vote. Neither is a three-node majority rule. A signal at the sensed frequency counts as occupancy regardless of identity; this energy detector cannot establish that a transmitter is malicious.

## Scenarios and timing

Four 20,000-sample scenarios repeat for ten cycles (800,000 samples, 0.4 seconds of simulated time):

| Scenario | Wanted occupancy truth | Out-of-band interferer |
| --- | --- | --- |
| 0: noise only | 0 | Off |
| 1: wanted signal | 1 | Off |
| 2: interferer only | 0 | On |
| 3: wanted and interferer | 1 | On |

The source returns end-of-stream automatically. No physical SDR, antenna, recorded capture, Qt display, wall-clock throttle or hardware driver is required by the execution path. GRC itself still needs its normal desktop environment.

Observations occur at window ends, every 1,000 samples. At each scenario boundary, the first `len(taps) + window_samples` samples are excluded from metrics to avoid FIR/moving-average transients. The ground-truth stream is not delayed; only settled interiors are evaluated. Logged time is sample_index/sample_rate, not wall time or measured latency. No decision-latency metric is claimed.

## Running

Use Python 3, NumPy and GNU Radio 3.10.12.0-compatible analog/filter/blocks runtime and GRC. This simulation does not need Soapy, PlutoSDR or IIO. The new GRC contains its two Python blocks inline and can be copied as one file.

From the repository root, either:

```bash
gnuradio-companion simulation/full_simulation.grc
```

Then Generate and Execute. Set GRC variables before generation; changing the hand-maintained runner does not change the GRC.

Or run the companion implementation of the default configuration:

```bash
python3 simulation/run_full_simulation.py
```

For command-line GRC generation:

```bash
mkdir -p simulation/generated/grcc
grcc -d simulation/generated/grcc simulation/full_simulation.grc
python3 simulation/generated/grcc/full_simulation.py
```

The compiler creates the embedded-block companion modules alongside its output. Keep those modules together. Paths are relative to the launch directory; use the repository root. Run one flowgraph execution per top-block instance.

## Outputs

Each execution creates a unique `simulation/generated/full_sim_<id>/` directory:

- `config.json`: settings, actual FIR taps, seed and mock-ledger mode.
- `observations.csv`: filtered/full-band powers, ground truth, both local decisions, OR/AND and selected fusion.
- `summary.json`: completion/sample counts, TP/FP/TN/FN, detection and false-alarm probabilities globally and per scenario. Undefined rates are null.
- `mock_ledger.jsonl`: sequence, configuration hash, observation, fused decision and previous-record hash.

The mock hash chain demonstrates record linkage. It provides no distributed trust, authentication or protection against someone rewriting the entire file. Its configuration hash does not hash the source code: record the Git commit in the experiment record. Outputs are ignored by Git. No raw I/Q captures are generated.

## Baseline differences and limitations

The detector's filter, averaging and power scaling are retained. Local decisions are sampled strict comparisons rather than the baseline's continuous GNU Radio threshold block (which retains state at exact equality). Noise is generated with NumPy and explicitly defined per I/Q component; this is not a claim of bitwise equivalence to GNU Radio's noise amplitude or seed semantics. The new source has explicit occupancy transitions and reproducible chunk-independent noise.

Default threshold 0.05 is inherited, not calibrated for either node. Low-amplitude wanted signals and differing node noise can yield misses or false alarms; there is no promised accuracy. Use noise-only runs to select thresholds, then evaluate on independent seeds. Vary wanted amplitude, interference amplitude, gains and seeds before reporting results. Changing samp_rate also requires checking filter cutoff/transition and tone offsets. Require window_samples <= guard_samples < segment_samples. Very short scenarios are rejected.

This models gain differences and AWGN, not a complete propagation channel: fading, multipath, oscillator offsets, asynchronous reports, malicious nodes and blockchain failures remain future extensions. RF validation and actual blockchain integration remain pending.

## Verification status

### GRC generation troubleshooting

If an older copy generates `SyntaxError: expression cannot contain assignment` with a line containing `self.cycles=self.cycles`, update `full_simulation.grc` and regenerate. The `run_config` variable now uses a dictionary literal with quoted keys. GRC 3.10 rewrites variable names inside keyword arguments such as `dict(cycles=cycles)`, producing invalid Python in generated setters. Do not fix only the generated Python: the next generation would overwrite that edit.

The generic no-flow-control/throttle warning is separate. This finite batch simulation intentionally runs faster than wall time and stops at end-of-stream; a throttle is not needed to fix the syntax error. Close other heavy applications if CPU use is inconvenient.

Code-generation regression checks require PyYAML as well as NumPy. Run `python3 -m unittest discover -s tests -p 'test_*.py' -v` for all seven behavioral/expression tests. They do not substitute for GNU Radio execution.

Python/NumPy behavioral tests exercise deterministic source generation, scenario truth, guard exclusion, fusion metrics, completion reporting and mock-ledger hashes:

```bash
python3 -m unittest discover -s tests -p 'test_full_simulation.py' -v
```

These tests use a minimal block-base substitute and do not test the GNU Radio scheduler or FIR implementation. GRC structure and embedded-code consistency are checked separately during development. GNU Radio is not installed in the authoring environment, so opening/compiling the GRC and end-to-end GNU Radio execution still need verification on a team laptop. Do not treat these static/unit checks as a successful simulation run or measured RF result.
