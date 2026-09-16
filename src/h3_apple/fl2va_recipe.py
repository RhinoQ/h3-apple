"""Pinned LightX2V FL2VA v1.2 weights and their sampling recipe."""

FL12_SOURCE = dict(
    repo="lightx2v/Minimax-h3-Turbo",
    revision="3ec17a324ced54151364f24f8b5fb6bf7e26414f",
    filename="minimax_h3_fl2v_turbo_4step_v1.2_768p_bf16.safetensors",
    bytes=1383677808,
    sha256="c3d4a2cf618efea71b9e21a4baaa12d412f1eb6c2b6f86efacaf0ebb6814b689",
)
FL12_SAMPLING = dict(
    recipe_id="lightx2v-fl2va-4step-v1.2-768p", sampler="euler",
    num_steps=4, video_shift=6, audio_shift=3,
    adapter_sha256=FL12_SOURCE["sha256"],
)


def fl2va_sampling(recipe, requested_steps=4):
    expected = dict(schema="h3-apple-fl2va/v1", task="fl2va", lora_tensors=624,
                    lora_rank=128, lora_alpha=8, gate_tensors=50,
                    precision="int8_group64_bf16", fasth3_t2va_deltas_applied=False,
                    sampling=FL12_SAMPLING)
    if any(recipe.get(key) != value for key, value in expected.items()):
        raise ValueError("FL2VA requires the pinned LightX2V v1.2 recipe and all 50 VSA gates; prepare a new bundle.")
    if type(requested_steps) is not int or requested_steps != 4:
        raise ValueError("LightX2V FL2VA v1.2 requires four steps.")
    return dict(FL12_SAMPLING)
