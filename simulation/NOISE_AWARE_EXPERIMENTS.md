# Noise-aware detection and longer listening

Higher noise defeated the fixed energy threshold: the completed stress study reported 99.17% false alarms under 1.2x noise amplitude. Listening longer alone cannot remove a systematic noise-floor error. This new experiment combines reference-band normalization with longer observations and a separately calibrated two-look rule. It is an experimental redesign, not a promise of high-noise accuracy.

## Algorithms

1. Compute a Hann-windowed complex FFT for each node. Average spectral power in the target band, +380 to +420 kHz (same nominal target center, but not identical to the frozen FIR response).
2. Estimate simultaneous noise from four reference sectors: +280..310, +310..340, +460..490 and +490..520 kHz. Use the median sector mean as the reference. The +600 kHz interferer is outside these sectors.
3. Divide target power by reference power. Under broadband noise that scales both regions equally, this ratio removes absolute noise-level changes. Calibrated ratio thresholds produce time-varying equivalent energy thresholds: ratio_threshold × current_reference_power.
4. Check reference agreement. If maximum/minimum sector power exceeds 4, reject that reference as unreliable. Flat contamination or target-band-only colored noise may evade this check; it is not a universal noise classifier.
5. Compare `reference_4000`, `reference_8000`, and `two_look`. The two-look rule can declare presence after 4,000 samples; otherwise it listens to 8,000. Its threshold is fitted to the maximum of the valid short/long ratios on training noise, accounting for both opportunities to trigger. It does not apply the same single-look threshold twice.

The 8,000-sample Hann measurement and the 4,000-prefix overlap intentionally. Frames do not cross 20,000-sample scenario boundaries; two complete frames are used per segment and 4,000 trailing samples are discarded. There is no FIR startup in the spectral detector. The frozen native FIR detector runs in parallel on the same source, with its original guard and evaluation cadence. Their observation counts and positions differ and must be reported; comparisons are not per-observation paired classifications.

The detector functions accept samples/features and thresholds, **not occupancy labels**. Ground truth is attached separately for selecting training noise and computing evaluation metrics. No test labels, known noise schedule or source noise amplitude enter the detector's decisions. Reference-band locations, disagreement limit and decision policies are predeclared.

For fixed-look OR fusion, both nodes must have reliable references; otherwise the system abstains. In two-look mode each node may accept a reliable positive short look immediately; otherwise a valid long look supplies its decision. If either node has no decision, fusion abstains. Output includes coverage, abstention counts, conditional detection/false alarms and detections over all occupied observations. Early positives are not revoked by a later reference warning. Nominal listening samples are algorithmic costs, not measured latency; this offline implementation computes both looks before scoring and reports the maximum node listening length for fusion.

## Study design

Five fresh calibration seeds (60001, 61001, 62001, 63001, 64001; second node +1) fit each method/node from scenario-0 training noise only, targeting 2.5% per node. Three untouched test seeds (70001, 71001, 72001) evaluate weak/baseline/strong amplitudes under:

- unchanged control noise;
- 1.2x I/Q noise amplitude;
- alternating 0.8x/1.2x noise by complete cycle;
- independent Rayleigh block fading;
- a deliberately contaminating tone at +490 kHz in the reference bands.

Default 100 cycles: 50 finite native GNU Radio acquisitions (five calibration plus 45 evaluation runs), 400 million source samples. Each evaluation run has 800 spectral observations versus 1,600 native frozen-detector observations. Source noise is paired across conditions/algorithms by using the same seeds, not independent across every comparison. No report-loss cases are included yet: this experiment isolates detector adaptation.

High noise also reduces actual signal-to-noise ratio. Normalization can control false alarms but cannot manufacture information about a signal buried in noise. Longer integration may help, with added listening time. Success requires measured detection and false alarms jointly, with abstentions visible.

## Run

Merge/pull, close prior simulations, then double-click `simulation/RUN_NOISE_AWARE_WINDOWS.bat`.

Or, from Radioconda Prompt in the repository root:

```bat
python -u simulation\run_noise_aware_experiments.py
```

Use `--cycles 10` for a smoke test only; default 100 is the study. Upload `noise_aware_summary.json` and `noise_aware_comparison.csv` from the printed `simulation/generated/noise_aware_<id>/` folder. Individual spectral features, frozen native outputs/configs and progress records are retained. Failed runs are marked incomplete; restart creates a fresh study.

Do not select a winning rule from this study and claim untouched confirmation: reserve another set of seeds afterward. The reference bands must represent target-band noise; narrowband reference contamination, broadband spectral shaping, or a band-specific noise rise can break that assumption. Full RF/channel realism, transport failures and actual blockchain integration remain separate work. Existing mock ledgers record the frozen FIR detector, not the adaptive decisions. GNU Radio execution still requires the team laptop; authoring unit tests are not measured GNU Radio results.
