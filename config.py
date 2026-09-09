"""
Central config for the Madrid fan-page bot.
Edit RSS_FEEDS, BRAND_VOICE, and thresholds here.

SECRETS (API keys, tokens) are read from environment variables, not hardcoded
here, so this file is safe to commit to a public GitHub repo. Locally, put
them in a `.env` file (already gitignored) and load it, or export them in
your shell. In GitHub Actions, set them as repo Secrets - see README.md.
"""
import os

# --- News sources (RSS, all free, no API key needed) ---
RSS_FEEDS = [
    "https://as.com/rss/futbol/equipos/real_madrid.xml",
    "https://www.marca.com/rss/futbol/equipos/real-madrid.xml",
    "https://www.realmadrid.com/en-US/rss/all-news",
    "https://feeds.bbci.co.uk/sport/football/teams/real-madrid/rss.xml",
]

# --- Duplicate detection ---
# Cosine similarity above this = considered the same story
DUPLICATE_SIMILARITY_THRESHOLD = 0.78
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # small, fast, free (sentence-transformers)

# --- LLM backend ---
# Cloud (used automatically whenever GROQ_API_KEY is set, e.g. in GitHub Actions):
GROQ_MODEL = "llama-3.1-8b-instant"  # free tier on Groq; swap for another Groq model if you like
# Local fallback (used only when GROQ_API_KEY is NOT set, e.g. running on your own laptop):
OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_HOST = "http://localhost:11434"

# --- Brand voice for caption generation ---
BRAND_VOICE = """
You are the social media voice for a Real Madrid fan page on Instagram.
Style: short, energetic, passionate but not cringe. Use emojis sparingly (2-4 per post).
Always distinguish confirmed official news from rumours - never state a rumour as fact.
End posts with relevant hashtags (4-6 max), e.g. #RealMadrid #HalaMadrid plus player/topic specific tags.
Never copy wording from a source verbatim - always write in your own words.
"""

# --- Importance scoring thresholds ---
# Anything below this score is ignored / not posted
MIN_IMPORTANCE_TO_POST = 4  # scale 1-10

# Anything at/above this is flagged for instant posting; below queues for review
AUTO_POST_THRESHOLD = 8

# --- Database ---
DB_PATH = "madrid_bot.db"

# --- Image template ---
IMAGE_SIZE = (1080, 1080)
BRAND_NAME = "YOUR PAGE NAME"          # shown on generated graphic
LOGO_PATH = "assets/logo.png"           # optional, put your own logo here
FONT_PATH_BOLD = "assets/fonts/Inter-Bold.ttf"
FONT_PATH_REGULAR = "assets/fonts/Inter-Regular.ttf"

# --- Instagram Graph API ---
# Read from environment / GitHub Secrets - never hardcode real values here.
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IG_BUSINESS_ACCOUNT_ID = os.environ.get("IG_BUSINESS_ACCOUNT_ID", "")
IG_GRAPH_API_VERSION = "v21.0"

# --- Public image hosting for IG API (IG requires a public image URL, not a file upload) ---
# Free option used by this project: generated images are committed back to this
# GitHub repo by the Actions workflow, then served from raw.githubusercontent.com.
# Fill in PUBLIC_IMAGE_BASE_URL as an env var / secret, e.g.:
#   https://raw.githubusercontent.com/<you>/<repo>/main/generated_images/
PUBLIC_IMAGE_BASE_URL = os.environ.get("PUBLIC_IMAGE_BASE_URL", "")

# --- Auto-run behavior ---
# When true (set automatically in CI, see workflow), the pipeline also
# auto-publishes anything that clears AUTO_POST_THRESHOLD, with no human in
# the loop. Keep this False while you're still trusting the bot's judgement.
AUTO_PUBLISH = os.environ.get("AUTO_PUBLISH", "false").lower() == "true"
