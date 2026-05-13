#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import argparse
import os
import sys

# Priority list for Japanese-capable fonts
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansJP-Bold.otf",
    "/usr/share/fonts/truetype/noto/NotoSansJP-Bold.otf",
]

def find_font(user_font=None):
    if user_font and os.path.exists(user_font):
        return user_font
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None

def fit_cover(img, width, height):
    src_w, src_h = img.size
    scale = max(width / src_w, height / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - width) // 2
    top = (new_h - height) // 2
    return img.crop((left, top, left + width, top + height))

def add_glow_text(base, text, font, y, fill, stroke_fill, stroke_width, glow_fill):
    # Glow layer
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    w, _ = base.size
    bbox = glow_draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw = bbox[2] - bbox[0]
    x = (w - tw) // 2

    glow_draw.text(
        (x, y),
        text,
        font=font,
        fill=glow_fill,
        stroke_width=stroke_width + 2,
        stroke_fill=glow_fill,
    )

    glow = glow.filter(ImageFilter.GaussianBlur(8))
    base.alpha_composite(glow)

    # Sharp text layer
    draw = ImageDraw.Draw(base)
    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )

def main():
    parser = argparse.ArgumentParser(description="Create vertical opening thumbnail")
    parser.add_argument("--input", required=True, help="Base image path")
    parser.add_argument("--output", required=True, help="Output thumbnail path")
    parser.add_argument("--title", default="天使のミク")
    parser.add_argument("--subtitle", default="光のメロディ")
    parser.add_argument("--font", default=None)
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=1280)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: input image not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    font_path = find_font(args.font)
    if not font_path:
        print("ERROR: Japanese-capable font not found. Please install Noto Sans CJK or specify path via --font", file=sys.stderr)
        sys.exit(1)

    img = Image.open(args.input).convert("RGBA")
    img = fit_cover(img, args.width, args.height)

    # Dark gradient at bottom for readability
    gradient = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(gradient)
    for y in range(args.height):
        if y > int(args.height * 0.58):
            alpha = int((y - args.height * 0.58) / (args.height * 0.42) * 150)
            gdraw.line([(0, y), (args.width, y)], fill=(0, 8, 20, min(alpha, 150)))
    img.alpha_composite(gradient)

    font_title = ImageFont.truetype(font_path, 76)
    font_sub = ImageFont.truetype(font_path, 48)

    add_glow_text(
        img,
        args.title,
        font_title,
        900,
        fill="#fffdf7",
        stroke_fill="#04101f",
        stroke_width=7,
        glow_fill=(90, 230, 255, 180),
    )

    add_glow_text(
        img,
        args.subtitle,
        font_sub,
        1002,
        fill="#fff2b0",
        stroke_fill="#04101f",
        stroke_width=5,
        glow_fill=(255, 220, 120, 150),
    )

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        
    img.convert("RGB").save(args.output, quality=95)
    print(f"Saved thumbnail: {args.output}")

if __name__ == "__main__":
    main()
