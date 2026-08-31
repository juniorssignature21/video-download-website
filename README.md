# ClipGrab

A small Django app for downloading videos from social platforms (Facebook,
Instagram, TikTok, X/Twitter, YouTube, Vimeo, Reddit, ...) by pasting a
link. Built on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Features

- Paste a link (or use the **Paste** button) to fetch title, thumbnail and
  available qualities before downloading.
- Best-effort clipboard detection: on load, on tab focus, and on
  visibility change, the page checks the clipboard and surfaces a banner
  offering to use a detected video link. Browsers require clipboard-read
  permission for this, so it degrades gracefully to the **Paste** button
  and normal paste-into-the-input flow when permission isn't granted.
- Streams the downloaded file straight back to the browser; no accounts,
  no stored history.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DJANGO_DEBUG=True
python manage.py migrate
python manage.py runserver
```

Then open http://127.0.0.1:8000/.

Optional: install [ffmpeg](https://ffmpeg.org/) and make sure it's on your
`PATH` to get MP3 conversion for the "Audio only" option; without it,
audio downloads are served in their original container format.

## Configuration

Environment variables (all optional except `DJANGO_SECRET_KEY` in
production):

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | dev key | Set a real secret key in production |
| `DJANGO_DEBUG` | `False` | Set to `True` for local development |
| `DJANGO_ALLOWED_HOSTS` | none (`*` if `DEBUG=True`) | Comma-separated allowed hosts |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | none | Comma-separated origins, e.g. `https://example.com` |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` on Railway, else `False` | Force HTTP→HTTPS redirects |
| `DATABASE_URL` | none (uses SQLite) | Postgres URL — set automatically if you attach Railway's Postgres plugin |
| `DOWNLOAD_TMP_DIR` | system temp dir | Where in-progress downloads are staged |
| `MAX_DOWNLOAD_MB` | `500` | Per-download size cap |

## Deploying to Railway

The repo already includes `railway.json` (build/start commands) and
`nixpacks.toml` (installs `ffmpeg` at build time and runs
`collectstatic`), plus `whitenoise` for serving static files and
`gunicorn` as the app server — no extra Railway configuration is needed
beyond environment variables.

1. In the Railway dashboard: **New Project → Deploy from GitHub repo**,
   pick this repository, and set the deploy branch to `main` (Settings →
   Source → Branch).
2. Add environment variables on the service (Variables tab):
   - `DJANGO_SECRET_KEY` — generate one, e.g.
     `python -c "import secrets; print(secrets.token_urlsafe(50))"`
   - `DJANGO_DEBUG=False` (or omit — this is already the default)
   - Optional: `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` if
     you attach a custom domain (Railway's own `*.up.railway.app` domain
     is picked up automatically via `RAILWAY_PUBLIC_DOMAIN`).
   - Optional: attach Railway's **Postgres** plugin for a persistent
     database — `DATABASE_URL` is injected automatically and picked up
     without further changes. Without it, the app uses SQLite on the
     service's ephemeral disk, which is fine since the app doesn't store
     any user data (only Django's built-in `admin`/`auth` tables, useful
     if you want an admin login).
3. Deploy. Railway builds with Nixpacks (installing `ffmpeg` and running
   `collectstatic`), then runs `python manage.py migrate --noinput &&
   gunicorn videodl.wsgi --bind 0.0.0.0:$PORT --workers 3` on each
   release.
4. Open the generated `*.up.railway.app` URL to confirm the app is live.

## Legal note

Only download videos you own the rights to, or that you have explicit
permission to save. Downloading content from a platform may be subject to
that platform's terms of service and applicable copyright law — this tool
does not grant any rights beyond what you already have.
