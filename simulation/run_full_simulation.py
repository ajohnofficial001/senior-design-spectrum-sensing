#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0
"""Hand-maintained runner for full_simulation.grc's default configuration.

Use grcc on the GRC file when changing its variables; this runner is not regenerated.
"""
import signal
from gnuradio import gr, blocks, filter
from gnuradio.filter import firdes
from full_simulation_blocks.scenario_source import blk as ScenarioSource
from full_simulation_blocks.fusion_logger import blk as FusionLogger


class FullSimulation(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self, 'Two-node cooperative spectrum sensing - SOFTWARE ONLY')
        fs, segment, cycles, window, scale = 2000000, 20000, 10, 1000, 1000000
        taps = firdes.low_pass(1.0, fs, 20000, 10000)
        self.source = ScenarioSource()
        config = dict(expected_samples=4 * segment * cycles, cycles=cycles,
                      tone_offset=400000, signal_amplitude=0.0002,
                      interference_offset=600000, interference_amplitude=0.002,
                      node2_gain=0.65, noise1=0.001, noise2=0.0012, seed=101,
                      power_scale=scale, filter_taps=list(taps),
                      noise_definition='independent I/Q standard deviation',
                      scenario_order=['noise_only', 'wanted', 'interferer_only',
                                      'wanted_and_interferer'])
        self.logger = FusionLogger(guard_samples=len(taps) + window, config=config)
        self.processing = []
        for node in range(2):
            channel_filter = filter.freq_xlating_fir_filter_ccc(1, taps, 400000, fs)
            self.connect((self.source, node), channel_filter)
            self.processing.append(channel_filter)
            for branch in range(2):
                mag = blocks.complex_to_mag_squared(1)
                average = blocks.moving_average_ff(window, 1.0 / window, 4000, 1)
                scaling = blocks.multiply_const_ff(scale)
                origin = (channel_filter, 0) if branch == 0 else (self.source, node)
                self.connect(origin, mag, average, scaling, (self.logger, node + 2 * branch))
                self.processing.extend((mag, average, scaling))
        self.connect((self.source, 2), (self.logger, 4))


def main():
    tb = FullSimulation()
    def stop(*_):
        tb.stop()
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    tb.start()
    tb.wait()


if __name__ == '__main__':
    main()
