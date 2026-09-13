"""Media components can be reused without loading an unrelated DiT checkpoint."""
import pytest

from h3_apple.conversion import CONFIG
from h3_apple.runtime.engine import Pipeline


def test_media_geometry_needs_no_prepared_transformer(tmp_path):
    for name in ('vae','audio_vae'):
        (tmp_path/name).mkdir()
        (tmp_path/name/'model.safetensors').touch()
    pipeline=Pipeline(model_root=tmp_path,mlx_dit_checkpoint=None,dit_config=CONFIG)
    assert pipeline.dit_checkpoint is None and pipeline._dit_in_channels==24
    assert pipeline._dit_patch_size==(1,2,2)
    with pytest.raises(ValueError,match='prepared checkpoint'):
        pipeline.denoise(None,None,height=768,width=1376,num_frames=124,seed=42)


def test_media_only_constructor_still_rejects_missing_components(tmp_path):
    with pytest.raises(FileNotFoundError,match='Missing required'):
        Pipeline(model_root=tmp_path,mlx_dit_checkpoint=None,dit_config=CONFIG)


def test_missing_geometry_fails_before_loading(tmp_path):
    with pytest.raises(ValueError,match='explicit DiT geometry'):
        Pipeline(model_root=tmp_path,mlx_dit_checkpoint=None)
