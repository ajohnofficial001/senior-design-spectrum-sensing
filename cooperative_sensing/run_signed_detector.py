#!/usr/bin/env python3
"""Sign existing spectral detector features; simulate transport separately from sensing."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import uuid
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'simulation'))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from trust_protocol import Validator, canonical, digest, sign_report, quality, audit_batches
from run_reference_confirmation import frozen_settings, ARTIFACT
from noise_aware_detector import decide

CASES = ('clean', 'tamper', 'replay', 'delay', 'drop')


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_run(folder):
    """Require a complete acquisition artifact; provenance is a claim, not attestation."""
    folder = Path(folder)
    config = json.loads((folder / 'config.json').read_text())
    summary = json.loads((folder / 'summary.json').read_text())
    rows = json.loads((folder / 'spectral_features.json').read_text())
    if summary.get('completed') is not True or not rows:
        raise ValueError('A complete acquisition with spectral features is required')
    expected = config.get('expected_samples')
    if type(expected) is not int or expected <= 0 or expected % 80000:
        raise ValueError('Expected whole four-scenario cycles of 80,000 samples')
    indices = [r['sample_index'] for r in rows]
    wanted = [start + offset for start in range(0, expected, 20000) for offset in (7999, 15999)]
    if indices != wanted:
        raise ValueError('Missing, repeated or reordered spectral frames')
    provenance = dict(input_directory=str(folder.resolve()),
        files={name: sha(folder / name) for name in ('config.json', 'summary.json', 'spectral_features.json')},
        source_claim='GNU Radio acquisition' if 'gnuradio_version' in config else 'Unattested imported feature fixture',
        gnuradio_version=config.get('gnuradio_version'), expected_samples=expected)
    return rows, provenance


def evidence_for(row, node, threshold):
    # No truth/scenario label is included in the signed message or decision evidence.
    f = row['nodes'][node]['long']
    sectors = f['reference_sectors']
    if len(sectors) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in sectors):
        raise ValueError('Expected four finite nonnegative reference powers')
    for field in ('score', 'target_power', 'noise_reference', 'reference_spread'):
        if type(f[field]) not in (int, float) or not math.isfinite(f[field]) or f[field] < 0:
            raise ValueError('Invalid detector feature: ' + field)
    if type(f['reliable']) is not bool:
        raise ValueError('Expected boolean reference quality')
    if len(row['nodes']) != 2:
        raise ValueError('Expected the existing two-node detector')
    return dict(sample_index=row['sample_index'], sample_rate=2000000, window_samples=8000,
                method='reference_8000', threshold=threshold, features=copy.deepcopy(f))


def evidence_quality(report, evidence, threshold):
    """Check report/feature consistency, not physical truth or raw-IQ provenance."""
    try:
        e = json.loads(evidence)
        f = e['features']
        reliable = f['reliable']
        # Compare the signed feature with the exact configured threshold and score.
        if (e['method'] != 'reference_8000' or e['threshold'] != threshold or
                e['sample_rate'] != 2000000 or e['window_samples'] != 8000 or
                report['observed_at'] != (e['sample_index'] + 1) / 2000000 or
                report['ratio'] != f['score'] / threshold or report['quality_valid'] != reliable):
            return 'evidence_inconsistent'
        return quality(report, ratio_threshold=1.)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return 'evidence_inconsistent'


def process(rows, settings, provenance, case, keys=None):
    if case not in CASES or not rows:
        raise ValueError('Unknown case or empty input')
    keys = keys or [Ed25519PrivateKey.generate() for _ in range(2)]
    policy = dict(detector=settings, sample_rate=2000000, window_samples=8000,
                  fusion='two-node OR, both valid required', freshness_seconds=.012,
                  transport='simulated receiver delay, not wall-clock measurement',
                  input_hashes=provenance['files'], frozen_artifact_sha256=sha(ARTIFACT))
    config_hash = digest(policy)
    validator = Validator(config_hash, max_age=.012)
    for node in range(2):
        validator.authorize(str(node), 'ephemeral1', keys[node].public_key(), 'run1')
    events, dropped, baseline, observations = [], 0, {}, {}
    for sequence, row in enumerate(rows):
        timestamp = (row['sample_index'] + 1) / 2000000
        baseline[sequence] = [decide(row['nodes'][n], 'reference_8000', settings['thresholds'][n])[0] for n in range(2)]
        observations[sequence] = timestamp
        for node in range(2):
            threshold = settings['thresholds'][node]
            e = evidence_for(row, node, threshold)
            raw = canonical(e)
            f = e['features']
            report = dict(version=1, node_id=str(node), key_id='ephemeral1', session_id='run1',
                sequence=sequence, observed_at=timestamp, processing_ms=0., config_hash=config_hash,
                evidence_hash=hashlib.sha256(raw).hexdigest(), ratio=f['score']/threshold,
                vote=int(f['score'] > threshold), quality_valid=f['reliable'])
            envelope = sign_report(report, keys[node])
            # Predefined sparse injections; no truth or scenario consulted.
            injected = node == 0 and sequence % 10 == 5 and case != 'clean'
            if injected and case == 'drop':
                dropped += 1
                continue
            if injected and case == 'tamper':
                envelope['report']['vote'] = 1 - report['vote']
            received_at = timestamp + (.020 if injected and case == 'delay' else .0005)
            events.append(dict(envelope=envelope, evidence_hex=raw.hex(), received_at=received_at,
                               injected=injected, injection=case if injected else None))
            if injected and case == 'replay':
                # Retain original honest transmission; inject a duplicate afterward.
                events[-1]['injected'] = False
                events[-1]['injection'] = None
                duplicate = copy.deepcopy(events[-1])
                duplicate.update(received_at=received_at+.0001, injected=True, injection='replay')
                events.append(duplicate)
    events.sort(key=lambda e: e['received_at'])
    accepted, audit, statuses = {}, [], Counter()
    for event in events:
        env = event['envelope']; r = env['report']; raw = bytes.fromhex(event['evidence_hex'])
        status = validator.validate(env, raw, event['received_at'])
        q = evidence_quality(r, raw, settings['thresholds'][int(r['node_id'])]) if status == 'valid' else 'unavailable'
        statuses[status] += 1
        if status == 'valid' and q == 'usable':
            accepted.setdefault(r['sequence'], {})[r['node_id']] = r['vote']
        audit.append(dict(event, integrity=status, quality=q))
    counts = Counter(tp=0, fp=0, tn=0, fn=0, no_decision=0, changed_from_direct=0)
    decisions = []
    for sequence, row in enumerate(rows):
        votes = accepted.get(sequence, {})
        result = int(any(votes.values())) if len(votes) == 2 else None
        direct = None if any(v is None for v in baseline[sequence]) else int(any(baseline[sequence]))
        counts['changed_from_direct'] += int(result != direct)
        # Ground truth enters only after the signed-message pipeline has decided.
        truth = row.get('truth')
        if type(truth) is not int or truth not in (0, 1):
            raise ValueError('Evaluation requires binary truth labels')
        if result is None:
            counts['no_decision'] += 1
        else:
            counts[('tp' if truth else 'fp') if result else ('fn' if truth else 'tn')] += 1
        decisions.append(dict(sequence=sequence, sample_index=row['sample_index'], truth=truth,
                              direct_decision=direct, signed_decision=result))
    return (dict(case=case, frames=len(rows), reports_received=len(events), reports_dropped=dropped,
                integrity=dict(statuses), quality=dict(Counter(a['quality'] for a in audit)),
                injected_received=sum(e['injected'] for e in audit),
                injected_rejected=sum(e['injected'] and e['integrity'] != 'valid' for e in audit),
                metrics=dict(counts), policy=policy,
                public_keys={str(n):k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex() for n,k in enumerate(keys)},
                timing=dict(frame_intervals_seconds=sorted({round(observations[i]-observations[i-1],9) for i in range(1,len(rows))}),
                            ordinary_simulated_delay_seconds=.0005, injected_delay_seconds=.020,
                            processing_duration='Not measured; report field is zero and must not be interpreted as runtime latency')),
           audit, decisions)


def run(input_run, output_root):
    rows, provenance = load_run(input_run)
    settings = frozen_settings()
    folder = Path(output_root) / ('signed_detector_' + uuid.uuid4().hex)
    folder.mkdir(parents=True)
    write(folder/'plan.json', dict(status='running', cases=CASES, provenance=provenance))
    runs = []
    try:
        for case in CASES:
            result, audit, decisions = process(rows, settings, provenance, case)
            destination = folder/case; destination.mkdir()
            write(destination/'audit.json', audit)
            write(destination/'decisions.json', decisions)
            write(destination/'simulated_batches.json', audit_batches(audit))
            result['artifact_sha256'] = {n:sha(destination/n) for n in ('audit.json','decisions.json','simulated_batches.json')}
            runs.append(result)
        if runs[0]['metrics']['changed_from_direct']:
            raise RuntimeError('Clean signed path differs from direct detector')
        write(folder/'signed_detector_summary.json', dict(completed=True, provenance=provenance, runs=runs,
            limitations=['Detector features are imported, not cryptographically attested RF truth',
                         'Acquisition uses GNU Radio only when --input-run is omitted',
                         'Transport, timestamps and ledger receipts are simulated; no real network or blockchain',
                         'Two original virtual nodes; no additional independent sensors invented',
                         'Audit replay only; not a live GRC block or real-time benchmark',
                         'Trusted validator, enrollment, frozen policy and common sample clock',
                         'Out-of-order reports rejected; no reorder buffer; finite injected cases are not a security proof']))
        write(folder/'plan.json', dict(status='completed', cases=CASES, provenance=provenance))
    except BaseException as exc:
        write(folder/'plan.json', dict(status='incomplete', error=str(exc), provenance=provenance))
        raise
    print('COMPLETED. Upload signed_detector_summary.json from', folder, flush=True)
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-run', type=Path, help='Existing completed acquisition directory containing spectral_features.json')
    parser.add_argument('--output-root', type=Path, default=ROOT/'simulation/generated')
    parser.add_argument('--cycles', type=int, default=20)
    parser.add_argument('--seed', type=int, default=150001)
    args = parser.parse_args()
    if args.cycles < 1:
        parser.error('--cycles must be positive')
    if args.input_run is None:
        from run_noise_aware_experiments import acquire
        args.input_run, _, _ = acquire(args.output_root/'signed_acquisition', args.seed, args.cycles, 1., {})
    run(args.input_run, args.output_root)
