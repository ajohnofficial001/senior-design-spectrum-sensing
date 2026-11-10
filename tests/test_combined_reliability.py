import json
from pathlib import Path
import tempfile
import unittest
from test_signed_detector import fixture
from run_signed_detector import process
from run_reference_confirmation import frozen_settings
from run_combined_reliability import schedule, metrics, run, PROFILES


class CombinedReliabilityTests(unittest.TestCase):
    def test_schedule_is_paired_and_seeded(self):
        a=schedule(400,160001,'loss_20pct')
        self.assertEqual(a,schedule(400,160001,'loss_20pct'))
        self.assertNotEqual(a,schedule(400,161001,'loss_20pct'))
        combined=schedule(400,160001,'combined')
        for key,delay in a.items():
            if delay is None:self.assertIsNone(combined[key])
        self.assertEqual(set(schedule(400,1,'clean').values()),{.0005})
        for s in range(160,240):self.assertIsNone(combined[s,0])

    def test_abstentions_cannot_inflate_unconditional_detection(self):
        decisions=[dict(sequence=0,truth=1,signed_decision=1),dict(sequence=1,truth=1,signed_decision=None),
                   dict(sequence=2,truth=0,signed_decision=0),dict(sequence=3,truth=0,signed_decision=None)]
        audit=[dict(integrity='valid',quality='usable',received_at=.0005,
                    envelope={'report':dict(sequence=0,observed_at=0.)}),
               dict(integrity='valid',quality='usable',received_at=.001,
                    envelope={'report':dict(sequence=2,observed_at=0.)})]
        m=metrics(decisions,audit)
        self.assertEqual(m['detection_given_decision'],1.)
        self.assertEqual(m['detected_fraction_all_positive'],.5)
        self.assertEqual(m['availability'],.5)
        self.assertEqual(m['unavailable_positive_fraction'],.5)
        self.assertEqual(m['simulated_decision_delay_seconds']['maximum'],.001)
        none=metrics([dict(sequence=0,truth=1,signed_decision=None)],[])
        self.assertIsNone(none['detection_given_decision'])
        self.assertIsNone(none['simulated_decision_delay_seconds']['mean'])

    def test_transport_reuses_detector_and_validates_schedule(self):
        rows=fixture();p={'files':{'features':'fixture'}};settings=frozen_settings()
        r,_,_=process(rows,settings,p,'clean',delivery=schedule(len(rows),1,'clean'))
        self.assertEqual(r['metrics']['changed_from_direct'],0)
        with self.assertRaises(ValueError):process(rows,settings,p,'clean',delivery={})
        d=schedule(len(rows),1,'clean');d[0,0]=float('nan')
        with self.assertRaises(ValueError):process(rows,settings,p,'clean',delivery=d)

    def test_full_runner_pairing_and_failure_record(self):
        rows=fixture()
        def acquire(root,seed,cycles,factor,channel):
            folder=Path(root)/str(seed);folder.mkdir(parents=True)
            for name,value in [('config.json',{'expected_samples':160000}),('summary.json',{'completed':True}),
                               ('spectral_features.json',rows)]:
                (folder/name).write_text(json.dumps(value))
            return folder,rows,{'completed':True}
        with tempfile.TemporaryDirectory() as temp:
            out=run(temp,cycles=2,acquire_fn=acquire)
            s=json.loads((out/'combined_summary.json').read_text())
            self.assertEqual(len(s['runs']),50);self.assertTrue(s['completed'])
            self.assertFalse(s['plan']['native_acquisition'])
            for condition in ['normal','high_noise']:
                group=[r for r in s['runs'] if r['condition']==condition and r['seed']==160001]
                self.assertEqual(len({r['provenance']['files']['spectral_features.json'] for r in group}),1)
                self.assertEqual({r['transport_profile'] for r in group},set(PROFILES))
            def fail(*args):raise RuntimeError('intentional acquisition failure')
            with self.assertRaises(RuntimeError):run(temp,acquire_fn=fail)
            plans=[json.loads(p.read_text()) for p in Path(temp).glob('*/combined_plan.json')]
            self.assertIn('incomplete',[p['status'] for p in plans])


if __name__=='__main__':unittest.main()
