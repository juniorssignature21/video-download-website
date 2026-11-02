import json
import shutil
import tempfile
import os
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.http import require_POST

from .ratelimit import rate_limit
from .services import ALLOWED_QUALITIES, VideoFetchError, download_video, fetch_video_info


def index(request):
    return render(request, "downloader/index.html")


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /$",
        "Disallow: /api/",
        "Disallow: /admin/",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def service_worker(request):
    precache = [
        "/",
        static("downloader/css/style.css"),
        static("downloader/js/app.js"),
        static("downloader/manifest.json"),
        static("downloader/img/icon-192.png"),
        static("downloader/img/icon-512.png"),
    ]
    response = render(
        request,
        "downloader/sw.js",
        {"cache_name": "snagreel-shell-v2", "precache_json": json.dumps(precache)},
        content_type="application/javascript",
    )
    # Without this header the service worker's scope is limited to the
    # directory it's served from; we need it to control the whole site.
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


@rate_limit("RATE_LIMIT_FETCH_PER_MIN")
@require_POST
def api_fetch_info(request):
    if request.content_type == "multipart/form-data":
        url = (request.POST.get("url") or "").strip()
    else:
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON body.")
        url = (payload.get("url") or "").strip()
    if not url:
        return JsonResponse({"error": "Please paste a video link first."}, status=400)

    cookie_upload = request.FILES.get("cookies")
    cookie_path = None
    try:
        if cookie_upload:
            fd, cookie_path = tempfile.mkstemp(prefix="videodl_cookies_")
            with os.fdopen(fd, "wb") as cookie_file:
                for chunk in cookie_upload.chunks():
                    cookie_file.write(chunk)
        info = fetch_video_info(url, cookie_path)
        except VideoFetchError as exc:
        return JsonResponse({"error": _helpful_error(exc, cookie_upload)}, status=422)
    finally:
        if cookie_path:
            os.unlink(cookie_path)

    return JsonResponse(info)


@rate_limit("RATE_LIMIT_DOWNLOAD_PER_MIN")
def api_download(request):
    params = request.POST if request.method == "POST" else request.GET
    url = (params.get("url") or "").strip()
    quality = params.get("quality", "best")

    if not url:
        return JsonResponse({"error": "Missing 'url' parameter."}, status=400)
    if quality not in ALLOWED_QUALITIES:
        return JsonResponse({"error": "Unsupported quality option."}, status=400)

    tmp_root = settings.DOWNLOAD_TMP_DIR or None
    tmpdir = tempfile.mkdtemp(prefix="videodl_", dir=tmp_root)

    cookie_path = None
    try:
        cookie_upload = request.FILES.get("cookies")
        if cookie_upload:
            fd, cookie_path = tempfile.mkstemp(prefix="videodl_cookies_")
            with os.fdopen(fd, "wb") as cookie_file:
                for chunk in cookie_upload.chunks():
                    cookie_file.write(chunk)
        filepath = download_video(url, quality, Path(tmpdir), cookie_path)
    except VideoFetchError as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return JsonResponse({"error": _helpful_error(exc, cookie_upload)}, status=422)
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return JsonResponse({"error": "Unexpected error while downloading this video."}, status=500)
    finally:
        if cookie_path:
            os.unlink(cookie_path)

    size_mb = filepath.stat().st_size / (1024 * 1024)
    if size_mb > settings.MAX_DOWNLOAD_MB:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return JsonResponse(
            {"error": f"File exceeds the {settings.MAX_DOWNLOAD_MB}MB download limit."},
            status=413,
        )

    response = FileResponse(open(filepath, "rb"), as_attachment=True, filename=filepath.name)
    # yt-dlp writes into a per-request temp dir; remove it once Django has
    # finished streaming the file back to the client.
    response._resource_closers.append(lambda: shutil.rmtree(tmpdir, ignore_errors=True))
    return response


def _helpful_error(exc, cookie_upload):
    message = str(exc)
    if "Sign in to confirm" in message and not cookie_upload:
        return (
            "YouTube requires authentication for this video. Upload a valid "
            "Netscape-format YouTube cookies.txt file, then try again."
        )
    return message
