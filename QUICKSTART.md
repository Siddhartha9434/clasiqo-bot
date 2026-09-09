# Quick Start Checklist

Full explanations of every step are in README.md - this is just the ordered
checklist so nothing gets missed.

## 1. Verify your RSS feeds actually work
Feed URLs change. Test each one in `config.py`:
```bash
curl -sL "PASTE_FEED_URL_HERE" | head -c 500
```
You should see `<?xml` / `<rss` near the top. If not, find the real feed URL
(search "site.com RSS feed football" or check the site footer) and swap it in.

## 2. Push this repo to GitHub - make it **public**
Public = unlimited free Actions minutes for the every-30-min schedule.
Private works too, just widen the cron interval (see README.md).

## 3. Get a free Groq API key
https://console.groq.com -> create key -> add as repo secret `GROQ_API_KEY`.
This replaces local Ollama entirely, so the bot works with your laptop off.

## 4. Fonts + logo (optional, improves image quality)
Google Fonts "Inter" Bold/Regular TTFs into `assets/fonts/`, your logo PNG
into `assets/logo.png`. Commit and push.

## 5. Edit `config.py`
At minimum: `BRAND_NAME`, confirmed `RSS_FEEDS`, `BRAND_VOICE`. Push.

## 6. First test run
GitHub repo -> **Actions** tab -> "Run Madrid Bot Pipeline" -> **Run
workflow**. Check the committed `generated_images/` and `madrid_bot.db`
afterward to see what it produced. Nothing posts yet - Instagram isn't
wired up.

## 7. Instagram API access (start this in parallel - it's slow)
1. Convert your Instagram account to Business/Creator (free, in-app).
2. Create a Meta developer app: https://developers.facebook.com/apps
3. Request `instagram_content_publish` - requires Meta app review, days to
   weeks. Start immediately.
4. Once approved: get a long-lived Page access token, your IG Business
   Account ID, and your app's App ID + App Secret.
5. Add as repo secrets: `IG_ACCESS_TOKEN`, `IG_BUSINESS_ACCOUNT_ID`,
   `PUBLIC_IMAGE_BASE_URL`, `FB_APP_ID`, `FB_APP_SECRET`.

`PUBLIC_IMAGE_BASE_URL` =
`https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/generated_images/`

## 8. Automatic token refresh (so it never silently breaks in ~60 days)
Create a GitHub personal access token with secrets-write access to this
repo, add it as secret `GH_PAT`. `.github/workflows/refresh_token.yml`
handles the rest, monthly, automatically.

## 9. Turn on auto-posting
Repo **Settings -> Secrets and variables -> Actions -> Variables** -> new
variable `AUTO_PUBLISH` = `true`. From then on it posts unattended, every
30 minutes, forever. Until you do this, review manually with:
```bash
python publisher.py --list
python publisher.py --approve 3
```

---

Full details on every module and the "why" behind each step: see README.md
