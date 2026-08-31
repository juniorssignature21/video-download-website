"""Thin wrapper around yt-dlp used by the downloader views."""
import shutil
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

QUALITY_LADDER = [1080, 720, 480, 360, 240]
ALLOWED_QUALITIES = {"best", "audio", *(f"{h}p" for h in QUALITY_LADDER)}


class VideoFetchError(Exception):
    """Raised whenever yt-dlp cannot read or fetch the requested link."""


def _base_opts(**overrides):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 20,
    }
    opts.update(overrides)
    return opts


def fetch_video_info(url):
    """Look up metadata + available qualities for a link without downloading it."""
    try:
        with YoutubeDL(_base_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as exc:
        raise VideoFetchError(_clean_message(str(exc))) from exc

    if not info:
        raise VideoFetchError("No video could be found at that link.")

    if "entries" in info:
        entries = [e for e in info["entries"] if e]
        if not entries:
            raise VideoFetchError("No video could be found at that link.")
        info = entries[0]

    heights = {
        fmt.get("height")
        for fmt in info.get("formats", [])
        if fmt.get("vcodec") not in (None, "none")
        and fmt.get("acodec") not in (None, "none")
        and fmt.get("height")
    }
    qualities = ["best"] + [f"{h}p" for h in QUALITY_LADDER if h in heights] + ["audio"]

    return {
        "title": info.get("title") or "Untitled video",
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader") or info.get("channel"),
        "site": info.get("extractor_key") or info.get("extractor"),
        "webpage_url": info.get("webpage_url") or url,
        "qualities": qualities,
    }


def _format_string_for(quality):
    if quality == "audio":
        return "bestaudio/best"
    if quality == "best":
        return "best[ext=mp4]/best"
    height = quality.rstrip("p")
    return f"best[height<={height}][ext=mp4]/best[height<={height}]/best"


def download_video(url, quality, dest_dir: Path):
    """Download the requested quality to dest_dir and return the resulting file path."""
    if quality not in ALLOWED_QUALITIES:
        raise VideoFetchError("Unsupported quality option.")

    ffmpeg_available = shutil.which("ffmpeg") is not None
    opts = _base_opts(
        format=_format_string_for(quality),
        outtmpl=str(dest_dir / "%(title).80s.%(ext)s"),
        restrictfilenames=True,
    )

    if quality == "audio" and ffmpeg_available:
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = Path(ydl.prepare_filename(info))
    except DownloadError as exc:
        raise VideoFetchError(_clean_message(str(exc))) from exc

    # prepare_filename() reports the pre-postprocessing name; the audio
    # postprocessor renames the file to .mp3 after download() returns.
    if quality == "audio" and ffmpeg_available:
        filepath = filepath.with_suffix(".mp3")

    if not filepath.exists():
        raise VideoFetchError("Download finished but the output file was not found.")

    return filepath


def _clean_message(message):
    return message.replace("ERROR: ", "").strip()
