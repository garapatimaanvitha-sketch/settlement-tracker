# The Settlement Docket — setup (all free, ~20 minutes)

## What you're setting up
A static site hosted free on GitHub Pages, that checks a couple of free
RSS feeds once a day (via GitHub's free scheduler) and auto-drafts new
case-file posts using Google's free-tier Gemini API — no credit card,
no hosting bill, no server to maintain.

## Steps

**1. Create the GitHub repo (5 min)**
- Create a free GitHub account if you don't have one.
- Create a new **public** repository (public = free unlimited Actions minutes).
- Upload everything in this folder to that repo (drag-and-drop on
  github.com works, or `git push` if you're comfortable with git).

**2. Turn on GitHub Pages (2 min)**
- In the repo: Settings → Pages → Source: "Deploy from a branch" →
  branch `main`, folder `/ (root)` → Save.
- Your site goes live at `https://<your-username>.github.io/<repo-name>/`
  within a few minutes. This is your $0 blog URL.

**3. Get a free Gemini API key (3 min)**
- Go to https://aistudio.google.com/app/apikey → "Create API key."
  No credit card required for the free tier.
- ⚠️ Free-tier prompts may be used by Google to improve their models.
  Since this pipeline only ever sends public news headlines/snippets
  (never your personal data), that's an acceptable trade-off here —
  just don't repurpose this exact key for anything sensitive.

**4. Add your secrets (3 min)**
In the repo: Settings → Secrets and variables → Actions → New repository secret.
Add:
- `GEMINI_API_KEY` — the key from step 3.
- `ALERT_RSS_URL_1` — a Google Alerts RSS feed URL (see below).
- `ALERT_RSS_URL_2` — optional, a second feed.

**Getting a Google Alerts RSS URL (free):**
- Go to google.com/alerts, sign in.
- Create an alert for `"Canada class action settlement"`.
- Click the alert's settings (gear icon) → "Deliver to: RSS feed."
- Copy that RSS URL into `ALERT_RSS_URL_1`.
- Repeat with a second alert like `"claims administrator Canada"` for `ALERT_RSS_URL_2`.

**5. Test it manually (2 min)**
- Repo → Actions tab → "Daily settlement check" → "Run workflow" →
  confirm. Watch it run; check the logs if anything fails.
- If it succeeds, you'll see a new commit adding a post, and your live
  site updates automatically within a minute or two.

From here it runs itself once a day, no further action needed — until
you're ready to check step "What still needs you," below.

## What still needs you (be honest with yourself about this)
- **Spot-check new posts weekly**, at minimum. The script is instructed
  to write "not specified in source — verify directly" rather than
  guess at a dollar figure or deadline, but AI mistakes happen. A wrong
  deadline on a legal claim site is the one failure mode that actively
  hurts your readers and your credibility — this is the single biggest
  reason not to treat this as fully hands-off.
- **Distribution is manual for now.** Free social APIs (X/LinkedIn) are
  heavily rate-limited or paid-only at real posting volumes. Sharing
  new case files to LinkedIn/Reddit/relevant Facebook groups yourself
  is what actually drives traffic — the blog won't go viral on its own.
- **Custom domain is optional, not free** (~$10–15/year if you want
  settlementdocket.ca instead of the github.io URL). Skip this until
  you have traffic worth the cost.

## Cost summary
| Component | Cost |
|---|---|
| Hosting (GitHub Pages) | $0 |
| Scheduler (GitHub Actions) | $0 (public repo) |
| Writer model (Gemini API free tier) | $0 (rate-limited) |
| Domain | $0 (using github.io subdomain) |
| **Total** | **$0** |
