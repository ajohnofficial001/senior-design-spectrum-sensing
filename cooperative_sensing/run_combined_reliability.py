#!/usr/bin/env python3
"""Paired native detector acquisitions with independently seeded transport stress."""
import argparse
import json
import random
from pathlib import Path
import uuid
from run_signed_detector import ROOT, load_run, process, write, sha
from run_reference_confirmation import frozen_settings
from trust_protocol import audit_batches

SEEDS = (160001, 161001, 162001, 163001, 164001)
CONDITIONS = {'normal': {}, 'high_noise': {'noise_factor':1.2}}
PROFILES = ('clean', 'loss_20pct', 'burst_delay', 'node_outage', 'combined')


def schedule(count, seed, profile):
    if profile not in PROFILES or count < 1:
        raise ValueError('Invalid transport profile or frame count')
    rng = random.Random(seed + 1000000)
    delivery = {}
    for sequence in range(count):
        for node in range(2):
            loss = rng.random() < .2  # Draw even for clean to keep schedules paired.
            outage = node == 0 and count * 2 // 5 <= sequence < count * 3 // 5
            burst = node == 0 and 10 <= sequence % 40 < 20
            missing = (profile in ('loss_20pct','combined') and loss) or (
                       profile in ('node_outage','combined') and outage)
            delay = .020 if profile in ('burst_delay','combined') and burst else .0005
            delivery[sequence,node] = None if missing else delay
    return delivery


def metrics(decisions, audit):
    positive = sum(d['truth'] == 1 for d in decisions)
    negative = len(decisions)-positive
    counts = {k:0 for k in ('tp','fp','tn','fn','unavailable_positive','unavailable_negative')}
    for d in decisions:
        vote,truth = d['signed_decision'],d['truth']
        if vote is None:counts['unavailable_positive' if truth else 'unavailable_negative'] += 1
        else:counts[('tp' if truth else 'fp') if vote else ('fn' if truth else 'tn')] += 1
    available = len(decisions)-counts['unavailable_positive']-counts['unavailable_negative']
    def ratio(a,b):return a/b if b else None
    # Decision latency is last usable report arrival minus observation time, not CPU duration.
    arrivals = {}
    for event in audit:
        if event['integrity']=='valid' and event['quality']=='usable':
            r=event['envelope']['report']
            arrivals.setdefault(r['sequence'],[]).append(event['received_at']-r['observed_at'])
    latencies = sorted(max(arrivals[d['sequence']]) for d in decisions if d['signed_decision'] is not None)
    return dict(counts, positive_frames=positive, negative_frames=negative,
        availability=ratio(available,len(decisions)),
        detection_given_decision=ratio(counts['tp'],counts['tp']+counts['fn']),
        false_alarm_given_decision=ratio(counts['fp'],counts['fp']+counts['tn']),
        detected_fraction_all_positive=ratio(counts['tp'],positive),
        false_alarm_fraction_all_negative=ratio(counts['fp'],negative),
        unavailable_positive_fraction=ratio(counts['unavailable_positive'],positive),
        unavailable_negative_fraction=ratio(counts['unavailable_negative'],negative),
        simulated_decision_delay_seconds=dict(count=len(latencies),mean=sum(latencies)/len(latencies) if latencies else None,
            maximum=max(latencies) if latencies else None),
        note='Delays conditional on available decisions; rejected/missing reports are represented by availability')


def run(output_root, cycles=50, acquire_fn=None):
    if type(cycles) is not int or cycles < 1:raise ValueError('cycles must be positive integer')
    folder=Path(output_root)/('combined_reliability_'+uuid.uuid4().hex)
    folder.mkdir(parents=True)
    plan=dict(status='running',cycles=cycles,seeds=SEEDS,conditions=CONDITIONS,profiles=PROFILES,
        native_acquisition=acquire_fn is None,
        noise_definition='noise_factor 1.2 scales I/Q standard deviation, not variance or dB',
        transport_seed_offset=1000000,freshness_seconds=.012,
        policy='Frozen original 8000-sample detector, two-node OR, require both usable reports',
        injection_policy='Independent 20% loss per report; node 0 20 ms delay on frames 10..19 modulo 40; node 0 absent middle 20% of frames',
        limitations=['Software-only sensing; no RF validation','Simulated transport/common sample clock and local batch receipts',
                     'Strict increasing sequence policy; legitimate delayed reports can be rejected',
                     'No timing calibration or deployed blockchain; frame observations are not independent trials'])
    write(folder/'combined_plan.json',plan)
    results=[];settings=frozen_settings()
    try:
        if acquire_fn is None:
            from run_noise_aware_experiments import acquire
            acquire_fn=acquire
        for condition,channel in CONDITIONS.items():
            for seed in SEEDS:
                print('Acquiring',condition,seed,flush=True)
                source,_,_=acquire_fn(folder/'acquisitions'/condition,seed,cycles,1.,channel)
                rows,provenance=load_run(source)
                for profile in PROFILES:
                    delivery=schedule(len(rows),seed,profile)
                    result,audit,decisions=process(rows,settings,provenance,'clean',
                        delivery=delivery,delivery_policy=dict(profile=profile,transport_seed=seed+1000000))
                    if profile=='clean' and result['metrics']['changed_from_direct']:
                        raise RuntimeError('Clean path differs from direct detector')
                    path=folder/condition/str(seed)/profile;path.mkdir(parents=True)
                    write(path/'audit.json',audit);write(path/'decisions.json',decisions)
                    write(path/'simulated_batches.json',audit_batches(audit))
                    result.update(condition=condition,seed=seed,transport_profile=profile,
                        provenance=provenance,reliability=metrics(decisions,audit),
                        artifacts={n:sha(path/n) for n in ('audit.json','decisions.json','simulated_batches.json')})
                    results.append(result)
                    write(folder/'combined_progress.json',dict(completed_runs=len(results),expected_runs=50,runs=results))
        plan['status']='completed'
        write(folder/'combined_plan.json',plan)
        write(folder/'combined_summary.json',dict(completed=True,plan=plan,runs=results))
    except BaseException as exc:
        plan.update(status='incomplete',error=type(exc).__name__+': '+str(exc))
        write(folder/'combined_plan.json',plan)
        raise
    print('COMPLETED. Upload combined_summary.json from',folder,flush=True)
    return folder


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cycles',type=int,default=50)
    parser.add_argument('--output-root',type=Path,default=ROOT/'simulation/generated')
    args=parser.parse_args()
    run(args.output_root,args.cycles)
