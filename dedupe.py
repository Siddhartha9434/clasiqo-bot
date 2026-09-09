"""
Agent 3 - Duplicate Detector.
Uses sentence-transformers (free, runs locally, no API cost) to embed
headline+summary text and cluster items that describe the same story,
even when worded differently across sources.
"""
import json
import numpy as np
from sentence_transformers import SentenceTransformer

from config import DUPLICATE_SIMILARITY_THRESHOLD, EMBEDDING_MODEL
import db

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_text(text: str) -> np.ndarray:
    model = get_model()
    return model.encode(text, normalize_embeddings=True)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))  # vectors are normalized, so dot == cosine sim


def process_new_items():
    """
    For every 'new' item: compute embedding, compare against recent items
    that already have a cluster, and either attach to an existing cluster
    (marking as duplicate) or start a new cluster (marking as the one to post).
    """
    new_items = db.get_items_by_status("new")
    if not new_items:
        print("[dedupe] No new items to process.")
        return

    recent = db.get_recent_items(hours=72)
    # Build a lookup of clustered items with embeddings for comparison
    clustered = [r for r in recent if r["status"] not in ("new",) and r["embedding"]]

    for item in new_items:
        text = f"{item['headline']}. {item.get('summary') or ''}"
        emb = embed_text(text)

        match_cluster_id = None
        best_sim = 0.0

        for other in clustered:
            other_emb = np.array(json.loads(other["embedding"]))
            sim = cosine_sim(emb, other_emb)
            if sim > best_sim:
                best_sim = sim
            if sim >= DUPLICATE_SIMILARITY_THRESHOLD and other.get("cluster_id"):
                match_cluster_id = other["cluster_id"]
                break

        db.update_item(item["id"], embedding=json.dumps(emb.tolist()))

        if match_cluster_id:
            db.mark_duplicate(item["id"], match_cluster_id)
            print(f"[dedupe] DUPLICATE (sim={best_sim:.2f}): {item['headline']}")
        else:
            cluster_id = db.create_cluster(item["id"])
            db.update_item(item["id"], status="clustered", cluster_id=cluster_id)
            print(f"[dedupe] New story/cluster {cluster_id}: {item['headline']}")

            # Add to local "clustered" list so items later in this same batch
            # can be compared against it too
            item["cluster_id"] = cluster_id
            item["embedding"] = json.dumps(emb.tolist())
            item["status"] = "clustered"
            clustered.append(item)


if __name__ == "__main__":
    db.init_db()
    process_new_items()
