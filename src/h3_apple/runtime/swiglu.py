"""Keep packed SwiGLU view offsets within signed 32-bit element indexing.

The pinned MLX backend can misread split views spanning more than INT32_MAX
elements, even when the logical half-view has fewer elements. Only the
elementwise activation is split; the two projection calls keep their shapes,
weights, dtypes and reduction order.
"""

INT32_MAX = 2**31 - 1
ROW_CHUNK = 32768


def bounded_swiglu(hidden):
    import mlx.core as mx

    if hidden.ndim != 2 or hidden.shape[1] % 2:
        raise ValueError("expected 2D value-first packed SwiGLU halves")
    if hidden.size <= INT32_MAX:
        value, gate = mx.split(hidden, 2, axis=-1)
        return value * (gate * mx.sigmoid(gate))
    # Slice the packed buffer first, so both half-views have bounded spans.
    rows = min(ROW_CHUNK, INT32_MAX // hidden.shape[1])
    if rows < 1:
        raise ValueError("one SwiGLU row exceeds the supported indexing span")
    parts = []
    for start in range(0, hidden.shape[0], rows):
        value, gate = mx.split(hidden[start:start + rows], 2, axis=-1)
        part = value * (gate * mx.sigmoid(gate))
        mx.eval(part)
        parts.append(part)
    return mx.concatenate(parts, axis=0)


def make_bounded_feed_forward(model, receipt):
    """Build a scoped FFN replacement with an explicit affected-call count."""
    receipt.update(bounded_swiglu_calls=0, ordinary_swiglu_calls=0)

    def feed_forward(weights, x):
        hidden = model.linear(x, weights["ff.net.0.proj.weight"])
        key = "bounded_swiglu_calls" if hidden.size > INT32_MAX else "ordinary_swiglu_calls"
        receipt[key] += 1
        return model.linear(bounded_swiglu(hidden), weights["ff.net.2.weight"])

    return feed_forward
