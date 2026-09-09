"""
Agent 2 - News Analyzer.
Classifies each clustered story: category, importance score, rumour vs confirmed.
"""
import db
import llm

SYSTEM_PROMPT = """You are a football news analyst for a Real Madrid fan page.
Given a headline and summary, classify the story. Respond ONLY with valid JSON,
no other text, matching exactly this schema:
{
  "category": one of ["transfer", "player_news", "match_result", "match_preview",
                       "injury", "club_news", "rumour", "official_announcement", "opinion", "other"],
  "importance": integer 1-10 (10 = major breaking news like a confirmed transfer or a big match result,
                 5 = normal squad/player update, 1 = trivial/low interest),
  "is_rumour": true or false,
  "key_players": [list of player names mentioned, empty list if none],
  "one_line_summary": "a neutral one-sentence summary of what happened, in your own words"
}"""


def analyze_item(item: dict) -> dict:
    prompt = f"Headline: {item['headline']}\nSummary: {item.get('summary') or '(none)'}"
    result = llm.generate_json(prompt, system=SYSTEM_PROMPT, temperature=0.2)
    return result


def process_clustered_items():
    items = db.get_items_by_status("clustered")
    if not items:
        print("[analyzer] No clustered items to analyze.")
        return

    for item in items:
        try:
            analysis = analyze_item(item)
        except Exception as e:
            print(f"[analyzer] Failed to analyze item {item['id']}: {e}")
            continue

        db.update_item(
            item["id"],
            status="analyzed",
            category=analysis.get("category", "other"),
            importance=int(analysis.get("importance", 1)),
            is_rumour=1 if analysis.get("is_rumour") else 0,
            summary=analysis.get("one_line_summary") or item.get("summary"),
        )
        print(f"[analyzer] {item['headline']} -> {analysis.get('category')} "
              f"(importance={analysis.get('importance')}, rumour={analysis.get('is_rumour')})")


if __name__ == "__main__":
    db.init_db()
    process_clustered_items()
