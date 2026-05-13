from PIL import Image, ImageDraw, ImageFont
import os

def add_text_to_image(input_path, output_path, text1, text2, font_path):
    img = Image.open(input_path)
    draw = ImageDraw.Draw(img)
    
    # Font sizes
    size1 = 72
    size2 = 46
    
    # Load fonts
    font1 = ImageFont.truetype(font_path, size1)
    font2 = ImageFont.truetype(font_path, size2)
    
    # Colors
    color1 = "white"
    color2 = "#fff2b0"
    border_color = "#04101f"
    shadow_color = "#5ee7ff"
    
    def draw_text_with_outline(draw, position, text, font, fill_color, outline_color, outline_width):
        x, y = position
        # Draw outline
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        # Draw main text
        draw.text((x, y), text, font=font, fill=fill_color)

    # Calculate positions
    w, h = img.size
    
    # Text 1
    bbox1 = draw.textbbox((0, 0), text1, font=font1)
    tw1 = bbox1[2] - bbox1[0]
    pos1 = ((w - tw1) // 2, 940)
    
    # Text 2
    bbox2 = draw.textbbox((0, 0), text2, font=font2)
    tw2 = bbox2[2] - bbox2[0]
    pos2 = ((w - tw2) // 2, 1030)
    
    # Draw
    draw_text_with_outline(draw, pos1, text1, font1, color1, border_color, 6)
    draw_text_with_outline(draw, pos2, text2, font2, color2, border_color, 4)
    
    img.save(output_path)
    print(f"Saved thumbnail to {output_path}")

if __name__ == "__main__":
    input_img = "projects/pixar_angel_miku_mv/assets/opening_thumbnail_base.png"
    output_img = "projects/pixar_angel_miku_mv/assets/opening_thumbnail.png"
    font_p = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
    
    add_text_to_image(input_img, output_img, "天使のミク", "光のメロディ", font_p)
