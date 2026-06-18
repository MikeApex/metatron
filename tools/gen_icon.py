"""
Generate Metatron app icon — Phoenician/early Hebrew mem.
Shape: three upward peaks (W) with a descending tail (like a y stem).
Renders at 512x512 then scales to all required Android mipmap sizes.
"""
from PIL import Image, ImageDraw
import os
from pathlib import Path

BG   = (210, 190, 155, 255)  # buff / aged parchment
INK  = (90, 50, 20, 255)    # dark burnt-umber brown

SIZES = {
    "mipmap-mdpi":    48,
    "mipmap-hdpi":    72,
    "mipmap-xhdpi":   96,
    "mipmap-xxhdpi":  144,
    "mipmap-xxxhdpi": 192,
}

RES = Path(__file__).parent.parent / "android/app/src/main/res"


def draw_mem(size: int) -> Image.Image:
    """Draw the mem glyph on a square canvas of `size` pixels."""
    img = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(img)

    p = size * 0.10          # padding
    lw = max(3, int(size * 0.085))  # stroke width

    # --- W part: three upward peaks, two valleys ---
    # x positions
    xl  = p                  # far left
    xp1 = size * 0.22        # peak 1
    xv1 = size * 0.38        # valley 1
    xp2 = size * 0.50        # peak 2 (centre)
    xv2 = size * 0.62        # valley 2
    xp3 = size * 0.78        # peak 3
    xr  = size - p           # far right

    # y positions
    y_peak   = p * 1.3       # tops of the three peaks
    y_valley = size * 0.44   # bottom of the W valleys
    y_base   = size * 0.44   # same level — W sits here

    # Tail: descends from centre valley, finishes near bottom
    y_tail   = size * 0.87

    # Draw the W as connected line segments
    w_pts = [
        (xl,  y_valley),
        (xp1, y_peak),
        (xv1, y_valley),
        (xp2, y_peak),
        (xv2, y_valley),
        (xp3, y_peak),
        (xr,  y_valley),
    ]
    for a, b in zip(w_pts, w_pts[1:]):
        draw.line([a, b], fill=INK, width=lw)

    # Draw the tail: vertical stroke from centre valley downward
    cx = size * 0.50
    draw.line([(cx, y_base), (cx, y_tail)], fill=INK, width=lw)

    # Round the line-cap ends with filled circles
    r = lw // 2
    for (x, y) in [w_pts[0], w_pts[-1], (cx, y_tail)]:
        draw.ellipse([x-r, y-r, x+r, y+r], fill=INK)

    return img


def main():
    master = draw_mem(512)

    for folder, px in SIZES.items():
        scaled = master.resize((px, px), Image.LANCZOS)
        for name in ("ic_launcher.png", "ic_launcher_round.png",
                     "ic_launcher_foreground.png"):
            dest = RES / folder / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            # foreground uses a transparent background for adaptive icons
            if name == "ic_launcher_foreground.png":
                fg = Image.new("RGBA", (px, px), (0, 0, 0, 0))
                glyph = draw_mem(px)
                fg.paste(glyph, (0, 0))
                fg.save(dest)
            else:
                scaled.save(dest)
        print(f"  {folder}: {px}px written")

    print("Done.")


if __name__ == "__main__":
    main()
