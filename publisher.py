"""
Agent 5 - Publisher.
Posts approved items to Instagram via the Graph API (free to use once your
Business/Creator account + app are approved for content publishing).

IMPORTANT: Instagram's API requires a PUBLICLY reachable image URL - it will
not accept a local file upload directly. Cheapest free option: commit
generated images to a public GitHub repo and reference the raw.githubusercontent.com
URL, or use any free static file host. Set PUBLIC_IMAGE_BASE_URL in config.py.

Usage:
  python publisher.py --auto     # posts only items with status 'queued' AND importance >= AUTO_POST_THRESHOLD
  python publisher.py --approve 12   # manually approve+post item id 12
  python publisher.py --list     # show what's pending
"""
import argparse
import requests

from config import (
    IG_ACCESS_TOKEN, IG_BUSINESS_ACCOUNT_ID, IG_GRAPH_API_VERSION,
    PUBLIC_IMAGE_BASE_URL, AUTO_POST_THRESHOLD,
)
import db

GRAPH_BASE = f"https://graph.facebook.com/{IG_GRAPH_API_VERSION}"


def _check_config():
    missing = [
        name for name, val in [
            ("IG_ACCESS_TOKEN", IG_ACCESS_TOKEN),
            ("IG_BUSINESS_ACCOUNT_ID", IG_BUSINESS_ACCOUNT_ID),
            ("PUBLIC_IMAGE_BASE_URL", PUBLIC_IMAGE_BASE_URL),
        ] if not val
    ]
    if missing:
        raise RuntimeError(
            f"Missing config values before you can post: {', '.join(missing)}. "
            f"Fill these in config.py once your Instagram Graph API access is approved."
        )


def publish_item(item: dict) -> str:
    """Create the media container, then publish it. Returns the IG post ID."""
    _check_config()

    image_filename = item["image_path"].split("/")[-1]
    public_url = PUBLIC_IMAGE_BASE_URL.rstrip("/") + "/" + image_filename

    # Step 1: create media container
    container_resp = requests.post(
        f"{GRAPH_BASE}/{IG_BUSINESS_ACCOUNT_ID}/media",
        data={
            "image_url": public_url,
            "caption": item["caption"],
            "access_token": IG_ACCESS_TOKEN,
        },
    )
    container_resp.raise_for_status()
    creation_id = container_resp.json()["id"]

    # Step 2: publish the container
    publish_resp = requests.post(
        f"{GRAPH_BASE}/{IG_BUSINESS_ACCOUNT_ID}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": IG_ACCESS_TOKEN,
        },
    )
    publish_resp.raise_for_status()
    post_id = publish_resp.json()["id"]
    return post_id


def run_auto():
    items = db.get_items_by_status("queued")
    to_post = [i for i in items if (i.get("importance") or 0) >= AUTO_POST_THRESHOLD and not i.get("is_rumour")]

    if not to_post:
        print("[publisher] Nothing meets the auto-post threshold right now.")
        return

    for item in to_post:
        try:
            post_id = publish_item(item)
        except Exception as e:
            print(f"[publisher] Failed to post item {item['id']}: {e}")
            continue
        db.update_item(item["id"], status="posted", instagram_post_id=post_id)
        print(f"[publisher] Posted item {item['id']} -> IG post {post_id}")


def run_approve(item_id: int):
    items = db.get_items_by_status("queued")
    match = next((i for i in items if i["id"] == item_id), None)
    if not match:
        print(f"[publisher] Item {item_id} not found in queue.")
        return
    try:
        post_id = publish_item(match)
    except Exception as e:
        print(f"[publisher] Failed to post item {item_id}: {e}")
        return
    db.update_item(item_id, status="posted", instagram_post_id=post_id)
    print(f"[publisher] Posted item {item_id} -> IG post {post_id}")


if __name__ == "__main__":
    db.init_db()
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="Post all items above the auto-post importance threshold")
    parser.add_argument("--approve", type=int, help="Manually approve and post a specific item ID")
    parser.add_argument("--list", action="store_true", help="List items pending review")
    args = parser.parse_args()

    if args.list:
        from approval import list_pending
        list_pending()
    elif args.approve:
        run_approve(args.approve)
    elif args.auto:
        run_auto()
    else:
        parser.print_help()
