# SPDX-License-Identifier: GPL-3.0
"""Source code also embedded in full_simulation.grc. Ledger is a local mock."""
import csv
import hashlib
import json
from pathlib import Path
import uuid
import numpy as np
from gnuradio import gr


class blk(gr.sync_block):
    """Window-end decisions, OR/AND fusion, metrics and hash-linked local ledger."""

    def __init__(self, sample_rate=2000000, segment_samples=20000,
                 window_samples=1000, guard_samples=2000,
                 threshold1=0.05, threshold2=0.05, fusion_rule='OR',
                 output_root='simulation/generated', config=None):
        gr.sync_block.__init__(self, name='Fusion, metrics and MOCK ledger',
                               in_sig=[np.float32] * 5, out_sig=None)
        if window_samples < 1 or not window_samples <= guard_samples < segment_samples:
            raise ValueError('Require window <= guard < segment_samples')
        if sample_rate <= 0 or min(threshold1, threshold2) < 0:
            raise ValueError('Invalid sample rate or threshold')
        if fusion_rule not in ('OR', 'AND'):
            raise ValueError('fusion_rule must be OR or AND')
        self.fs, self.segment = float(sample_rate), int(segment_samples)
        self.window, self.guard = int(window_samples), int(guard_samples)
        self.thresholds, self.rule = (threshold1, threshold2), fusion_rule
        self.root, self.config = output_root, dict(config or {})
        self.position = 0
        self.counts = {name: dict(tp=0, fp=0, tn=0, fn=0)
                       for name in ('rx1', 'rx2', 'OR', 'AND')}
        self.scenarios = {str(i): {name: dict(tp=0, fp=0, tn=0, fn=0)
                                  for name in self.counts} for i in range(4)}
        self.previous_hash = '0' * 64
        self.records = 0
        self.csv_file = self.ledger_file = None
        self.directory = None

    def start(self):
        # GRC introspects constructors: create files only when execution starts.
        self.directory = Path(self.root) / ('full_sim_' + uuid.uuid4().hex)
        self.directory.mkdir(parents=True, exist_ok=False)
        config = dict(self.config, sample_rate=self.fs, segment_samples=self.segment,
                      window_samples=self.window, guard_samples=self.guard,
                      thresholds=self.thresholds, fusion_rule=self.rule,
                      ledger_mode='LOCAL_MOCK_NOT_BLOCKCHAIN')
        encoded = json.dumps(config, sort_keys=True, separators=(',', ':'))
        self.config_hash = hashlib.sha256(encoded.encode()).hexdigest()
        (self.directory / 'config.json').write_text(encoded + '\n', encoding='utf-8')
        self.csv_file = (self.directory / 'observations.csv').open('w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.csv_file)
        self.writer.writerow(['sample_index', 'sample_time_s', 'scenario', 'truth',
                              'rx1_filtered', 'rx2_filtered', 'rx1_full', 'rx2_full',
                              'rx1_decision', 'rx2_decision', 'OR', 'AND', 'selected'])
        self.ledger_file = (self.directory / 'mock_ledger.jsonl').open('w', encoding='utf-8')
        print('Simulation outputs:', self.directory)
        return True

    @staticmethod
    def update(counts, decision, truth):
        key = ('tp' if truth else 'fp') if decision else ('fn' if truth else 'tn')
        counts[key] += 1

    def work(self, input_items, output_items):
        n = len(input_items[0])
        # Input order: filtered RX1/RX2, unfiltered RX1/RX2, ideal truth.
        for local in range((-self.position + self.window - 1) % self.window, n, self.window):
            index = self.position + local
            if index % self.segment < self.guard:
                continue  # Exclude FIR/window transients after every scenario change.
            powers = [float(stream[local]) for stream in input_items[:4]]
            if not np.all(np.isfinite(powers)):
                raise ValueError('Nonfinite power observation')
            truth = int(input_items[4][local] >= 0.5)
            decisions = [int(powers[i] > self.thresholds[i]) for i in range(2)]
            either, both = int(any(decisions)), int(all(decisions))
            scenario = (index // self.segment) % 4
            for name, decision in zip(self.counts, decisions + [either, both]):
                self.update(self.counts[name], decision, truth)
                self.update(self.scenarios[str(scenario)][name], decision, truth)
            selected = either if self.rule == 'OR' else both
            self.writer.writerow([index, index / self.fs, scenario, truth,
                                  *powers, *decisions, either, both, selected])
            record = dict(sequence=self.records, sample_index=index, truth=truth,
                          scenario=int(scenario), powers=powers, decisions=decisions,
                          fusion_rule=self.rule, fused=selected, config_sha256=self.config_hash,
                          previous_hash=self.previous_hash, mode='LOCAL_MOCK_NOT_BLOCKCHAIN')
            canonical = json.dumps(record, sort_keys=True, separators=(',', ':'))
            self.previous_hash = hashlib.sha256(canonical.encode()).hexdigest()
            record['hash'] = self.previous_hash
            self.ledger_file.write(json.dumps(record, sort_keys=True) + '\n')
            self.records += 1
        self.position += n
        return n

    @staticmethod
    def metrics(counts):
        tp, fp, tn, fn = (counts[k] for k in ('tp', 'fp', 'tn', 'fn'))
        return dict(counts, probability_detection=tp / (tp + fn) if tp + fn else None,
                    probability_false_alarm=fp / (fp + tn) if fp + tn else None)

    def stop(self):
        if self.directory is not None:
            expected = int(self.config.get('expected_samples', 0))
            summary = dict(samples_consumed=self.position, expected_samples=expected,
                           completed=(self.position == expected) if expected else None,
                           observations=self.records, final_mock_hash=self.previous_hash,
                           metrics={k: self.metrics(v) for k, v in self.counts.items()},
                           per_scenario={s: {k: self.metrics(v) for k, v in nodes.items()}
                                         for s, nodes in self.scenarios.items()},
                           limitations=['Simulation only; no RF validation',
                                        'Ideal synchronized reporting, no packet loss or network model',
                                        'Local hash chain, no consensus, contract or blockchain network',
                                        'Window observations overlap in filter memory; no confidence intervals'])
            (self.directory / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
            self.csv_file.close()
            self.ledger_file.close()
        return True
