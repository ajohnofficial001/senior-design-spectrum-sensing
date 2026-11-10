"""Protocol and adversarial-study regression tests; no RF claims."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cooperative_sensing'))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from trust_protocol import Validator, PhiMonitor, canonical, sign_report, quality, fuse, audit_batches, digest
from run_trust_experiments import experiment


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.validator = Validator('config')
        self.validator.authorize('0', 'key1', self.key.public_key(), 's1')
        self.evidence = b'evidence'
        self.report = dict(version=1, node_id='0', key_id='key1', session_id='s1', sequence=1,
                           observed_at=1., processing_ms=10., config_hash='config',
                           evidence_hash=hashlib.sha256(self.evidence).hexdigest(), ratio=2., vote=1,
                           quality_valid=True)

    def validate(self, report=None, evidence=None):
        return self.validator.validate(sign_report(report or self.report, self.key),
                                       self.evidence if evidence is None else evidence, 1.1)

    def test_signature_and_replay(self):
        self.assertEqual(self.validate(), 'valid')
        self.assertEqual(self.validate(), 'replay_or_out_of_order')

    def test_tamper_and_wrong_signer(self):
        envelope = sign_report(self.report.copy(), self.key)
        envelope['report']['ratio'] = 1.
        self.assertEqual(self.validator.validate(envelope, self.evidence, 1.1), 'invalid_signature')
        forged = sign_report(self.report, Ed25519PrivateKey.generate())
        self.assertEqual(self.validator.validate(forged, self.evidence, 1.1), 'invalid_signature')

    def test_evidence_session_config_schema_and_age(self):
        for field, value, status in [('session_id', 'other', 'unauthorized_session'),
                                    ('config_hash', 'other', 'unknown_configuration'),
                                    ('sequence', True, 'malformed_report'),
                                    ('observed_at', 10., 'stale_or_clock_mismatch')]:
            self.assertEqual(self.validate(dict(self.report, **{field: value})), status)
        self.assertEqual(self.validate(evidence=b'changed'), 'evidence_mismatch')
        self.assertEqual(self.validate(), 'valid')  # Bad inputs never advance sequence.

    def test_rotation_revokes_old_key_without_resetting_sequence(self):
        self.assertEqual(self.validate(), 'valid')
        replacement = Ed25519PrivateKey.generate()
        self.validator.authorize('0', 'key2', replacement.public_key(), 's1')
        self.assertEqual(self.validate(), 'revoked_or_unknown_key')
        r = dict(self.report, key_id='key2')
        self.assertEqual(self.validator.validate(sign_report(r, replacement), self.evidence, 1.1),
                         'replay_or_out_of_order')

    def test_quality_is_not_truth(self):
        self.assertEqual(quality(self.report), 'usable')
        self.assertEqual(quality(dict(self.report, vote=0)), 'internally_inconsistent')
        self.assertEqual(quality(dict(self.report, quality_valid=False)), 'uncertain_reference')

    def test_unique_quorum(self):
        with self.assertRaises(ValueError):
            fuse([self.report] * 3)
        self.assertEqual(fuse([self.report])[0], None)

    def test_phi_increases_and_batches_bind_content(self):
        monitor = PhiMonitor([1.] * 30)
        self.assertLess(monitor.phi(1.), monitor.phi(2.))
        self.assertFalse(monitor.suspicious(1.))
        self.assertTrue(monitor.suspicious(2.))
        events = [dict(received_at=1., status='valid'), dict(received_at=11., status='valid')]
        batches = audit_batches(events)
        self.assertEqual(batches[1]['previous_hash'], batches[0]['hash'])
        record = dict(batches[0]); record.pop('hash')
        self.assertEqual(digest(record), batches[0]['hash'])
        changed = copy.deepcopy(events); changed[0]['status'] = 'invalid'
        self.assertNotEqual(audit_batches(changed)[0]['commitment'], batches[0]['commitment'])

    def test_attack_and_honest_controls(self):
        monitor = PhiMonitor([1.] * 30)
        for case in ('tampered_payload', 'forged_signature', 'replay', 'revoked_key'):
            r, _, _ = experiment(case, 120001, monitor)
            self.assertGreater(r['integrity']['attack_reports'], 0)
            self.assertEqual(r['integrity']['attack_reports'], r['integrity']['rejected_attack_reports'])
        r, _, _ = experiment('authorized_key_rotation', 120001, monitor)
        self.assertEqual(r['integrity']['rejected_honest_reports'], 0)

    def test_collusion_exposes_limit(self):
        monitor = PhiMonitor([1.] * 30)
        single, _, _ = experiment('signed_fabrication', 120001, monitor)
        majority, _, _ = experiment('majority_collusion', 120001, monitor)
        self.assertEqual(single['integrity']['rejected_attack_reports'], 0)
        self.assertEqual(single['fusion']['errors'], 0)
        self.assertEqual(majority['fusion']['errors'], 20)
        self.assertEqual(majority['fusion']['disagreements_on_honest'], 40)

    def test_ledger_delay_is_separate_from_node_health(self):
        monitor = PhiMonitor([1.] * 30)
        control, _, _ = experiment('control', 120001, monitor)
        delay, _, _ = experiment('ledger_delay', 120001, monitor)
        self.assertEqual(control['health'], delay['health'])
        self.assertNotEqual(control['simulated_ledger_delay'], delay['simulated_ledger_delay'])


if __name__ == '__main__':
    unittest.main()
