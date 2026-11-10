# GNU Radio energy-detection simulation

Next: [confirm the frozen 8,000-sample noise-aware detector and test a reference-sector fallback](REFERENCE_CONFIRMATION.md) on untouched seeds.

Experimental redesign: [noise-aware reference-band thresholding and longer listening](NOISE_AWARE_EXPERIMENTS.md), with the confirmed frozen detector retained as a parallel baseline.

Next: [stress the frozen detector](STRESS_EXPERIMENTS.md) under changing noise, block fading and missing reports; no thresholds are refitted.

After the window comparison, run the [frozen 4,000-sample confirmation study](FROZEN_CONFIRMATION.md) on untouched seeds without recalibrating thresholds.

Next study: [longer averaging-window experiments](WINDOW_EXPERIMENTS.md), with separate calibration for 1,000, 2,000 and 4,000 samples and fresh evaluation seeds.

For the new two-node, finite software-only model, see [full_simulation.grc](full_simulation.grc) and its [guide](FULL_SIMULATION.md). The original imported baseline below is preserved.

After the first completed run, separate node thresholds were fitted using noise-only observations. Use [full_simulation_calibrated.grc](full_simulation_calibrated.grc) for a fresh-seed evaluation and follow the [calibration guide](THRESHOLD_CALIBRATION.md). The first independent-seed run completed; it showed a detection/false-alarm tradeoff summarized in the multiseed guide.

For broader calibration across five seeds and evaluation across three seeds at three signal amplitudes, use the [multiseed experiment guide](MULTISEED_EXPERIMENTS.md) and [batch runner](run_calibration_experiments.py). These new batch runs still need execution on the team laptop.

**Completed by the team; source imported November 9, 2026. Independent runtime reproduction remains pending.**

- [senior_flowchart.grc](senior_flowchart.grc): editable GNU Radio Companion source.
- [senior_flowchart.py](senior_flowchart.py): supplied generated Python, GNU Radio 3.10.12.0.
- [Archive manifest](../experiments/uploaded_archive_manifest.json): original file sizes, SHA-256 hashes and import disposition.

## Active signal path and settings

The active source is a simulated complex tone plus Gaussian noise. The Pluto source, head block and complex capture sink in the .grc are disabled. There is no active hardware receiver or cooperative fusion in this flowgraph.

| Parameter | Value in supplied source |
| --- | --- |
| Sample rate | 2,000,000 samples/s |
| Spectrum display center | 915,000,000 Hz (display label, not active RF tuning) |
| Complex cosine | +400,000 Hz offset, amplitude 0.0002 |
| Gaussian noise | Amplitude parameter 0.001; seed parameter 0 |
| Translating FIR | +400,000 Hz center; low-pass gain 1, cutoff 20,000 Hz, transition 10,000 Hz; decimation 1 |
| Energy estimate | Magnitude squared → moving average of 1,000 samples, scale 1/1,000 |
| Display/output scale | Energy multiplied by 1,000,000 on both branches |
| Filtered decision | Threshold block low/high 0.05; initial state 0 |
| Saved power streams | Keep one in 2,000 samples after scaling; float streams |

The threshold is in scaled digital power units, not calibrated watts or dBm. Its equivalent unscaled value is 5e-8. The window spans 0.5 ms of sample time; output spacing is nominally 1 ms of sample time. Filter and moving-average startup transients must be considered. The GUI titled `threshold` displays the threshold block's binary output, not the threshold setting itself.

## Run from the repository root

Use a compatible GNU Radio 3.10.12.0 environment with Python 3, PyQt5, sip and GNU Radio analog, blocks, filter and Qt GUI modules. A graphical session is required. Opening the .grc may require IIO block definitions for its disabled Pluto block; the supplied Python does not import IIO or access an SDR.

```bash
mkdir -p simulation/generated
python3 simulation/senior_flowchart.py
```

Or open `gnuradio-companion simulation/senior_flowchart.grc` from the repository root and generate/run it. Stop through the GUI or Ctrl+C. These are source-derived instructions; runtime verification of this import remains pending.

The imported Windows file-sink paths were changed to `simulation/generated/` in both source files; signal-processing settings and connections were preserved. Paths resolve against the current working directory. Runs overwrite `full_power.f32` and `filtered_power.f32`; copy results to a separately named experiment location before rerunning. The disabled complex sink also points into that output directory.

There is no throttle or active finite-run head block. This software-only graph runs as fast as scheduling allows and continues until stopped; wall time is not sample time, and files can grow quickly. The noise seed is recorded as supplied; bitwise repeatability is not established. The supplied .grc and Python were not regenerated during import.

## Uploaded binary files

The archive also contains `full_power.f32`, `filtered_power.f32`, `rx1_200k.c64`, `rx1_400k.c64`, `rx1_600k.c64`, `rx1_tx_off.c64` and `rx2_tx_off.c64`. They remain in the original uploaded archive rather than Git, following the repository raw-data policy. Their checksums and sizes are in the manifest. Extract them locally if needed; `.f32` and `.c64` files are ignored by Git.

The simulation does not read these files. Extensions suggest float32 power and complex64 sample streams, but byte order, acquisition settings, creation dates and provenance are unconfirmed. Filenames alone do not establish RF capture origin, ground truth, or cooperative sensing. No association between these outputs and a particular source revision has been verified.

## Remaining evidence

Reproduce the simulation, record dependency versions and duration/sample counts, save labeled plots and fill out an [experiment record](../experiments/TEMPLATE.md). Confirm binary formats and capture provenance before analysis. RF validation and blockchain integration remain pending.
