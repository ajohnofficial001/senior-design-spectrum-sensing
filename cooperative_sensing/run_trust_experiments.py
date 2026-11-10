#!/usr/bin/env python3
"""Executable report-protocol study with real signatures and simulated time/data."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import uuid
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from trust_protocol import (Validator, PhiMonitor, canonical, digest, sign_report,
                            quality, fuse, audit_batches)

SEEDS = (120001, 121001, 122001, 123001, 124001)
CASES = ('control', 'honest_jitter', 'honest_cpu_delay', 'node_outage', 'tampered_payload',
         'replay', 'forged_signature', 'signed_fabrication', 'majority_collusion',
         'ledger_delay', 'authorized_key_rotation', 'revoked_key')


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def experiment(case, seed, monitor):
    rng = random.Random(seed)
    keys = [Ed25519PrivateKey.generate() for _ in range(5)]
    validator = Validator(digest({'schema': 1, 'ratio_threshold': 1.3}))
    for node, key in enumerate(keys):
        validator.authorize(str(node), 'key1', key.public_key(), 'session1')
    events = []
    for sequence in range(200):
        truth = int(sequence % 20 >= 10)
        for node in range(5):
            if case == 'node_outage' and node == 0 and 140 <= sequence < 160:
                continue
            ratio = (2. if truth else 1.) + rng.uniform(-.04, .04)
            processing = .05
            if case == 'honest_cpu_delay' and node == 0 and 140 <= sequence < 160:
                processing = .8
            jitter = abs(rng.gauss(0., .04 if case != 'honest_jitter' else .35))
            received = sequence + processing + jitter
            injected = False
            if case in ('signed_fabrication', 'majority_collusion') and 140 <= sequence < 160:
                if node < (1 if case == 'signed_fabrication' else 3):
                    ratio = 1. if truth else 2.
                    injected = True
            evidence = canonical(dict(ratio=ratio, quality_valid=True))
            report = dict(version=1, node_id=str(node), key_id='key1', session_id='session1',
                sequence=sequence, observed_at=float(sequence), processing_ms=processing * 1000,
                config_hash=validator.config_hash, evidence_hash=hashlib.sha256(evidence).hexdigest(),
                ratio=ratio, vote=int(ratio > 1.3), quality_valid=True)
            envelope = sign_report(report, keys[node])
            if case == 'tampered_payload' and node == 0 and 140 <= sequence < 160:
                envelope['report']['ratio'] += 10
                injected = True
            if case == 'forged_signature' and node == 0 and 140 <= sequence < 160:
                envelope = sign_report(report, keys[1])
                injected = True
            events.append(dict(envelope=envelope, evidence=evidence, received_at=received,
                               truth=truth, injected=injected))
            if case == 'replay' and node == 0 and 140 <= sequence < 160:
                events.append(dict(envelope=copy.deepcopy(envelope), evidence=evidence,
                    received_at=received+.001, truth=truth, injected=True))
    # Rotation is an explicit trusted control-plane event at receiver time 150.
    replacement = Ed25519PrivateKey.generate()
    if case == 'authorized_key_rotation':
        for event in events:
            r = event['envelope']['report']
            if r['node_id'] == '0' and r['sequence'] >= 150:
                r['key_id'] = 'key2'
                event['envelope'] = sign_report(r, replacement)
    if case == 'revoked_key':
        for event in events:
            r = event['envelope']['report']
            event['injected'] = r['node_id'] == '0' and r['sequence'] >= 150
    events.sort(key=lambda e: e['received_at'])
    accepted, audit, last = {}, [], {str(n): 100. for n in range(5)}
    integrity = dict(attack_reports=0, rejected_attack_reports=0,
                     honest_reports=0, rejected_honest_reports=0)
    health = {name: dict(false_warning_ticks=0, healthy_monitor_ticks=0, outage_warning_ticks=0,
                        outage_monitor_ticks=0, first_outage_warning_delay=None)
              for name in ('phi_style', 'fixed_3s')}
    rotated, event_index = False, 0
    for tick in range(400, 841):
        now = tick / 4.
        if case in ('authorized_key_rotation', 'revoked_key') and now >= 150 and not rotated:
            validator.authorize('0', 'key2', replacement.public_key(), 'session1')
            rotated = True
        while event_index < len(events) and events[event_index]['received_at'] <= now:
            e = events[event_index]
            event_index += 1
            # Warm-up traffic <100 is not scored; validate it separately below through same path.
            report = e['envelope']['report']
            status = validator.validate(e['envelope'], e['evidence'], e['received_at'])
            measurement = quality(report) if status == 'valid' else 'unavailable'
            if status == 'valid':
                last[report['node_id']] = e['received_at']
                if report['sequence'] not in accepted:
                    accepted[report['sequence']] = []
                if e['received_at'] <= report['observed_at'] + 2:
                    accepted[report['sequence']].append(report)
            if report['sequence'] >= 100:
                suffix = 'attack_reports' if e['injected'] else 'honest_reports'
                integrity[suffix] += 1
                if status != 'valid':
                    integrity['rejected_' + suffix] += 1
                audit.append(dict(received_at=e['received_at'], report_hash=digest(report),
                    envelope=copy.deepcopy(e['envelope']), evidence_hex=e['evidence'].hex(),
                    node_id=report['node_id'], sequence=report['sequence'], integrity=status,
                    quality=measurement, processing_warning=bool(status == 'valid' and report['processing_ms'] > 500)))
        if now < 101 or now > 199:
            continue
        for node in range(5):
            elapsed = now - last[str(node)]
            outage = case == 'node_outage' and node == 0 and 140 <= now < 160
            for method, alarm in [('phi_style', monitor.suspicious(elapsed)), ('fixed_3s', elapsed > 3.)]:
                h = health[method]
                prefix = 'outage' if outage else 'healthy'
                h[prefix + '_monitor_ticks'] += 1
                h['outage_warning_ticks' if outage else 'false_warning_ticks'] += int(alarm)
                if outage and alarm and h['first_outage_warning_delay'] is None:
                    h['first_outage_warning_delay'] = now - 140
    fusion = dict(evaluated_epochs=100, errors=0, no_decision=0,
                  disagreements_on_injected=0, disagreements_on_honest=0)
    for seq in range(100, 200):
        reports = accepted.get(seq, [])
        decision, disagree = fuse(reports)
        truth = int(seq % 20 >= 10)
        if decision is None:
            fusion['no_decision'] += 1
        else:
            fusion['errors'] += int(decision != truth)
        for node in disagree:
            fabricated = case in ('signed_fabrication', 'majority_collusion') and 140 <= seq < 160 and int(node) < (1 if case == 'signed_fabrication' else 3)
            fusion['disagreements_on_injected' if fabricated else 'disagreements_on_honest'] += 1
    batches = audit_batches(audit, confirmation_delay=15. if case == 'ledger_delay' else 1.)
    return dict(case=case, seed=seed, integrity=integrity, health=health, fusion=fusion,
                public_keys={**{str(n) + ':key1': k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
                                for n, k in enumerate(keys)},
                             '0:key2': replacement.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()},
                rotation_at=150 if case in ('authorized_key_rotation', 'revoked_key') else None,
                processing_warnings=sum(e['processing_warning'] for e in audit),
                simulated_ledger_delay=15. if case == 'ledger_delay' else 1.), audit, batches


def run(root):
    root = Path(root) / ('trust_' + uuid.uuid4().hex)
    root.mkdir(parents=True)
    intervals = [max(.1, random.Random(seed).gauss(1., .08)) for seed in range(110001, 110301)]
    monitor = PhiMonitor(intervals)
    plan = dict(status='running', cases=CASES, test_seeds=SEEDS,
        training_seed_range=[110001,110300], monitor_mean=monitor.mean, monitor_std=monitor.std,
        phi_threshold=3., acceptable_pause=.2, fixed_timeout=3.,
        sampling_tick_seconds=.25, node_count=5, expected_interval=1.,
        time_model='Single simulated receiver clock; no wall-clock prediction',
        ledger_mode='LOCAL_SIMULATOR_NOT_BLOCKCHAIN')
    dump(root / 'trust_plan.json', plan)
    results = []
    try:
        for case in CASES:
            for seed in SEEDS:
                print(case, seed, flush=True)
                result, audit, batches = experiment(case, seed, monitor)
                folder = root / case / str(seed)
                folder.mkdir(parents=True)
                dump(folder / 'audit.json', audit)
                dump(folder / 'simulated_batches.json', batches)
                result['audit_sha256'] = hashlib.sha256((folder / 'audit.json').read_bytes()).hexdigest()
                results.append(result)
                dump(root / 'trust_progress.json', results)
        summary = dict(completed=True, runs=results, plan=plan,
            limitations=['Synthetic protocol traces, not GNU Radio-derived reports or measured network traffic',
                         'Real Ed25519 signatures; ephemeral private keys remain in memory only',
                         'Authorized registry/session/configuration and common simulated time are trusted',
                         'Signed fabrication can pass integrity checks; evidence hashes do not prove RF truth',
                         'Majority collusion can defeat fusion and flag honest minorities',
                         'Phi-style model uses frozen independently calibrated timing, not adaptive Pekko code',
                         'Health warnings indicate unusual availability, not malicious intent or future prediction',
                         'Receipts and batching are simulated; no smart contract or blockchain deployment'])
        summary['plan'] = dict(plan, status='completed')
        dump(root / 'trust_summary.json', summary)
        plan['status'] = 'completed'
        dump(root / 'trust_plan.json', plan)
        print('COMPLETED. Upload trust_summary.json from', root, flush=True)
    except BaseException as exc:
        plan.update(status='incomplete', error=type(exc).__name__ + ': ' + str(exc))
        dump(root / 'trust_plan.json', plan)
        raise
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', default='simulation/generated')
    args = parser.parse_args()
    run(args.output_root)
