"""The qualified VOSR2 recipe, with native PyTorch kernels on MPS."""

from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from .model import Restorer
from ._vendor.vosr import tiling
from ._vendor.vosr.conditioning import wavelet_color_fix


def frame_noise(width, height):
    """Replay the original native noise; use a local fixed CPU seed for X2 sizes."""
    path = Path(__file__).parents[1] / 'data/vosr-noise.npz'
    from ..io import digest
    from .assets import manifest
    if digest(path) != manifest()['noise']['sha256']:
        raise RuntimeError('Packaged VOSR noise checksum mismatch. Reinstall h3-apple.')
    with np.load(path, allow_pickle=False) as arrays:
        key = f'{width}x{height}'
        if key in arrays:
            return torch.from_numpy(arrays[key])
    if (width, height) not in ((1920, 1088), (1088, 1920), (2048, 1152), (1152, 2048)):
        raise ValueError('Unsupported VOSR frame size.')
    shape = (1, 16, ((height * 2 + 15) // 16) * 2, ((width * 2 + 15) // 16) * 2)
    return torch.randn(shape, generator=torch.Generator(device='cpu').manual_seed(42), dtype=torch.float32)


def submit_after(fn):
    event = torch.mps.Event(enable_timing=False)

    def call(*args, **kwargs):
        result = fn(*args, **kwargs)
        event.record()
        return result

    return call


def configure(restorer):
    for model in (restorer.encoder, restorer.model):
        for module in model.modules():
            if isinstance(module, (torch.nn.Linear, torch.nn.Conv2d)):
                module.to(dtype=torch.float16)
    decoder = restorer.vae.decoder
    protected = {id(child) for module in decoder.modules()
                 if module.__class__.__name__ == 'AttentionBlock2D' for child in module.modules()}
    for module in decoder.modules():
        if isinstance(module, torch.nn.Conv2d) and id(module) not in protected:
            forward = module.forward

            def call(x, _forward=forward):
                with torch.autocast(x.device.type, dtype=torch.float16):
                    return _forward(x).float()

            module.forward = call
    restorer.model.forward = submit_after(restorer.model.forward)


class Upscaler:
    def __init__(self, model_dir, width, height):
        if torch.__version__.split('+')[0] != '2.14.1' or not torch.backends.mps.is_available():
            raise RuntimeError('VOSR requires PyTorch 2.14.1 with MPS on the supported Mac.')
        torch.set_num_threads(4)
        torch.set_grad_enabled(False)
        self.size = (width, height)
        self.restorer = Restorer(Path(model_dir))
        args = self.restorer.args
        args.tile_size, args.tile_overlap = 512, 32
        args.posterior_mode, args.infer_steps = True, 1
        configure(self.restorer)
        if max(self.size) > 1366:
            for module in self.restorer.vae.modules():
                if module.__class__.__name__ == 'AttentionBlock2D':
                    module.query_chunk_size = 2048
        # Only this worker's namespaced tiling function uses the submission wrapper.
        self.features = tiling.get_venc_features
        tiling.get_venc_features = submit_after(self.features)
        self.noise = frame_noise(width, height).to('mps')
        self.finite = []
        for module in (self.restorer.vae.decoder, self.restorer.vae.quant_conv, self.restorer.model):
            module.register_forward_hook(self.check_finite)
        torch.mps.synchronize()

    def check_finite(self, module, values, result):
        self.finite.append(torch.isfinite(result).all())

    @torch.inference_mode()
    def restore(self, image):
        if image.size != self.size:
            raise ValueError('Video dimensions changed during decoding.')
        target = image.convert('RGB').resize(tuple(n * 2 for n in self.size), Image.Resampling.BICUBIC)
        width, height = target.size
        pixels = np.pad(np.asarray(target), ((0, -height % 16), (0, -width % 16), (0, 0)), mode='reflect')
        tensor = transforms.ToTensor()(pixels).unsqueeze(0).to('mps') * 2 - 1
        self.finite.clear()
        with torch.autocast('mps', dtype=torch.float16):
            prediction = tiling.tiled_latent_inference(
                self.restorer.model, self.restorer.vae, self.restorer.encoder,
                tensor, self.restorer.args, device='mps', noise=self.noise)
        torch.mps.synchronize()
        if (prediction.shape != tensor.shape or not self.finite
                or not bool(torch.stack(self.finite).all()) or not bool(torch.isfinite(prediction).all())):
            raise RuntimeError('VOSR produced invalid dimensions or nonfinite values.')
        raw = transforms.ToPILImage()(prediction[0, :, :height, :width].cpu() * .5 + .5)
        restored = wavelet_color_fix(raw, target)
        if np.asarray(restored).std() < 1:
            raise RuntimeError('VOSR produced a blank frame.')
        return restored
