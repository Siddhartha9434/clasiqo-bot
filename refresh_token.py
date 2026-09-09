"""
Long-lived Facebook Page access tokens (which is what powers Instagram Graph
API posting) last about 60 days, then stop working. Left alone, that would
silently break "fully automatic forever" two months in.

This script refreshes the token via Meta's token-exchange endpoint (free,
no extra approval needed - it's the same permission you already have) and,
if running in GitHub Actions with a GH_PAT secret available, writes the new
token straight back into the repo's IG_ACCESS_TOKEN secret using the GitHub
CLI. That closes the loop with zero manual steps.

Run this on a schedule well inside the 60-day window (the included workflow
runs it every 30 days) - see .github/workflows/refresh_token.yml.
"""
import os
import subprocess
import sys

import requests

from config import IG_ACCESS_TOKEN, IG_GRAPH_API_VERSION

GRAPH_BASE = f"https://graph.facebook.com/{IG_GRAPH_API_VERSION}"


def refresh(current_token: str) -> str:
    resp = requests.get(
        f"{GRAPH_BASE}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": os.environ.get("FB_APP_ID", ""),
            "client_secret": os.environ.get("FB_APP_SECRET", ""),
            "fb_exchange_token": current_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def update_github_secret(new_token: str):
    """Requires the `gh` CLI to be authenticated (GH_PAT env var with repo scope)."""
    subprocess.run(
        ["gh", "secret", "set", "IG_ACCESS_TOKEN", "--body", new_token],
        check=True,
    )
    print("[refresh_token] Updated IG_ACCESS_TOKEN GitHub secret.")


if __name__ == "__main__":
    if not IG_ACCESS_TOKEN:
        print("[refresh_token] No IG_ACCESS_TOKEN set yet - nothing to refresh. Skipping.")
        sys.exit(0)

    if not (os.environ.get("FB_APP_ID") and os.environ.get("FB_APP_SECRET")):
        print(
            "[refresh_token] FB_APP_ID / FB_APP_SECRET not set - can't refresh "
            "automatically. Add them as repo secrets (from your Meta developer "
            "app's Basic Settings page)."
        )
        sys.exit(1)

    try:
        new_token = refresh(IG_ACCESS_TOKEN)
    except Exception as e:
        print(f"[refresh_token] Refresh failed: {e}")
        sys.exit(1)

    print("[refresh_token] Got refreshed token.")

    if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GH_PAT"):
        update_github_secret(new_token)
    else:
        print(
            "[refresh_token] Not running in GitHub Actions with GH_PAT set - "
            f"here is your new token, update IG_ACCESS_TOKEN manually:\n{new_token}"
        )
