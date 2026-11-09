# SPDX-License-Identifier: GPL-3.0
"""Source code also embedded in full_simulation.grc; no device access."""
import numpy as np
from gnuradio import gr


class blk(gr.sync_block):
    """Finite two-node scenario source. Ports: RX1 complex, RX2 complex, truth float."""

    def __init__(self, sample_rate=2000000, segment_samples=20000, cycles=10,
                 tone_offset=400000, signal_amplitude=0.0002,
                 interference_offset=600000, interference_amplitude=0.002,
                 node2_gain=0.65, noise1=0.001, noise2=0.0012, seed=101):
        gr.sync_block.__init__(self, name='Finite two-node scenarios', in_sig=None,
                               out_sig=[np.complex64, np.complex64, np.float32])
        if sample_rate <= 0 or segment_samples < 1 or cycles < 1:
            raise ValueError('Positive sample rate, segment length and cycles required')
        if max(abs(tone_offset), abs(interference_offset)) >= sample_rate / 2:
            raise ValueError('Tone and interference offsets must be below Nyquist')
        if min(signal_amplitude, interference_amplitude, node2_gain, noise1, noise2) < 0:
            raise ValueError('Amplitudes and gains must be nonnegative')
        self.fs = float(sample_rate)
        self.segment = int(segment_samples)
        self.total = self.segment * 4 * int(cycles)
        self.offset, self.amplitude = tone_offset, signal_amplitude
        self.interference_offset = interference_offset
        self.interference_amplitude = interference_amplitude
        self.gain2 = node2_gain
        self.noise = (noise1, noise2)
        self.rng = (np.random.default_rng(int(seed)), np.random.default_rng(int(seed) + 1))
        self.position = 0

    def work(self, input_items, output_items):
        n = min(len(output_items[0]), self.total - self.position)
        if n <= 0:
            return -1
        index = np.arange(self.position, self.position + n, dtype=np.int64)
        scenario = (index // self.segment) % 4
        occupied = (scenario % 2).astype(np.float32)
        interferer_on = scenario >= 2
        wanted = self.amplitude * occupied * np.exp(2j * np.pi * self.offset * index / self.fs)
        unwanted = self.interference_amplitude * interferer_on * np.exp(
            2j * np.pi * self.interference_offset * index / self.fs)
        for node, gain in enumerate((1.0, self.gain2)):
            # Interleaved I/Q draws give identical samples across scheduler chunk sizes.
            iq = self.rng[node].standard_normal((n, 2)) * self.noise[node]
            output_items[node][:n] = gain * (wanted + unwanted) + iq[:, 0] + 1j * iq[:, 1]
        output_items[2][:n] = occupied
        self.position += n
        return n
