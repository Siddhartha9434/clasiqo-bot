# Madrid Fan Page Bot (Free, Cloud-Automated Stack)

Automated pipeline: monitors free RSS news sources, detects duplicate stories
across sources, writes original captions in your brand voice, renders a
branded graphic card, and (optionally) auto-posts to Instagram - running
entirely on GitHub's servers, on a schedule, with your laptop off.

**This does not scrape, copy, or repost other Instagram fan pages.** It reads
news from official/press RSS feeds, generates its own text and its own
graphics. That keeps you clear of copyright and Instagram ToS issues that
copying-and-rewatermarking another page's content would create.

## How "laptop off, $0 forever" actually works

| Piece | Where it runs | Cost |
|---|---|---|
| Scheduling (every 30 min) | GitHub Actions | Free (unlimited minutes on a **public** repo) |
| RSS fetch + dedupe | GitHub Actions runner | Free |
| Analysis + captions (LLM) | Groq's hosted API | Free tier |
| Image rendering | GitHub Actions runner (Pillow) | Free |
| State (DB of posted items) | Committed back to this git repo | Free |
| Image hosting for Instagram | `raw.githubusercontent.com` | Free |
| Posting | Instagram Graph API | Free (once Meta approves your app) |
| Keeping the IG token alive | Monthly Actions job | Free |

Nothing in this list needs your computer to be on. Once it's set up, it
runs by itself indefinitely. The one honest caveat: every row above is a
*free tier* of someone else's product (GitHub, Groq, Meta). They're free
today and have no cost to you as configured, but no one can promise a
third party's free tier terms never change - if one ever does, you'd need
to swap that piece (e.g. a different free LLM API), not rebuild the bot.

## 1. Push this to a GitHub repo

Make it a **public** repo - that's what gets you unlimited free Actions
minutes. (Private repos get 2,000 free minutes/month, which the default
every-30-minutes schedule burns through in under two weeks. If you want the
repo private, edit the cron in `.github/workflows/run_pipeline.yml` to run
less often, e.g. `"0 * * * *"` for hourly.)

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

## 2. Get a free Groq API key (replaces local Ollama)

The original local-only version needed Ollama running on your machine 24/7 -
that's the opposite of "works while offline." Swap in Groq instead:

1. Sign up free at https://console.groq.com (no credit card).
2. Create an API key.
3. In your GitHub repo: **Settings -> Secrets and variables -> Actions ->
   New repository secret** -> name `GROQ_API_KEY`, paste the key.

That's it - `llm.py` automatically uses Groq whenever this secret is set
(and falls back to local Ollama if you ever run `python main.py` on your
own machine without it, for local testing).

## 3. Fonts / logo (optional but recommended)

- Drop TTF font files into `assets/fonts/` and point `FONT_PATH_BOLD` /
  `FONT_PATH_REGULAR` in `config.py` at them (e.g. Google Fonts, free).
- Drop your page's logo PNG at `assets/logo.png` (or update `LOGO_PATH`).
- Commit and push these - the workflow reads whatever's in the repo.

## 4. Configure `config.py`

- `RSS_FEEDS` - the included URLs are best-guesses; verify each one actually
  returns XML (`curl -sL "<url>" | head -c 500`) and fix any that don't.
- `BRAND_NAME` - your Instagram handle/page name for the watermark.
- `BRAND_VOICE` - describe your caption style.
- Importance thresholds if you want to tune what gets posted vs. queued.

Push any changes.

## 5. First test run (before Instagram is wired up)

Trigger it manually from GitHub: **Actions tab -> Run Madrid Bot Pipeline ->
Run workflow**. It'll fetch news, dedupe, analyze, caption, and render
images, then commit `madrid_bot.db` and `generated_images/` back to the
repo so you can look at the output - nothing gets posted anywhere yet
because Instagram isn't configured.

## 6. Instagram posting setup (the one part that needs Meta, not this bot)

You need, one time:

1. A Facebook Page linked to an Instagram **Business or Creator** account
   (free, done in the Instagram app).
2. A Meta developer app (https://developers.facebook.com/apps) with the
   `instagram_content_publish` permission - **this requires Meta's app
   review and can take days to weeks. Start this first**, everything else
   above can happen while you wait.
3. A long-lived Page access token and your IG Business Account ID.
4. Your Meta app's **App ID** and **App Secret** (Basic Settings page) -
   needed for automatic token refresh in step 7.

Add these as repo secrets (**Settings -> Secrets and variables -> Actions**):

| Secret name | Value |
|---|---|
| `IG_ACCESS_TOKEN` | your long-lived Page access token |
| `IG_BUSINESS_ACCOUNT_ID` | your Instagram Business Account ID |
| `PUBLIC_IMAGE_BASE_URL` | `https://raw.githubusercontent.com/<you>/<repo>/main/generated_images/` |
| `FB_APP_ID` | from your Meta app's Basic Settings |
| `FB_APP_SECRET` | from your Meta app's Basic Settings |

## 7. Keep the Instagram token alive automatically

Long-lived tokens expire after ~60 days. `.github/workflows/refresh_token.yml`
refreshes it every 30 days automatically - but writing the new token back
into your repo's secrets requires a GitHub personal access token (the
default workflow token isn't allowed to manage secrets):

1. Create a **fine-grained PAT** at https://github.com/settings/tokens with
   `Secrets` write access scoped to this repo (or a classic PAT with `repo`
   scope).
2. Add it as a repo secret named `GH_PAT`.

Once this is set, the token refresh is fully automatic - no more manual
re-authentication every couple of months.

## 8. Turn on auto-posting

By default the bot fetches, analyzes, and queues posts, but does **not**
publish anything without you - a sensible default while you're still
building trust in its judgement.

Once you've reviewed a few runs and are happy with the output, flip it on:
**Settings -> Secrets and variables -> Actions -> Variables tab -> New
repository variable** -> name `AUTO_PUBLISH`, value `true`.

From then on, anything that clears `AUTO_POST_THRESHOLD` in `config.py`
posts automatically, every 30 minutes, with your laptop off. Rumours always
stay queued for manual review regardless of this setting (see
`approval.py`) - real transfer speculation is exactly the kind of thing
you don't want a bot posting unsupervised.

To manually review/approve what's queued at any time:

```bash
python publisher.py --list
python publisher.py --approve 12
```

## Pipeline stages

```
sources.py    -> RSS scout, inserts new items
dedupe.py     -> embeds + clusters, marks duplicates
analyzer.py   -> categorizes, scores importance, flags rumours (via Groq)
caption_gen.py-> writes original captions in your voice (via Groq)
image_gen.py  -> renders branded graphic card (Pillow, no third-party photos)
approval.py   -> routes to auto-post / review queue
publisher.py  -> posts to Instagram via Graph API
```

All of it runs inside `.github/workflows/run_pipeline.yml`, on GitHub's
servers, every 30 minutes, forever, whether or not your computer exists.

## Local testing (optional)

You can still run it on your own machine to test changes before pushing:

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in values, then:
export $(cat .env | xargs)
python main.py
```

Without `GROQ_API_KEY` set, it'll try local Ollama instead (`ollama pull
llama3.1:8b`, `ollama serve`) - useful for testing without burning Groq
quota, but only works while your machine is on.

## Notes on scaling this up later

- Swap the Pillow template graphics for real photos once you have a licensed
  photo source (a paid sports-photo API, or your own photography) - just
  don't pull images from other Instagram accounts.
- If Groq's free tier ever isn't enough, `llm.py` is a thin wrapper - point
  it at any other OpenAI-compatible free/cheap API with a small edit.
