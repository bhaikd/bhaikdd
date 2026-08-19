#!/usr/bin/env python3
"""
prep_photo.py — turn a normal photo into a clean, high-contrast grayscale
source image ready for ASCII conversion.

Steps:
  1. Remove the background with rembg so only the subject remains.
  2. Composite onto pure white so background -> blank end of ramp.
  3. Edge-preserving smoothing to kill high-frequency texture (plaid
     shirts, fabric weave) that would otherwise alias into ASCII "static" —
     while keeping the face's actual contours crisp.
  4. Gentle CLAHE contrast boost (mild — enough for real highlights/
     shadows on skin without re-amplifying texture noise).
  5. Crop to subject bounding box with generous padding so the portrait
     has real breathing room instead of filling the whole frame.

Usage:
    python scripts/prep_photo.py source-photo.jpg [output.png]
"""
import sys
import numpy as np
import cv2
from PIL import Image
from rembg import remove, new_session

# u2netp is the small (~4.7MB) model — plenty for a clean headshot cutout
# and much lighter on memory than the default multi-GB model.
_SESSION = new_session("u2netp")


def prep(in_path: str, out_path: str = "source-prepped.png"):
    with open(in_path, "rb") as f:
        input_bytes = f.read()

    # 1. Remove background -> RGBA with alpha mask around the subject
    result_bytes = remove(input_bytes, session=_SESSION)
    rgba = Image.open(__import__("io").BytesIO(result_bytes)).convert("RGBA")

    # 2. Composite onto pure white using the alpha mask
    white_bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(white_bg, rgba).convert("RGB")
    gray = cv2.cvtColor(np.array(composited), cv2.COLOR_RGB2GRAY)

    # 3. Edge-preserving smoothing — kills fine fabric/texture noise
    #    (plaid shirts etc.) that otherwise turns into ASCII "static",
    #    while keeping the face's real edges intact.
    smoothed = cv2.bilateralFilter(gray, d=9, sigmaColor=60, sigmaSpace=60)

    # 4. Mild CLAHE — enough contrast for real shading, not so much that
    #    it re-introduces texture noise in the smoothed regions.
    clahe = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(16, 16))
    boosted = clahe.apply(smoothed)

    # Re-flatten background to pure white using the alpha mask from rembg
    alpha_arr = np.array(rgba.split()[-1])
    boosted = np.where(alpha_arr > 10, boosted, 255).astype(np.uint8)

    # 5. Crop to the subject's bounding box with generous padding so the
    #    portrait doesn't fill the whole frame (leaves breathing room).
    ys, xs = np.where(alpha_arr > 10)
    if len(xs) and len(ys):
        pad = int(0.22 * max(boosted.shape))
        x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, boosted.shape[1])
        y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, boosted.shape[0])
        boosted = boosted[y0:y1, x0:x1]

    Image.fromarray(boosted).save(out_path)
    print(f"wrote {out_path}  ({boosted.shape[1]}x{boosted.shape[0]})")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "source-photo.jpg"
    dst = sys.argv[2] if len(sys.argv) > 2 else "source-prepped.png"
    prep(src, dst)
