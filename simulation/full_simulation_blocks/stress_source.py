"""Additional channel models; original source and GRCs remain unchanged."""
import numpy as np
from .scenario_source import blk as BaselineSource


class blk(BaselineSource):
    def __init__(self, sample_rate=2000000, segment_samples=20000, cycles=100,
                 signal_amplitude=0.0002, seed=50001, noise_factor=1.0,
                 noise_step=False, fading=False, reference_tone_amplitude=0.0):
        super().__init__(sample_rate=sample_rate, segment_samples=segment_samples,
                         cycles=cycles, signal_amplitude=signal_amplitude, seed=seed)
        if noise_factor <= 0:
            raise ValueError('noise_factor must be positive')
        self.reference_tone_amplitude = float(reference_tone_amplitude)
        self.noise_factor = float(noise_factor)
        self.noise_step = bool(noise_step)
        self.fading = bool(fading)
        channel_rng = np.random.default_rng(int(seed) + 100000)
        # Unit mean power complex Rayleigh block fading, independent across nodes.
        self.channels = ((channel_rng.standard_normal((2, 4 * int(cycles), 2)) @
                          np.array([1, 1j])) / np.sqrt(2)) if fading else None

    def work(self, input_items, output_items):
        n = min(len(output_items[0]), self.total - self.position)
        if n <= 0:
            return -1
        index = np.arange(self.position, self.position + n, dtype=np.int64)
        segments = index // self.segment
        scenario = segments % 4
        truth = (scenario % 2).astype(np.float32)
        wanted = self.amplitude * truth * np.exp(2j * np.pi * self.offset * index / self.fs)
        interferer = self.interference_amplitude * (scenario >= 2) * np.exp(
            2j * np.pi * self.interference_offset * index / self.fs)
        interferer += self.reference_tone_amplitude * np.exp(2j * np.pi * 490000 * index / self.fs)
        # Alternate noise amplitude by complete cycle; occupancy remains balanced.
        noise_scale = (np.where((segments // 4) % 2 == 0, .8, 1.2)
                       if self.noise_step else np.ones(n)) * self.noise_factor
        for node, gain in enumerate((1.0, self.gain2)):
            iq = self.rng[node].standard_normal((n, 2)) * self.noise[node]
            channel = self.channels[node, segments] if self.fading else 1.0
            output_items[node][:n] = gain * channel * (wanted + interferer) + noise_scale * (iq[:, 0] + 1j * iq[:, 1])
        output_items[2][:n] = truth
        self.position += n
        return n
