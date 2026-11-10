"""Research prototype: authenticated reports and separate health/quality checks."""
import hashlib
import json
import math
import statistics
from cryptography.exceptions import InvalidSignature


def canonical(value):
    # Restricted Python JSON encoding, not a general RFC 8785 implementation.
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sign_report(report, private_key):
    return dict(report=report, signature=private_key.sign(canonical(report)).hex())


class Validator:
    def __init__(self, config_hash, max_age=3.):
        self.config_hash, self.max_age = config_hash, max_age
        self.registry = {}
        self.last_sequence = {}

    def authorize(self, node, key_id, public_key, session):
        # Trusted control-plane action. Replaces/revokes previous key, not sequence history.
        self.registry[node] = (key_id, public_key, session)

    def validate(self, envelope, evidence, received_at):
        try:
            report = envelope['report']
            identity = self.registry.get(report['node_id'])
            if identity is None:
                return 'unauthorized_node'
            key_id, public_key, session = identity
            if report['key_id'] != key_id:
                return 'revoked_or_unknown_key'
            public_key.verify(bytes.fromhex(envelope['signature']), canonical(report))
        except InvalidSignature:
            return 'invalid_signature'
        except (KeyError, TypeError, ValueError, OverflowError):
            return 'malformed_report'
        try:
            required = {'version', 'node_id', 'key_id', 'session_id', 'sequence', 'observed_at',
                        'processing_ms', 'config_hash', 'evidence_hash', 'ratio', 'vote', 'quality_valid'}
            if set(report) != required or report['version'] != 1:
                return 'malformed_report'
            if (type(report['sequence']) is not int or report['sequence'] < 0 or
                    type(report['vote']) is not int or report['vote'] not in (0, 1) or
                    type(report['quality_valid']) is not bool):
                return 'malformed_report'
            for field in ('observed_at', 'processing_ms', 'ratio'):
                if type(report[field]) not in (int, float) or not math.isfinite(report[field]) or report[field] < 0:
                    return 'malformed_report'
            if report['session_id'] != session:
                return 'unauthorized_session'
            if report['config_hash'] != self.config_hash:
                return 'unknown_configuration'
            if report['evidence_hash'] != hashlib.sha256(evidence).hexdigest():
                return 'evidence_mismatch'
            if report['sequence'] <= self.last_sequence.get((report['node_id'], session), -1):
                return 'replay_or_out_of_order'
            age = received_at - report['observed_at']
            if age < -.05 or age > self.max_age:
                return 'stale_or_clock_mismatch'
            self.last_sequence[(report['node_id'], session)] = report['sequence']
            return 'valid'
        except (KeyError, TypeError, ValueError, OverflowError):
            return 'malformed_report'


def quality(report, ratio_threshold=1.3):
    """No ground truth or peer majority supplied here."""
    if not report['quality_valid']:
        return 'uncertain_reference'
    if report['vote'] != int(report['ratio'] > ratio_threshold):
        return 'internally_inconsistent'
    return 'usable'


class PhiMonitor:
    """Normal-model phi-style monitor with independently calibrated, frozen history.

    This intentionally does not claim to reproduce Pekko's adaptive implementation.
    """
    def __init__(self, intervals, threshold=3., pause=.2, std_floor=.1):
        if len(intervals) < 20 or any(x <= 0 or not math.isfinite(x) for x in intervals):
            raise ValueError('Need at least 20 positive finite calibration intervals')
        self.mean = statistics.mean(intervals)
        self.std = max(statistics.stdev(intervals), std_floor)
        self.threshold, self.pause = threshold, pause

    def phi(self, elapsed):
        z = (max(0., elapsed - self.pause) - self.mean) / self.std
        survival = max(.5 * math.erfc(z / math.sqrt(2)), 1e-15)
        return -math.log10(survival)

    def suspicious(self, elapsed):
        return self.phi(elapsed) >= self.threshold


def fuse(reports):
    """Five-node prototype: quorum >=3, strict majority, ties abstain.

    Disagreement is diagnostic only. No automatic reputation punishment.
    """
    usable = [r for r in reports if quality(r) == 'usable']
    if len({r['node_id'] for r in usable}) != len(usable):
        raise ValueError('Duplicate node identity in fusion epoch')
    if len(usable) < 3:
        return None, []
    positives = sum(r['vote'] for r in usable)
    if 2 * positives == len(usable):
        return None, []
    decision = int(2 * positives > len(usable))
    return decision, [r['node_id'] for r in usable if r['vote'] != decision]


def audit_batches(events, seconds=10., confirmation_delay=1.):
    """Local batch-commitment/receipt simulator. NOT blockchain transactions."""
    buckets = {}
    for event in events:
        bucket = int(event['received_at'] // seconds)
        buckets.setdefault(bucket, []).append(event)
    records, previous = [], '0' * 64
    for index, values in sorted(buckets.items()):
        close = (index + 1) * seconds
        record = dict(batch=index, record_count=len(values), commitment=digest(values),
                      previous_hash=previous, scheduled_close=close,
                      simulated_confirmation_at=close + confirmation_delay,
                      ledger_mode='LOCAL_SIMULATOR_NOT_BLOCKCHAIN')
        previous = digest(record)
        records.append(dict(record, hash=previous))
    return records
