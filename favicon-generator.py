#!/usr/bin/env python3
"""
Generate favicons and PWA icons from a single SVG or PNG source.

Copyright 2025 Sean Whalen

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Layout (MDN-aligned):
static/
  site.webmanifest               # unless --no-manifest
  browserconfig.xml              # only if --make-browserconfig
  icons/
    favicon.svg                  # only if source was SVG (copied)
    favicon.ico                  # unless --no-ico
    favicon-<NxN>.png            # from --favicon-sizes (default: 16,32,48,256)
    apple-touch-icon.png         # unless --no-apple-touch
    icon-192x192.png
    icon-256x256.png             # (tight, non-maskable)
    icon-512x512.png
    icon-maskable-512x512.png    # unless --no-maskable
    safari-pinned-tab.svg        # only if --pinned-svg provided
"""

from __future__ import annotations

import argparse
import json
from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Tuple

from PIL import Image


# ---------- Core helpers ----------
def load_source_image(src: Path) -> tuple[Image.Image, bool]:
    """Return (Pillow image, is_svg_input)."""
    ext = src.suffix.lower()
    if ext == ".svg":
        try:
            import cairosvg  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(
                "SVG input requires cairosvg. Install with: pip install cairosvg"
            ) from exc
        png_bytes = cairosvg.svg2png(
            url=str(src), output_width=1024, output_height=1024
        )
        img = Image.open(BytesIO(png_bytes)).convert("RGBA")
        return img, True
    img = Image.open(src)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img, False


def ensure_outdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def contain(img: Image.Image, box: Tuple[int, int]) -> Image.Image:
    w, h = img.size
    bw, bh = box
    scale = min(bw / w, bh / h)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    return img.copy().resize((nw, nh), Image.LANCZOS) # pyright: ignore[reportAttributeAccessIssue]


def center(inner: Tuple[int, int], outer: Tuple[int, int]) -> Tuple[int, int]:
    ix, iy = inner
    ox, oy = outer
    return (ox - ix) // 2, (oy - iy) // 2


def trim_alpha(img: Image.Image) -> Image.Image:
    """Crop transparent gutters (helps Windows taskbar sizing)."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    bbox = img.split()[-1].getbbox()
    return img.crop(bbox) if bbox else img


# ---------- Icon writers ----------
def save_png(img: Image.Image, path: Path, size: Tuple[int, int]) -> None:
    out = img.copy().resize(size, Image.LANCZOS) # pyright: ignore[reportAttributeAccessIssue]
    out.save(path, format="PNG", optimize=True)


def save_apple_touch(img: Image.Image, path: Path, bg_hex: str) -> None:
    size = (180, 180)
    base = Image.new("RGB", size, bg_hex)
    icon = contain(img, size)
    base.paste(icon, center(icon.size, size), mask=icon.split()[-1])
    base.save(path, format="PNG", optimize=True)


def save_maskable(
    img: Image.Image, path: Path, size: int = 512, pad: float = 0.12
) -> None:
    pad = max(0.0, min(0.3, pad))
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner = int(round(size * (1 - 2 * pad)))
    icon = contain(img, (inner, inner))
    base.paste(icon, center(icon.size, base.size), mask=icon.split()[-1])
    base.save(path, format="PNG", optimize=True)


def save_ico(img: Image.Image, path: Path, sizes: Iterable[int]) -> None:
    base = contain(img, (max(sizes), max(sizes))).convert("RGBA")
    base.save(path, format="ICO", sizes=[(s, s) for s in sorted(sizes)])


# ---------- Metadata writers ----------
def write_manifest(
    outdir: Path,
    theme: str,
    bg: str,
    name: str,
    short: str,
    include_maskable: bool = True,
) -> None:
    # Order matters for some UAs (Windows/Edge): list tight, non-maskable first.
    icons = [
        {"src": "icons/icon-512x512.png", "sizes": "512x512", "type": "image/png"},
        {"src": "icons/icon-256x256.png", "sizes": "256x256", "type": "image/png"},
        {"src": "icons/icon-192x192.png", "sizes": "192x192", "type": "image/png"},
    ]
    if include_maskable:
        icons.append(
            {
                "src": "icons/icon-maskable-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            }
        )
    data = {
        "name": name,
        "short_name": short,
        "icons": icons,
        "theme_color": theme,
        "background_color": bg,
        "display": "standalone",
        "scope": "/",
        "start_url": "/",
    }
    (outdir / "site.webmanifest").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def write_browserconfig(outdir: Path, tile_color: str) -> None:
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<browserconfig>
  <msapplication>
    <tile>
      <square150x150logo src="icons/mstile-150x150.png"/>
      <TileColor>{tile_color}</TileColor>
    </tile>
  </msapplication>
</browserconfig>
"""
    (outdir / "browserconfig.xml").write_text(xml, encoding="utf-8")


