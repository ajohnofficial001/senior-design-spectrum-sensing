"""Integration checks using numerical detector frames, without claiming GNU Radio execution."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'simulation'), str(ROOT/'cooperative_sensing')]
from noise_aware_detector import FeatureFrames
from run_reference_confirmation import frozen_settings
from run_signed_detector import process, run, load_run, evidence_quality
from trust_protocol import canonical
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from trust_protocol import audit_batches


def fixture():
    rng = np.random.default_rng(150001)
    n = 160000
    time = np.arange(n)/2000000
    truth = (np.arange(n)//20000 % 4 % 2).astype(np.float32)
    frames = FeatureFrames()
    sources = []
    for gain in (1., .65):
        x = (.001*(rng.standard_normal(n)+1j*rng.standard_normal(n)) +
             .0002*gain*truth*np.exp(2j*np.pi*400000*time)).astype(np.complex64)
        sources.append(x)
    frames.push(sources+[truth])
    return frames.records


class SignedDetectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = fixture()
        cls.settings = frozen_settings()
        cls.provenance = {'files': {'spectral_features.json':'fixture-only'}}

    def test_clean_preserves_frozen_detector_and_sample_times(self):
        r, audit, decisions = process(self.rows, self.settings, self.provenance, 'clean')
        self.assertEqual(r['metrics']['changed_from_direct'], 0)
        self.assertEqual(r['integrity'], {'valid':32})
        self.assertEqual(r['timing']['frame_intervals_seconds'], [.004,.006])
        self.assertEqual(audit[0]['envelope']['report']['observed_at'], .004)
        for e in audit:
            evidence = bytes.fromhex(e['evidence_hex'])
            self.assertEqual(hashlib.sha256(evidence).hexdigest(), e['envelope']['report']['evidence_hash'])
            self.assertNotIn('truth', json.loads(evidence))
            self.assertNotIn('scenario', json.loads(evidence))

    def test_attacks_and_loss_abstain_without_fabricating_decisions(self):
        for case in ('tamper','replay','delay','drop'):
            r, _, _ = process(self.rows, self.settings, self.provenance, case)
            self.assertEqual(r['injected_received'], r['injected_rejected'])
            self.assertEqual(r['metrics']['no_decision'], 0 if case=='replay' else 2)
            self.assertEqual(r['reports_dropped'], 2 if case=='drop' else 0)

    def test_quality_abstention_survives_signing(self):
        rows = copy.deepcopy(self.rows)
        rows[0]['nodes'][0]['long']['reliable'] = False
        rows[0]['nodes'][0]['reliable']['reference_8000'] = False
        r, audit, _ = process(rows, self.settings, self.provenance, 'clean')
        self.assertEqual(r['metrics']['no_decision'], 1)
        self.assertEqual(r['metrics']['changed_from_direct'], 0)
        self.assertEqual(audit[0]['quality'], 'uncertain_reference')

    def test_truth_labels_cannot_change_reports_or_decisions(self):
        rows = copy.deepcopy(self.rows)
        for row in rows:
            row['truth'] = 1-row['truth'];row['scenario'] = 99
        _, original, decisions = process(self.rows,self.settings,self.provenance,'clean')
        _, altered, new_decisions = process(rows,self.settings,self.provenance,'clean')
        self.assertEqual([x['envelope']['report'] for x in original],[x['envelope']['report'] for x in altered])
        self.assertEqual([x['signed_decision'] for x in decisions],[x['signed_decision'] for x in new_decisions])

    def test_evidence_threshold_or_score_mismatch(self):
        _, audit, _ = process(self.rows,self.settings,self.provenance,'clean')
        event = audit[0]; r=event['envelope']['report'];raw=bytes.fromhex(event['evidence_hex'])
        e=json.loads(raw);e['threshold']=123.
        self.assertEqual(evidence_quality(r,canonical(e),self.settings['thresholds'][0]),'evidence_inconsistent')

    def test_complete_run_outputs_and_reject_incomplete_frames(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'source';source.mkdir()
            (source/'config.json').write_text(json.dumps({'expected_samples':160000}))
            (source/'summary.json').write_text(json.dumps({'completed':True}))
            (source/'spectral_features.json').write_text(json.dumps(self.rows))
            result=run(source,root/'outputs')
            s=json.loads((result/'signed_detector_summary.json').read_text())
            self.assertTrue(s['completed']);self.assertEqual(len(s['runs']),5)
            self.assertEqual(s['provenance']['source_claim'],'Unattested imported feature fixture')
            for case in s['runs']:
                folder=result/case['case']
                events=json.loads((folder/'audit.json').read_text())
                self.assertEqual(audit_batches(events),json.loads((folder/'simulated_batches.json').read_text()))
                for event in events:
                    if event['integrity'] != 'valid': continue
                    env=event['envelope'];r=env['report']
                    key=Ed25519PublicKey.from_public_bytes(bytes.fromhex(case['public_keys'][r['node_id']]))
                    key.verify(bytes.fromhex(env['signature']),canonical(r))
                    self.assertEqual(hashlib.sha256(bytes.fromhex(event['evidence_hex'])).hexdigest(),r['evidence_hash'])
            (source/'spectral_features.json').write_text(json.dumps(self.rows[:-1]))
            with self.assertRaises(ValueError):load_run(source)
            (source/'summary.json').write_text(json.dumps({'completed':False}))
            with self.assertRaises(ValueError):load_run(source)


if __name__=='__main__': unittest.main()
