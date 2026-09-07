"""
Generate tactical GIS icon for LANDSLIDENEI Windows Application
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw

def create_app_icon(output_path: Path):
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []

    for width, height in sizes:
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background rounded rectangle
        pad = max(1, width // 16)
        r = width // 6
        bg_color = (13, 27, 42, 255) # Deep navy/slate
        border_color = (0, 230, 118, 255) # Radar Emerald

        draw.rounded_rectangle(
            [pad, pad, width - pad, height - pad],
            radius=r,
            fill=bg_color,
            outline=border_color,
            width=max(1, width // 32)
        )

        # Mountain peak 1 (left)
        p1 = [(width * 0.2, height * 0.75), (width * 0.45, height * 0.35), (width * 0.7, height * 0.75)]
        # Mountain peak 2 (right)
        p2 = [(width * 0.4, height * 0.75), (width * 0.65, height * 0.45), (width * 0.85, height * 0.75)]

        draw.polygon(p1, fill=(26, 77, 62, 220), outline=(0, 230, 118, 240))
        draw.polygon(p2, fill=(35, 95, 120, 220), outline=(56, 189, 248, 240))

        # Radar pulse / warning dot
        dot_r = max(2, width // 14)
        dot_x, dot_y = width * 0.45, height * 0.35
        draw.ellipse(
            [dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r],
            fill=(255, 61, 0, 255), # Alert orange/red
            outline=(255, 255, 255, 255),
            width=max(1, width // 40)
        )

        # Crosshairs / GIS reticle lines
        cx, cy = width / 2, height / 2
        line_col = (56, 189, 248, 160)
        lw = max(1, width // 48)
        draw.line([(cx, pad * 2), (cx, pad * 4)], fill=line_col, width=lw)
        draw.line([(cx, height - pad * 4), (cx, height - pad * 2)], fill=line_col, width=lw)
        draw.line([(pad * 2, cy), (pad * 4, cy)], fill=line_col, width=lw)
        draw.line([(width - pad * 4, cy), (width - pad * 2, cy)], fill=line_col, width=lw)

        images.append(img)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        output_path,
        format="ICO",
        sizes=[img.size for img in images],
        append_images=images[1:]
    )
    print(f"Generated icon: {output_path}")

if __name__ == "__main__":
    icon_path = Path("C:/SIH Landslide/assets/icon.ico")
    create_app_icon(icon_path)