# ---------- Parsing helpers ----------
def parse_sizes(csv: str) -> List[int]:
    try:
        sizes = sorted({int(s.strip()) for s in csv.split(",") if s.strip()})
    except ValueError as exc:  # noqa: BLE001
        raise SystemExit(
            "--favicon-sizes must be a comma-separated list of integers"
        ) from exc
    if not sizes:
        raise SystemExit("At least one size must be provided for --favicon-sizes")
    return sizes


# ---------- Main ----------
def main() -> None:
    p = argparse.ArgumentParser(description="Generate favicon and PWA icons.")
    p.add_argument("source", type=Path, help="Source SVG or PNG.")
    p.add_argument("--icons-dir", type=Path, default=Path("static/icons"))
    p.add_argument("--manifest-dir", type=Path, default=Path("static"))
    p.add_argument("--pwa-theme", default="#ffffff", help="Theme color for PWA meta.")
    p.add_argument("--pwa-bg", default="#ffffff", help="Background color for PWA meta.")
    p.add_argument("--pwa-name", default="My App", help="Full PWA name.")
    p.add_argument("--pwa-short-name", default="App", help="Short PWA name.")
    p.add_argument("--maskable-padding", type=float, default=0.12)
    p.add_argument("--pinned-svg", type=Path, default=None)
    p.add_argument(
        "--safari-pinned-color",
        default="#5bbad5",
        help="Color for <link rel='mask-icon'>; only if --pinned-svg is provided.",
    )
    p.add_argument("--make-browserconfig", action="store_true")
    p.add_argument("--no-ico", action="store_true", help="Skip generating favicon.ico.")
    p.add_argument(
        "--no-apple-touch", action="store_true", help="Skip apple-touch-icon.png."
    )
    p.add_argument(
        "--no-maskable",
        action="store_true",
        help="Skip maskable icon and manifest entry.",
    )
    p.add_argument(
        "--no-manifest",
        action="store_true",
        help="Skip writing site.webmanifest and omit its <link>.",
    )
    p.add_argument(
        "--autotrim",
        action="store_true",
        help="Trim transparent margins before all resizes.",
    )
    p.add_argument(
        "--favicon-sizes",
        default="16,32,48,256",
        help="Comma-separated PNG favicon sizes (e.g., 16,32,48,96,128,256).",
    )
    p.add_argument("--flask", action="store_true", help="Output Flask/Jinja paths.")
    p.add_argument(
        "--public-prefix",
        default="/static/",
        help="Base URL prefix for HTML snippet (ignored with --flask). Example: /assets/",
    )
    args = p.parse_args()

    ensure_outdir(args.icons_dir)
    ensure_outdir(args.manifest_dir)

    img, is_svg_input = load_source_image(args.source)
    if args.autotrim:
        img = trim_alpha(img)

    # If the source is SVG, also copy it as icons/favicon.svg
    if is_svg_input:
        (args.icons_dir / "favicon.svg").write_bytes(args.source.read_bytes())

    favicon_sizes = parse_sizes(args.favicon_sizes)

    # Core PNG favicons
    for s in favicon_sizes:
        save_png(img, args.icons_dir / f"favicon-{s}x{s}.png", (s, s))

    # Apple touch (optional)
    if not args.no_apple_touch:
        save_apple_touch(img, args.icons_dir / "apple-touch-icon.png", args.pwa_bg)

    # PWA primary icons (tight, non-maskable)
    save_png(img, args.icons_dir / "icon-192x192.png", (192, 192))
    save_png(img, args.icons_dir / "icon-256x256.png", (256, 256))
    save_png(img, args.icons_dir / "icon-512x512.png", (512, 512))

    # Maskable icon (optional)
    if not args.no_maskable:
        save_maskable(
            img,
            args.icons_dir / "icon-maskable-512x512.png",
            512,
            args.maskable_padding,
        )

    # ICO (optional)
    if not args.no_ico:
        ico_sizes = [s for s in favicon_sizes if s in (16, 24, 32, 48, 64)]
        if not ico_sizes:
            ico_sizes = [16, 32, 48]
        save_ico(img, args.icons_dir / "favicon.ico", ico_sizes)

    # Optional pinned SVG
    if args.pinned_svg:
        (args.icons_dir / "safari-pinned-tab.svg").write_bytes(
            args.pinned_svg.read_bytes()
        )

    # Optional Microsoft tiles/browserconfig
    if args.make_browserconfig:
        save_png(img, args.icons_dir / "mstile-150x150.png", (150, 150))
        write_browserconfig(args.manifest_dir, args.pwa_theme)

    # Manifest (relative icon paths from the manifest location)
    if not args.no_manifest:
        write_manifest(
            args.manifest_dir,
            args.pwa_theme,
            args.pwa_bg,
            args.pwa_name,
            args.pwa_short_name,
            include_maskable=not args.no_maskable,
        )

    # ---------- HTML output ----------
    def normalize_prefix(prefix: str) -> str:
        if not prefix:
            return "/"
        prefix = prefix.replace("\\", "/")
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        return prefix.rstrip("/") + "/"

    if args.flask:
        base = "{{ url_for('static', filename='"
    
        def _fmt_flask(f):
            return base + f + "') }}"
    
        fmt = _fmt_flask
    
    else:
        prefix = normalize_prefix(args.public_prefix)
    
        def _fmt_hosted(f):
            return f"{prefix}{f}"
    
        fmt = _fmt_hosted

    lines: list[str] = []
    lines.append("<!-- === FAVICONS & PWA ICONS === -->")

    # Include SVG link only if input was SVG
    if is_svg_input:
        lines.append(
            f'<link rel="icon" href="{fmt("icons/favicon.svg")}" type="image/svg+xml">'
        )

    # PNG favicon links for exactly the sizes generated
    for s in favicon_sizes:
        lines.append(
            f'<link rel="icon" type="image/png" sizes="{s}x{s}" href="{fmt(f"icons/favicon-{s}x{s}.png")}">'
        )

    # Apple touch (only if generated)
    if not args.no_apple_touch:
        lines.append(
            f'<link rel="apple-touch-icon" sizes="180x180" href="{fmt("icons/apple-touch-icon.png")}">'
        )

    # Safari pinned tab only if provided (use configured color)
    if args.pinned_svg:
        lines.append(
            f'<link rel="mask-icon" href="{fmt("icons/safari-pinned-tab.svg")}" color="{args.safari_pinned_color}">'
        )

    # Manifest link (only if generated)
    if not args.no_manifest:
        lines.append(f'<link rel="manifest" href="{fmt("site.webmanifest")}">')

    # Theme/background (useful even without a manifest)
    lines.append(f'<meta name="theme-color" content="{args.pwa_theme}">')
    lines.append(f'<meta name="background-color" content="{args.pwa_bg}">')

    # msapplication-config only if browserconfig was generated
    if args.make_browserconfig:
        lines.append(
            f'<meta name="msapplication-TileColor" content="{args.pwa_theme}">'
        )
        lines.append(
            f'<meta name="msapplication-config" content="{fmt("browserconfig.xml")}">'
        )

    # Legacy ICO link only if generated
    if not args.no_ico:
        lines.append(
            f'<link rel="alternate icon" href="{fmt("icons/favicon.ico")}" type="image/x-icon">'
        )

    lines.append("<!-- === END FAVICONS & PWA ICONS === -->")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
