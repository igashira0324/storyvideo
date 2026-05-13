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

def add_glow_text(base, text, font, position, fill, stroke_fill, stroke_width, glow_fill, glow_radius=8, align="center"):
    # Glow layer
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    w, _ = base.size
    bbox = glow_draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw = bbox[2] - bbox[0]
    
    if align == "center":
        x = (w - tw) // 2
    elif align == "left":
        x = position[0]
    else: # right
        x = w - tw - position[0]
    
    y = position[1]

    glow_draw.text(
        (x, y),
        text,
        font=font,
        fill=glow_fill,
        stroke_width=stroke_width + 2,
        stroke_fill=glow_fill,
    )

    glow = glow.filter(ImageFilter.GaussianBlur(glow_radius))
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

def draw_badge(img, text, font, pos, color=(255, 95, 210, 255)):
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    padding = 15
    rect = [pos[0], pos[1], pos[0] + tw + padding*2, pos[1] + th + padding*2]
    
    # Draw rounded rect
    draw.rounded_rectangle(rect, radius=10, fill=color, outline="white", width=3)
    draw.text((pos[0] + padding, pos[1] + padding - 5), text, font=font, fill="white")

def main():
    parser = argparse.ArgumentParser(description="Create vertical opening thumbnail")
    parser.add_argument("--input", required=True, help="Base image path")
    parser.add_argument("--output", required=True, help="Output thumbnail path")
    parser.add_argument("--title", default="天使ミク")
    parser.add_argument("--subtitle", default="COMIKET COSPLAY")
    parser.add_argument("--kicker", default="COMIKET COSPLAY")
    parser.add_argument("--location", default="AKIHABARA -> TOKYO BIG SIGHT")
    parser.add_argument("--font", default=None)
    parser.add_argument("--style", default="comiket_poster", choices=["classic", "comiket_poster"])
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=1280)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: input image not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    font_path = find_font(args.font)
    if not font_path:
        print("ERROR: Japanese-capable font not found.", file=sys.stderr)
        sys.exit(1)

    img = Image.open(args.input).convert("RGBA")
    img = fit_cover(img, args.width, args.height)

    # 1. Subtle central glow (Rim light feel)
    glow_rim = Image.new("RGBA", img.size, (0, 0, 0, 0))
    g_rim = ImageDraw.Draw(glow_rim)
    g_rim.ellipse((100, 150, 620, 800), fill=(120, 240, 255, 45))
    glow_rim = glow_rim.filter(ImageFilter.GaussianBlur(60))
    img.alpha_composite(glow_rim)

    # 2. Dark gradient at bottom for readability
    gradient = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(gradient)
    for y in range(args.height):
        if y > int(args.height * 0.4):
            alpha = int((y - args.height * 0.4) / (args.height * 0.6) * 180)
            gdraw.line([(0, y), (args.width, y)], fill=(0, 8, 24, min(alpha, 180)))
    img.alpha_composite(gradient)

    if args.style == "comiket_poster":
        # 3. Diagonal Neon Band (Backing for title)
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        # Left-bottom to right-top band
        odraw.polygon(
            [(-40, 920), (760, 830), (760, 1030), (-40, 1120)],
            fill=(0, 220, 255, 45)
        )
        # Accent magenta line
        odraw.line([(60, 1045), (660, 1005)], fill=(255, 95, 210, 180), width=6)
        img.alpha_composite(overlay)

        # Fonts
        font_kicker = ImageFont.truetype(font_path, 40)
        font_title = ImageFont.truetype(font_path, 108)
        font_sub = ImageFont.truetype(font_path, 48)
        font_badge = ImageFont.truetype(font_path, 34)
        font_loc = ImageFont.truetype(font_path, 26)

        # 1. Kicker (Top of title)
        add_glow_text(img, args.kicker, font_kicker, (0, 820), "#ffe9a8", "#061426", 4, (255, 233, 168, 120))

        # 2. Title (Main)
        add_glow_text(img, args.title, font_title, (0, 880), "#fffdf7", "#061426", 9, (85, 231, 255, 200), glow_radius=14)

        # 3. Subtitle (Action)
        add_glow_text(img, args.subtitle, font_sub, (0, 1020), "#ff5fd2", "#061426", 5, (255, 95, 210, 140))

        # 4. Location (Bottom)
        add_glow_text(img, args.location, font_loc, (0, 1180), "#88ccff", "#000000", 2, (0, 0, 0, 0))

        # 5. Badge (Top Right)
        draw_badge(img, "C104", font_badge, (560, 50))
        draw_badge(img, "TOKYO", font_badge, (540, 130), color=(0, 120, 255, 255))

    else: # classic
        font_title = ImageFont.truetype(font_path, 76)
        font_sub = ImageFont.truetype(font_path, 48)
        add_glow_text(img, args.title, font_title, (0, 900), "#fffdf7", "#04101f", 7, (90, 230, 255, 180))
        add_glow_text(img, args.subtitle, font_sub, (0, 1002), "#fff2b0", "#04101f", 5, (255, 220, 120, 150))

    # Path Safety Guard
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        
    img.convert("RGB").save(args.output, quality=95)
    print(f"Saved thumbnail: {args.output}")

if __name__ == "__main__":
    main()
