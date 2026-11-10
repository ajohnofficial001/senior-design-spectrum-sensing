"""Reference-band normalized energy, without ground-truth input to decisions."""
import math
import numpy as np

METHODS = ('reference_4000', 'reference_8000', 'two_look')


class FeatureFrames:
    """Scheduler-chunk-independent frames that never cross scenario boundaries."""
    def __init__(self):
        self.position = 0
        self.buffers = [np.empty(0, dtype=np.complex64) for _ in range(2)]
        self.records = []

    def push(self, inputs):
        n, offset = len(inputs[0]), 0
        while offset < n:
            absolute = self.position + offset
            take = min(n - offset, 20000 - absolute % 20000)
            for node in range(2):
                self.buffers[node] = np.concatenate((self.buffers[node], inputs[node][offset:offset+take]))
            while len(self.buffers[0]) >= 8000:
                end = absolute + take - len(self.buffers[0]) + 8000 - 1
                features = [observe(buffer[:8000]) for buffer in self.buffers]
                self.records.append(dict(sample_index=int(end), scenario=int(end // 20000 % 4),
                                         truth=int(inputs[2][offset] >= .5), nodes=features))
                self.buffers = [b[8000:] for b in self.buffers]
            offset += take
            if (self.position + offset) % 20000 == 0:
                self.buffers = [np.empty(0, dtype=np.complex64) for _ in range(2)]
        self.position += n
        return n


def spectral_features(samples, fs=2000000):
    samples = np.asarray(samples, dtype=np.complex128)
    if len(samples) not in (4000, 8000) or not np.all(np.isfinite(samples)):
        raise ValueError('Expected 4000 or 8000 finite complex samples')
    window = np.hanning(len(samples))
    power = np.abs(np.fft.fft(samples * window)) ** 2 / np.sum(window ** 2)
    frequency = np.fft.fftfreq(len(samples), 1 / fs)
    target = float(np.mean(power[(frequency >= 380000) & (frequency < 420000)]))
    references = [float(np.mean(power[(frequency >= lo) & (frequency < hi)]))
                  for lo, hi in ((280000, 310000), (310000, 340000),
                                 (460000, 490000), (490000, 520000))]
    floor = max(float(np.median(references)), np.finfo(float).tiny)
    spread = max(references) / max(min(references), np.finfo(float).tiny)
    return dict(score=target / floor, noise_reference=floor, reference_spread=spread,
                reliable=bool(spread <= 4 and floor > np.finfo(float).tiny))


def observe(samples):
    if len(samples) != 8000:
        raise ValueError('Expected an 8000-sample frame')
    short, long = spectral_features(samples[:4000]), spectral_features(samples)
    return dict(short=short, long=long,
                scores=dict(reference_4000=short['score'], reference_8000=long['score'],
                            two_look=max(short['score'] if short['reliable'] else 0.,
                                         long['score'] if long['reliable'] else 0.)),
                reliable=dict(reference_4000=short['reliable'], reference_8000=long['reliable'],
                              two_look=short['reliable'] or long['reliable']))


def decide(features, method, threshold):
    if method not in METHODS or not math.isfinite(threshold) or threshold <= 0:
        raise ValueError('Invalid method or threshold')
    if method == 'two_look':
        if features['short']['reliable'] and features['short']['score'] > threshold:
            return 1, 4000
        if features['long']['reliable']:
            return int(features['long']['score'] > threshold), 8000
        return None, 8000
    if not features['reliable'][method]:
        return None, 8000 if method != 'reference_4000' else 4000
    decision = int(features['scores'][method] > threshold)
    listening = 4000 if method == 'reference_4000' or (
        method == 'two_look' and features['short']['score'] > threshold) else 8000
    return decision, listening
