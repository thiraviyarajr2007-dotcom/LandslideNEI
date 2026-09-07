"""
Generate Tactical GIS PNG Icons for LandslideNEI Chrome/Edge Browser Extension
=============================================================================
Generates icon16.png, icon32.png, icon48.png, and icon128.png into extension/icons/
"""
from pathlib import Path
from PIL import Image, ImageDraw


def create_extension_icons():
    icons_dir = Path(__file__).resolve().parents[1] / "extension" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    sizes = [16, 32, 48, 128]

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        pad = max(1, size // 16)
        r = max(2, size // 6)
        bg_color = (13, 27, 42, 255)       # Deep obsidian navy
        border_color = (0, 230, 118, 255)   # Emerald radar neon

        # Outer rounded tile
        draw.rounded_rectangle(
            [pad, pad, size - pad, size - pad],
            radius=r,
            fill=bg_color,
            outline=border_color,
            width=max(1, size // 24)
        )

        # Mountain peak left
        p1 = [
            (size * 0.18, size * 0.78),
            (size * 0.44, size * 0.32),
            (size * 0.72, size * 0.78)
        ]
        # Mountain peak right
        p2 = [
            (size * 0.40, size * 0.78),
            (size * 0.66, size * 0.44),
            (size * 0.86, size * 0.78)
        ]

        draw.polygon(p1, fill=(26, 77, 62, 230), outline=(0, 230, 118, 240))
        draw.polygon(p2, fill=(35, 95, 120, 230), outline=(56, 189, 248, 240))

        # Radar warning beacon dot
        dot_r = max(1, size // 12)
        dot_x, dot_y = size * 0.44, size * 0.32
        draw.ellipse(
            [dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r],
            fill=(255, 61, 0, 255),
            outline=(255, 255, 255, 255),
            width=max(1, size // 36)
        )

        # Crosshairs for larger icons
        if size >= 32:
            cx, cy = size / 2, size / 2
            line_col = (56, 189, 248, 160)
            lw = max(1, size // 48)
            draw.line([(cx, pad * 2), (cx, pad * 3.5)], fill=line_col, width=lw)
            draw.line([(cx, size - pad * 3.5), (cx, size - pad * 2)], fill=line_col, width=lw)
            draw.line([(pad * 2, cy), (pad * 3.5, cy)], fill=line_col, width=lw)
            draw.line([(size - pad * 3.5, cy), (size - pad * 2, cy)], fill=line_col, width=lw)

        out_path = icons_dir / f"icon{size}.png"
        img.save(out_path, format="PNG")
        print(f"Generated {out_path} ({size}x{size})")


if __name__ == "__main__":
    create_extension_icons()
