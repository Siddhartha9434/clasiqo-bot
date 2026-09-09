"""
Agent 4 - Content Creator (caption half).
Writes an ORIGINAL caption based on the underlying facts of the story,
in your page's brand voice. Never copies another page's wording -
works from the analyzed one-line summary, not from any source's exact text.
"""
from config import BRAND_VOICE, MIN_IMPORTANCE_TO_POST
import db
import llm

SYSTEM_TEMPLATE = """{brand_voice}

You will be given facts about a Real Madrid news story. Write an Instagram caption
from scratch based on the facts. Do not reuse phrasing from any source text you
might see - write entirely in your own words and voice.

Respond ONLY with valid JSON matching:
{{
  "caption": "the full caption text including emojis and hashtags",
  "headline_short": "a short punchy headline, max 6 words, for overlay on an image"
}}"""


def generate_caption(item: dict) -> dict:
    system = SYSTEM_TEMPLATE.format(brand_voice=BRAND_VOICE)
    prompt = (
        f"Category: {item.get('category')}\n"
        f"Is rumour: {bool(item.get('is_rumour'))}\n"
        f"Facts: {item.get('summary')}\n"
        f"Headline reference (for context only, do not copy wording): {item.get('headline')}"
    )
    return llm.generate_json(prompt, system=system, temperature=0.8)


def process_analyzed_items():
    items = db.get_items_by_status("analyzed")
    if not items:
        print("[caption_gen] No analyzed items ready for captioning.")
        return

    for item in items:
        if (item.get("importance") or 0) < MIN_IMPORTANCE_TO_POST:
            db.update_item(item["id"], status="ignored")
            print(f"[caption_gen] Ignored (low importance): {item['headline']}")
            continue

        try:
            result = generate_caption(item)
        except Exception as e:
            print(f"[caption_gen] Failed on item {item['id']}: {e}")
            continue

        db.update_item(
            item["id"],
            status="captioned",
            caption=result.get("caption"),
        )
        # stash short headline for the image step by reusing the headline field
        # (original source headline no longer needed past this point)
        db.update_item(item["id"], headline=result.get("headline_short") or item["headline"])
        print(f"[caption_gen] Captioned: {item['id']} - {result.get('headline_short')}")


if __name__ == "__main__":
    db.init_db()
    process_analyzed_items()
