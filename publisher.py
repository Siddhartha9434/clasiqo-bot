"""
Agent 5 - Publisher.
Posts approved items to Instagram via the Graph API.

Your app uses Instagram Login (not Facebook Login), so this uses:
  - graph.instagram.com as the host (NOT graph.facebook.com)
  - an Instagram User access token
  - the instagram_business_content_publish permission

Usage:
  python publisher.py --auto             # posts items above the auto-post importance threshold
  python publisher.py --approve 12       # manually approve+post item id 12
  python publisher.py --list             # show what's pending
"""
import argparse
import os
import time
import requests

from config import IG_BUSINESS_ACCOUNT_ID, PUBLIC_IMAGE_BASE_URL, AUTO_POST_THRESHOLD
import db

# Read the token from the environment (GitHub Actions secret) rather than
# hardcoding it in config.py - keeps it out of source control.
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IG_BUSINESS_ACCOUNT_ID = os.environ.get("IG_BUSINESS_ACCOUNT_ID", IG_BUSINESS_ACCOUNT_ID)

GRAPH_API_VERSION = "v23.0"
GRAPH_BASE = f"https://graph.instagram.com/{GRAPH_API_VERSION}"

MAX_STATUS_CHECKS = 10
STATUS_CHECK_DELAY_SECONDS = 5


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
            f"Set them as GitHub secrets (IG_ACCESS_TOKEN, IG_BUSINESS_ACCOUNT_ID) "
            f"and PUBLIC_IMAGE_BASE_URL in config.py."
        )


def _wait_for_container_ready(creation_id: str):
    """Poll the container until Instagram finishes downloading/processing the image."""
    for attempt in range(MAX_STATUS_CHECKS):
        status_resp = requests.get(
            f"{GRAPH_BASE}/{creation_id}",
            params={"fields": "status_code,status", "access_token": IG_ACCESS_TOKEN},
        )
        if not status_resp.ok:
            print(f"[publisher] Status check error: {status_resp.text}")
            status_resp.raise_for_status()

        status_data = status_resp.json()
        status_code = status_data.get("status_code")
        print(f"[publisher] Container {creation_id} status: {status_code} (attempt {attempt + 1})")

        if status_code == "FINISHED":
            return
        if status_code == "ERROR":
            raise RuntimeError(f"Instagram container processing failed: {status_data}")

        time.sleep(STATUS_CHECK_DELAY_SECONDS)

    raise RuntimeError(
        f"Container {creation_id} did not finish processing after "
        f"{MAX_STATUS_CHECKS * STATUS_CHECK_DELAY_SECONDS}s. "
        f"Common cause: the image URL wasn't publicly reachable yet when "
        f"the container was created - check it hasn't been pushed to GitHub "
        f"yet, or that the repo/branch/path in PUBLIC_IMAGE_BASE_URL is correct."
    )


def publish_item(item: dict) -> str:
    """Create the media container, wait until it's ready, then publish it."""
    _check_config()

    image_filename = item["image_path"].split("/")[-1]
    public_url = PUBLIC_IMAGE_BASE_URL.rstrip("/") + "/" + image_filename

    # Sanity check: fail fast with a clear message if the image genuinely
    # isn't reachable yet, instead of burning through the status-poll loop.
    check = requests.head(public_url, timeout=10)
    if check.status_code != 200:
        raise RuntimeError(
            f"Image URL not reachable (HTTP {check.status_code}): {public_url}\n"
            f"Make sure this file has been committed AND pushed to GitHub "
            f"before this step runs."
        )

    # Step 1: create media container
    container_resp = requests.post(
        f"{GRAPH_BASE}/{IG_BUSINESS_ACCOUNT_ID}/media",
        data={
            "image_url": public_url,
            "caption": item["caption"],
            "access_token": IG_ACCESS_TOKEN,
        },
    )
    if not container_resp.ok:
        print(f"[publisher] Meta container error: {container_resp.text}")
        container_resp.raise_for_status()

    creation_id = container_resp.json()["id"]
    print(f"[publisher] Container created: {creation_id}")

    # Step 2: wait until Instagram has actually finished downloading/processing it
    _wait_for_container_ready(creation_id)

    # Step 3: publish
    publish_resp = requests.post(
        f"{GRAPH_BASE}/{IG_BUSINESS_ACCOUNT_ID}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": IG_ACCESS_TOKEN,
        },
    )
    if not publish_resp.ok:
        print(f"[publisher] Meta publish error: {publish_resp.text}")
        publish_resp.raise_for_status()

    return publish_resp.json()["id"]


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
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--approve", type=int)
    parser.add_argument("--list", action="store_true")
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
