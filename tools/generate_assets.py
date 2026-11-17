"""Generate Ryotech web assets from the two brand source images.

Usage:
    python tools/generate_assets.py --logo path/to/logo.jpg --banner path/to/banner.jpg

Outputs (relative to the repository root):
    assets/img/logo-mark-{96,192}.webp            transparent, tightly cropped emblem (colour-to-alpha) for header/footer
    assets/img/hero-emblem-{480,640,960}.webp     opaque emblem with its glow on the logo background, for the hero
    assets/img/icon-192.png, icon-512.png         opaque app icons
    assets/img/icon-maskable-512.png              maskable icon (emblem inside the 40% safe radius)
    assets/img/og-image.jpg                       1200x630 social preview cropped from the banner
    assets/img/cta-texture.webp, -420.webp        decorative texture from the banner centre (820w and 420w)
    apple-touch-icon.png                          180x180 opaque
    favicon.ico                                   16/32/48

The source images are expected to be the 2048x2048 logo and the 3584x1184 banner.
Requires Pillow and numpy.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "assets" / "img"

GLOW_CENTER = (1050.0, 951.0)
FADE_INNER = 820.0
FADE_OUTER = 900.0
EMBLEM_CROP = (150, 51, 1950, 1851)
OG_CROP = (0, 41, 2100, 1143)
TEXTURE_CROP = (1310, 0, 2130, 1184)
LETTERS_CROP = (440, 770, 1610, 1600)
MARK_SIZES = (96, 192)
HERO_SIZES = (480, 640, 960)


def border_median(arr: np.ndarray, band: int = 100) -> np.ndarray:
    h, w, _ = arr.shape
    mask = np.zeros((h, w), dtype=bool)
    mask[:band, :] = True
    mask[-band:, :] = True
    mask[:, :band] = True
    mask[:, -band:] = True
    return np.median(arr[mask], axis=0)


def color_to_alpha(src: Image.Image) -> tuple[Image.Image, np.ndarray, np.ndarray]:
    rgb = src.convert("RGB")
    p = np.asarray(rgb, dtype=np.float64) / 255.0
    b = border_median(p)

    alpha = np.clip((p - b) / (1.0 - b), 0.0, 1.0).max(axis=2)
    floor = 0.012
    alpha = np.where(alpha >= 2.0 * floor, alpha, np.clip((alpha - floor) * 2.0, 0.0, None))

    h, w = alpha.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(xx - GLOW_CENTER[0], yy - GLOW_CENTER[1])
    t = np.clip((FADE_OUTER - r) / (FADE_OUTER - FADE_INNER), 0.0, 1.0)
    fade = t * t * (3.0 - 2.0 * t)
    alpha = alpha * fade

    safe = np.where(alpha > 0, alpha, 1.0)[..., None]
    fg = np.clip(b + (p - b) / safe, 0.0, 1.0)
    fg[alpha <= 0] = 0.0

    rgba = np.dstack([fg, alpha])
    out = Image.fromarray(np.round(rgba * 255.0).astype(np.uint8), "RGBA")
    return out, p, b


def verify_alpha(rgba: Image.Image, original: np.ndarray, b: np.ndarray) -> None:
    arr = np.asarray(rgba, dtype=np.float64) / 255.0
    a = arr[..., 3:4]
    comp = arr[..., :3] * a + b * (1.0 - a)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    inner = np.hypot(xx - GLOW_CENTER[0], yy - GLOW_CENTER[1]) <= FADE_INNER
    err = np.abs(comp - original)[inner] * 255.0
    mean_err = float(err.mean())
    p99_err = float(np.percentile(err, 99))
    print(f"  recomposite error inside r<={FADE_INNER:.0f}: mean={mean_err:.3f} p99={p99_err:.3f} levels")
    if mean_err >= 1.0 or p99_err > 4.0:
        raise SystemExit("colour-to-alpha self-check failed: recomposite error too large")


def resize_rgba(img: Image.Image, size: int) -> Image.Image:
    return img.convert("RGBa").resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")


def build_marks(logo: Image.Image) -> np.ndarray:
    rgba, original, b = color_to_alpha(logo)
    verify_alpha(rgba, original, b)
    alpha = np.asarray(rgba, dtype=np.float64)[..., 3] / 255.0

    full = rgba.crop(EMBLEM_CROP)
    edge = np.asarray(full, dtype=np.float64)[..., 3] / 255.0
    edge_max = max(edge[:4, :].max(), edge[-4:, :].max(), edge[:, :4].max(), edge[:, -4:].max())
    print(f"  max alpha on outer 4px of full crop: {edge_max:.4f}")
    if edge_max >= 0.01:
        raise SystemExit("colour-to-alpha self-check failed: crop edge not transparent")

    cx, cy, radius, _ = solid_geometry(alpha)
    half = radius * 1.06
    tight = square_crop(rgba, cx, cy, 2.0 * half)
    arr = np.asarray(tight, dtype=np.float64).copy()
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(xx - (w - 1) / 2.0, yy - (h - 1) / 2.0)
    t = np.clip((half - r) / (half - radius - 4.0), 0.0, 1.0)
    arr[..., 3] *= t * t * (3.0 - 2.0 * t)
    tight = Image.fromarray(np.round(arr).astype(np.uint8), "RGBA")
    for size in MARK_SIZES:
        out = IMG / f"logo-mark-{size}.webp"
        resize_rgba(tight, size).save(out, "WEBP", quality=75, alpha_quality=80, method=6)
        print(f"  wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")
    return alpha


def build_hero(logo: Image.Image) -> None:
    crop = logo.convert("RGB").crop(EMBLEM_CROP)
    for size in HERO_SIZES:
        out = IMG / f"hero-emblem-{size}.webp"
        crop.resize((size, size), Image.Resampling.LANCZOS).save(out, "WEBP", quality=85, method=6)
        print(f"  wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


def punch(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Contrast(img).enhance(1.35)
    img = ImageEnhance.Brightness(img).enhance(1.25)
    return ImageEnhance.Color(img).enhance(1.15)


def solid_geometry(alpha: np.ndarray, threshold: float = 0.5) -> tuple[float, float, float, tuple[int, int, int, int]]:
    ys, xs = np.nonzero(alpha >= threshold)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    radius = float(np.hypot(xs - cx, ys - cy).max())
    return cx, cy, radius, (int(x0), int(y0), int(x1), int(y1))


def square_crop(img: Image.Image, cx: float, cy: float, side: float) -> Image.Image:
    half = side / 2.0
    box = (int(round(cx - half)), int(round(cy - half)), int(round(cx + half)), int(round(cy + half)))
    return img.crop(box)


def build_icons(logo: Image.Image, alpha: np.ndarray) -> None:
    rgb = logo.convert("RGB")
    cx, cy, radius, bbox = solid_geometry(alpha)
    print(f"  solid emblem bbox={bbox} centre=({cx:.0f},{cy:.0f}) farthest radius={radius:.0f}")

    side = max(bbox[2] - bbox[0], bbox[3] - bbox[1]) * 1.12
    icon_src = square_crop(rgb, cx, cy, side)
    for size, name in ((512, "icon-512.png"), (192, "icon-192.png")):
        icon_src.resize((size, size), Image.Resampling.LANCZOS).save(IMG / name, optimize=True)
        print(f"  wrote assets/img/{name}")
    icon_src.resize((180, 180), Image.Resampling.LANCZOS).save(ROOT / "apple-touch-icon.png", optimize=True)
    print("  wrote apple-touch-icon.png")

    maskable_side = radius / 0.40
    square_crop(rgb, cx, cy, maskable_side).resize((512, 512), Image.Resampling.LANCZOS).save(
        IMG / "icon-maskable-512.png", optimize=True
    )
    print(f"  wrote assets/img/icon-maskable-512.png (source side {maskable_side:.0f}px)")

    full_small = punch(square_crop(rgb, cx, cy, max(bbox[2] - bbox[0], bbox[3] - bbox[1]) * 1.02))
    letters = rgb.crop(LETTERS_CROP)
    side = letters.width
    letters_sq = Image.new("RGB", (side, side), tuple(int(v) for v in np.round(border_median(np.asarray(rgb, dtype=np.float64)))))
    letters_sq.paste(letters, (0, (side - letters.height) // 2))
    letters_sq = punch(letters_sq)
    frames = {
        16: letters_sq.resize((16, 16), Image.Resampling.LANCZOS),
        32: letters_sq.resize((32, 32), Image.Resampling.LANCZOS),
        48: full_small.resize((48, 48), Image.Resampling.LANCZOS),
    }
    frames[48].save(
        ROOT / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[frames[16], frames[32]],
    )
    print("  wrote favicon.ico (16/32 letters-only, 48 full emblem)")


def build_og(banner: Image.Image) -> None:
    crop = banner.convert("RGB").crop(OG_CROP).resize((1200, 630), Image.Resampling.LANCZOS)
    out = IMG / "og-image.jpg"
    crop.save(out, "JPEG", quality=86, optimize=True, progressive=True)
    print(f"  wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


def build_texture(banner: Image.Image) -> None:
    crop = banner.convert("RGB").crop(TEXTURE_CROP)
    w, h = crop.size
    for target_w, name in ((820, "cta-texture.webp"), (420, "cta-texture-420.webp")):
        out = IMG / name
        crop.resize((target_w, round(h * target_w / w)), Image.Resampling.LANCZOS).save(out, "WEBP", quality=68, method=6)
        print(f"  wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--logo", required=True, type=Path)
    parser.add_argument("--banner", required=True, type=Path)
    args = parser.parse_args()

    IMG.mkdir(parents=True, exist_ok=True)
    logo = Image.open(args.logo)
    banner = Image.open(args.banner)
    if logo.size != (2048, 2048) or banner.size != (3584, 1184):
        print(f"warning: unexpected source sizes logo={logo.size} banner={banner.size}; crops assume 2048x2048 and 3584x1184")

    print("emblem:")
    alpha = build_marks(logo)
    build_hero(logo)
    print("icons:")
    build_icons(logo, alpha)
    print("social:")
    build_og(banner)
    build_texture(banner)
    return 0


if __name__ == "__main__":
    sys.exit(main())
