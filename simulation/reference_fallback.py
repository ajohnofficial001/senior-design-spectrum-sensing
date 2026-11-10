"""Predeclared reference-sector censoring; no truth or noise schedule input."""
import math
import statistics


def fallback_features(long_features):
    refs = list(long_features['reference_sectors'])
    if len(refs) != 4 or any(not math.isfinite(v) or v <= 0 for v in refs):
        return dict(reliable=False, score=0., sectors_used=0)
    # Lower pair seeds a candidate noise cluster; censor high/low outliers.
    anchor = statistics.mean(sorted(refs)[:2])
    survivors = [v for v in refs if .5 * anchor <= v <= 2. * anchor]
    reliable = len(survivors) >= 2 and max(survivors) / min(survivors) <= 2.
    noise = statistics.median(survivors) if reliable else None
    return dict(reliable=reliable, score=long_features['target_power'] / noise if reliable else 0.,
                sectors_used=len(survivors), noise_reference=noise)


def decide(features, threshold):
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError('Expected positive finite threshold')
    return int(features['score'] > threshold) if features['reliable'] else None
