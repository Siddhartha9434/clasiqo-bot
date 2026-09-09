"""
Approval / rules layer.
Decides whether an item auto-posts, gets queued for manual approval, or
is skipped. Strongly recommended to keep rumours and borderline-importance
items behind manual approval rather than letting the bot publish everything.
"""
from config import AUTO_POST_THRESHOLD
import db


def route_imaged_items():
    items = db.get_items_by_status("imaged")
    if not items:
        print("[approval] No imaged items to route.")
        return

    for item in items:
        importance = item.get("importance") or 0
        is_rumour = bool(item.get("is_rumour"))

        if is_rumour:
            db.update_item(item["id"], status="queued")
            print(f"[approval] Rumour -> manual review queue: {item['headline']}")
        elif importance >= AUTO_POST_THRESHOLD:
            db.update_item(item["id"], status="queued")  # publisher.py --auto will pick these up
            print(f"[approval] High importance ({importance}) -> auto-post queue: {item['headline']}")
        else:
            db.update_item(item["id"], status="queued")
            print(f"[approval] Normal -> review queue: {item['headline']}")


def list_pending():
    """Show everything sitting in the queue, for manual review via CLI."""
    items = db.get_items_by_status("queued")
    for item in items:
        print(f"\n--- #{item['id']} ---")
        print(f"Category: {item['category']} | Importance: {item['importance']} | Rumour: {bool(item['is_rumour'])}")
        print(f"Caption:\n{item['caption']}")
        print(f"Image: {item['image_path']}")
    return items


if __name__ == "__main__":
    db.init_db()
    route_imaged_items()
    print("\n=== Pending queue ===")
    list_pending()
