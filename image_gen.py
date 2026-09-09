"""
Agent 4 - Content Creator (image half).
Builds an original branded graphic card for each post using Pillow.
Deliberately does NOT use any other page's or agency's photography -
sidesteps copyright/watermark-removal issues entirely by generating
a text/graphic-based template instead.

If you later want real match photos, use a licensed stock/sports-photo
API and swap the background image source in `render_card` - just don't
pull them from other Instagram accounts.
"""
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

from config import IMAGE_SIZE, BRAND_NAME, LOGO_PATH, FONT_PATH_BOLD, FONT_PATH_REGULAR
import db

OUTPUT_DIR = "generated_images"

CATEGORY_COLORS = {
    "transfer": (0, 61, 165),        # Real Madrid blue
    "player_news": (255, 255, 255),
    "match_result": (0, 0, 0),
    "match_preview": (30, 30, 30),
    "injury": (139, 0, 0),
    "club_news": (255, 255, 255),
    "rumour": (90, 90, 90),
    "official_announcement": (0, 61, 165),
    "opinion": (50, 50, 50),
    "other": (40, 40, 40),
}


def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except (OSError, IOError):
        # Fallback to default bitmap font if the TTF isn't present -
        # you should drop real font files into assets/fonts/ for good output
        return ImageFont.load_default()


def render_card(headline_short: str, category: str, is_rumour: bool, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    bg_color = CATEGORY_COLORS.get(category, (40, 40, 40))
    img = Image.new("RGB", IMAGE_SIZE, color=bg_color)
    draw = ImageDraw.Draw(img)

    w, h = IMAGE_SIZE
    font_headline = _load_font(FONT_PATH_BOLD, 72)
    font_tag = _load_font(FONT_PATH_REGULAR, 36)
    font_brand = _load_font(FONT_PATH_BOLD, 40)

    text_color = (255, 255, 255) if sum(bg_color) < 550 else (20, 20, 20)

    # Category tag top-left
    tag_text = ("RUMOUR" if is_rumour else category.replace("_", " ").upper())
    draw.text((60, 60), tag_text, font=font_tag, fill=text_color)

    # Headline, wrapped and centered vertically
    wrapped = textwrap.wrap(headline_short.upper(), width=16)
    total_h = len(wrapped) * 90
    start_y = (h - total_h) // 2
    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=font_headline)
        line_w = bbox[2] - bbox[0]
        x = (w - line_w) // 2
        draw.text((x, start_y + i * 90), line, font=font_headline, fill=text_color)

    # Brand watermark bottom-right
    draw.text((60, h - 100), BRAND_NAME, font=font_brand, fill=text_color)

    # Optional logo overlay
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo.thumbnail((120, 120))
        img.paste(logo, (w - logo.width - 60, h - logo.height - 60), logo)

    img.save(out_path, quality=95)
    return out_path


def process_captioned_items():
    items = db.get_items_by_status("captioned")
    if not items:
        print("[image_gen] No captioned items ready for image generation.")
        return

    for item in items:
        out_path = os.path.join(OUTPUT_DIR, f"{item['id']}.jpg")
        try:
            render_card(
                headline_short=item["headline"],
                category=item.get("category") or "other",
                is_rumour=bool(item.get("is_rumour")),
                out_path=out_path,
            )
        except Exception as e:
            print(f"[image_gen] Failed on item {item['id']}: {e}")
            continue

        db.update_item(item["id"], status="imaged", image_path=out_path)
        print(f"[image_gen] Rendered: {out_path}")


if __name__ == "__main__":
    db.init_db()
    process_captioned_items()
