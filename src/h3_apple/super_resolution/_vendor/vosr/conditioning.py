# Adapted from VOSR 516f292b99cf23c76fdc33351e86dc4f97711fe8. Apache-2.0.
# H3 Apple modification: inference functions only, no CLI or training imports.
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from torchvision.transforms import Normalize
IMAGENET_DEFAULT_MEAN = (0.485, 0.456, 0.406)
IMAGENET_DEFAULT_STD = (0.229, 0.224, 0.225)

def wavelet_color_fix(target, source):
    import cv2
    target_np = np.array(target).astype(np.float32) / 255.0
    source_np = np.array(source.resize(target.size, Image.LANCZOS)).astype(np.float32) / 255.0
    sigma = 5
    source_low = cv2.GaussianBlur(source_np, (0, 0), sigma)
    target_low = cv2.GaussianBlur(target_np, (0, 0), sigma)
    target_high = target_np - target_low
    result = np.clip(source_low + target_high, 0, 1) * 255.0
    return Image.fromarray(result.astype(np.uint8))

def preprocess_raw_image(x, args):
    x = x / 255.
    x = F.interpolate(x, args.dinov2_size, mode='bicubic').clip(0., 1.)
    x = Normalize(IMAGENET_DEFAULT_MEAN, IMAGENET_DEFAULT_STD)(x)
    return x

def get_venc_features(venc, lq_tensor, args):
    with torch.no_grad():
        raw_image = (0.5 * lq_tensor + 0.5) * 255
        raw_image_ = preprocess_raw_image(raw_image, args)
        features, x_norm = venc.forward_with_features(raw_image_)
        z = [v for k, v in features.items() if k.startswith('layer_')]
        z[-1] = x_norm
        z = [z[i] for i in args.layer_dinov2b_list]
    return z
