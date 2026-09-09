"""
Orchestrates the full pipeline, in order:
  1. Scout        - fetch new RSS items
  2. Dedupe        - embed + cluster, skip duplicates
  3. Analyzer      - categorize + score importance
  4. Caption Gen   - write original captions
  5. Image Gen     - render branded graphic cards
  6. Approval      - route to auto-post or review queue

Publishing is a separate manual/scripted step (see publisher.py) so you
always have a chance to sanity-check before anything goes live, especially
early on.

Run this on a schedule (cron, GitHub Actions, etc.) e.g. every 15-30 min.
"""
import db
import sources
import dedupe
import analyzer
import caption_gen
import image_gen
import approval
from config import AUTO_PUBLISH


def run_pipeline():
    db.init_db()

    print("\n=== 1. Scout: fetching sources ===")
    sources.fetch_new_items()

    print("\n=== 2. Dedupe: clustering stories ===")
    dedupe.process_new_items()

    print("\n=== 3. Analyzer: categorizing + scoring ===")
    analyzer.process_clustered_items()

    print("\n=== 4. Caption Gen: writing captions ===")
    caption_gen.process_analyzed_items()

    print("\n=== 5. Image Gen: rendering graphics ===")
    image_gen.process_captioned_items()

    print("\n=== 6. Approval: routing items ===")
    approval.route_imaged_items()

    if AUTO_PUBLISH:
        print("\n=== 7. Publisher: auto-posting cleared items (AUTO_PUBLISH=true) ===")
        import publisher
        publisher.run_auto()
    else:
        print("\nPipeline run complete. Review the queue with:")
        print("  python publisher.py --list")
        print("Then post manually with:")
        print("  python publisher.py --approve <id>")
        print("Or let high-importance confirmed news auto-post with:")
        print("  python publisher.py --auto")


if __name__ == "__main__":
    run_pipeline()
