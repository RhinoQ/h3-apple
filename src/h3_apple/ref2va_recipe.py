"""Explicit Ref2VA adapter identities; no inference from tensor counts."""

DARETIES_SOURCE = dict(
    repo="silveroxides/MiniMax-H3_tests",
    revision="16f950c2e3d78440778fe1e84d9179932e19b1de",
    filename="ref2v_dareties/minimax_h3_ref2v_turbo_4step_v0.1_v4_step600_dareties_fro0995.safetensors",
    bytes=1158485256,
    sha256="e44c667b162a6e951f663b75d88facfd4e24c915e2c556b07ec1fec23fef5a61",
)
DARETIES_RECIPE = dict(
    schema="h3-apple-ref2va-dareties/v1", task="ref2va",
    adapter_source=DARETIES_SOURCE, lora_tensors=518, lora_pairs=259,
    mapped_targets=363, adaln_targets=51, alpha_normalized=True, lora_strength=1.0,
    qkv_layout="comfy_contiguous_qkv", swiglu_layout="gate_first",
    gate_tensors=50, precision="int8_group64_bf16", fasth3_t2va_deltas_applied=False,
)


def validate_ref2va_recipe(recipe):
    if recipe.get("schema") == DARETIES_RECIPE["schema"]:
        expected = DARETIES_RECIPE
    else:
        expected = dict(schema="h3-apple-ref2va/v1", task="ref2va", lora_rank=128,
                        lora_alpha=8, lora_tensors=624, gate_tensors=50,
                        precision="int8_group64_bf16", fasth3_t2va_deltas_applied=False)
    if any(recipe.get(key) != value for key, value in expected.items()):
        raise ValueError("Expected an explicit Ref2VA four-step checkpoint with 50 VSA gates.")
