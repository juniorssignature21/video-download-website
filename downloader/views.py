import json
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .services import ALLOWED_QUALITIES, VideoFetchError, download_video, fetch_video_info


def index(request):
    return render(request, "downloader/index.html")


@require_POST
def api_fetch_info(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON body.")

    url = (payload.get("url") or "").strip()
    if not url:
        return JsonResponse({"error": "Please paste a video link first."}, status=400)

    try:
        info = fetch_video_info(url)
    except VideoFetchError as exc:
        return JsonResponse({"error": str(exc)}, status=422)

    return JsonResponse(info)


@require_GET
def api_download(request):
    url = (request.GET.get("url") or "").strip()
    quality = request.GET.get("quality", "best")

    if not url:
        return JsonResponse({"error": "Missing 'url' parameter."}, status=400)
    if quality not in ALLOWED_QUALITIES:
        return JsonResponse({"error": "Unsupported quality option."}, status=400)

    tmp_root = settings.DOWNLOAD_TMP_DIR or None
    tmpdir = tempfile.mkdtemp(prefix="videodl_", dir=tmp_root)

    try:
        filepath = download_video(url, quality, Path(tmpdir))
    except VideoFetchError as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return JsonResponse({"error": str(exc)}, status=422)
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return JsonResponse({"error": "Unexpected error while downloading this video."}, status=500)

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
