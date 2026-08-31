"""Lightweight cache-backed rate limiting for the API endpoints.

Deliberately dependency-free: a fixed-window counter per client IP,
stored in Django's cache. Good enough to blunt scripted scraping of the
fetch/download endpoints without pulling in an external package. Note
that with the default LocMemCache each gunicorn worker keeps its own
counters, so the effective limit scales with worker count — swap in a
shared cache (e.g. Redis) if you need a strict cross-process limit.
"""
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def rate_limit(max_requests_setting, window_seconds=60):
    """Rate-limit a view, reading its cap from settings by name on every
    request (rather than at decoration time) so it stays overridable via
    env vars or Django's override_settings in tests."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            max_requests = getattr(settings, max_requests_setting)
            key = f"ratelimit:{view_func.__name__}:{_client_ip(request)}"
            cache.add(key, 0, timeout=window_seconds)
            count = cache.incr(key)
            if count > max_requests:
                return JsonResponse(
                    {"error": "Too many requests. Please slow down and try again shortly."},
                    status=429,
                )
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
