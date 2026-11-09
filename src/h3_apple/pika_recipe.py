"""Pika H3 Flex image-reference recipe from the pinned Mellis release."""

RECIPE = "pika-flex-ref2va-v1"
ADAPTER = "eef684ba1258f0cdbbbda6128188ad2688417f2eb17ff875375e74a32b6d61b5"
MANIFEST = "758497d3b316ea1a956a5b460d6c02ef380ecb5bf95f16f29e932d438c3ccff8"
KNOTS = (1000, 750, 500, 250, 100, 40, 0)


def sigmas(shift):
    import numpy as np
    grid = np.array(KNOTS, dtype=np.float64) / 1000
    return (shift * grid / (1 + (shift-1)*grid)).astype(np.float32)


def update(state, velocity, ladder, index, noise):
    import mlx.core as mx
    clean = state.astype(mx.float32) + float(ladder[index]) * velocity.astype(mx.float32)
    if index == len(ladder) - 2:
        return clean
    sigma_next = float(ladder[index+1])
    return (1 - sigma_next) * clean + sigma_next * mx.array(noise(state.shape), dtype=mx.float32)


def sources():
    hub = dict(repo="Pika-Labs/Pika-H3-Flex", revision="ca45d99f9b1d1859ffb9dc1cd6bfaaa994257f56")
    return [dict(hub, filename="ref2va/adapter.safetensors", bytes=2767274120, sha256=ADAPTER),
            dict(hub, filename="ref2va/manifest.json", bytes=1040, sha256=MANIFEST)]
