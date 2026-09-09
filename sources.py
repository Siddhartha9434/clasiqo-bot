"""
Agent 1 - Scout.
Pulls new items from free RSS feeds (official club site, news outlets).
No scraping of other Instagram fan pages - keeps this on solid legal footing
and avoids Instagram ToS issues around scraping competitor accounts.
"""
import feedparser
from dateutil import parser as dateparser
from datetime import datetime, timezone

from config import RSS_FEEDS
import db


def fetch_new_items():
    """Fetch all feeds, insert any URLs not already in the DB, return the new rows."""
    new_items = []
    for feed_url in RSS_FEEDS:
        parsed = feedparser.parse(feed_url)
        if parsed.bozo and not parsed.entries:
            print(f"[sources] Warning: could not parse {feed_url}: {parsed.bozo_exception}")
            continue

        source_name = parsed.feed.get("title", feed_url)

        for entry in parsed.entries:
            url = entry.get("link")
            if not url or db.item_exists(url):
                continue

            headline = entry.get("title", "").strip()
            summary = entry.get("summary", "") or entry.get("description", "")
            summary = _strip_html(summary)

            published_raw = entry.get("published") or entry.get("updated")
            try:
                published_at = dateparser.parse(published_raw).isoformat() if published_raw else None
            except Exception:
                published_at = None

            item_id = db.insert_item(
                source=source_name,
                url=url,
                headline=headline,
                summary=summary,
                published_at=published_at,
            )
            if item_id:
                new_items.append(item_id)
                print(f"[sources] New: [{source_name}] {headline}")

    return new_items


def _strip_html(text):
    import re
    return re.sub(r"<[^>]+>", "", text or "").strip()


if __name__ == "__main__":
    db.init_db()
    found = fetch_new_items()
    print(f"\n{len(found)} new items fetched.")
