"""
Django settings for the videodl project.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-insecure-secret-key-change-me-in-production",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()
]

# Railway assigns a public domain per environment; trust it automatically
# so ALLOWED_HOSTS/CSRF don't need to be re-set on every deploy.
RAILWAY_PUBLIC_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["*"] if DEBUG else []

# Railway's proxy terminates TLS and forwards over plain HTTP, so Django
# needs this header to know the original request was HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Only force HTTPS redirects when actually running behind Railway's
    # proxy (or explicitly requested) — a bare "DEBUG=False" locally
    # (e.g. running tests or manage.py check) shouldn't 301 every request.
    SECURE_SSL_REDIRECT = os.environ.get(
        "DJANGO_SECURE_SSL_REDIRECT", "True" if RAILWAY_PUBLIC_DOMAIN else "False"
    ) == "True"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "downloader",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "downloader.middleware.BlockKnownScrapersMiddleware",
]

ROOT_URLCONF = "videodl.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "videodl.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# If a Postgres plugin is attached on Railway, DATABASE_URL is set
# automatically — use it instead of the local SQLite file.
_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(_database_url, conn_max_age=600)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = []
STATIC_ROOT = BASE_DIR / "staticfiles"

# Compress static files for whitenoise to serve, without Manifest-style
# hashed filenames — those require collectstatic to run before the static
# tag can resolve *any* URL, which would break runserver/manage.py test
# unless collectstatic had already been run.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Directory yt-dlp writes temporary downloads to before they are streamed
# back to the user and cleaned up.
DOWNLOAD_TMP_DIR = os.environ.get("DOWNLOAD_TMP_DIR", "")

# Hard cap on a single download so one request can't fill up disk space.
MAX_DOWNLOAD_MB = int(os.environ.get("MAX_DOWNLOAD_MB", "500"))

# Backs the rate limiter in downloader/ratelimit.py. LocMemCache is fine
# for a single-process deploy; point this at Redis for a shared limit
# across multiple gunicorn workers/instances.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Anti-scraping: per-client-IP request caps on the JSON API, on top of
# the BlockKnownScrapersMiddleware user-agent filter.
RATE_LIMIT_FETCH_PER_MIN = int(os.environ.get("RATE_LIMIT_FETCH_PER_MIN", "20"))
RATE_LIMIT_DOWNLOAD_PER_MIN = int(os.environ.get("RATE_LIMIT_DOWNLOAD_PER_MIN", "10"))