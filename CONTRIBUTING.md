# Contributing

## Workflow

1. Open an issue describing the engineering problem, acceptance criteria, affected subsystem and evidence needed.
2. Branch from current main: `git switch -c feature/<short-description>` (or `docs/`, `fix/`, `test/`).
3. Make a focused change and update relevant setup, interfaces and status documentation.
4. Review the diff, run checks appropriate to the change and record exact commands and outcomes.
5. Open a pull request into main. Request a teammate review and resolve comments before merging. Do not push project work directly to main.

Assign an owner and reviewer in the issue or PR; do not assume ownership from folder names. Branch protection is a separate maintainer setting and is not configured by these guidelines.

## GNU Radio changes

Treat .grc as the editable flowgraph source. Commit its generated Python companion when applicable and state the GNU Radio version used. Review generated diffs for machine-specific paths and device URIs. Preserve original behavior unless a change is explicitly intended. Separate relocation from functional edits.

## Evidence and status

Use “completed” only for work with stated scope. The team reports the GNU Radio energy-detection simulation complete, and its source is archived in simulation/; independent reproduction, plots and executed run records remain pending. RF validation, cooperative sensing and blockchain integration remain pending until supported by recorded checks. Avoid invented results, unmeasured performance claims or placeholders presented as implemented code.

For simulations, record seeds, signal/noise configuration, detector settings and software versions. For RF trials, also record hardware, gains, tuning, sample rate, calibration and ground truth. Use [the experiment template](experiments/TEMPLATE.md).

## Code and review standards

Use descriptive names, explicit units and documented interfaces. Keep algorithms independent of GUI and device code where practical. Add meaningful tests when implementing behavior; include noise-only, signal-present and boundary cases for detectors. Document numerical tolerances. Hardware tests must be opt-in and clearly identified.

PRs should describe the problem, resulting behavior, evidence, limitations and linked issue. Never commit secrets, private keys or large raw captures. Store large data externally with a checksum and access instructions. Confirm ignored files with `git status --ignored` when adding results.

## Documentation-only changes

Check relative links, folder names, status consistency and preservation of existing source files. Do not claim runtime validation from static review.
