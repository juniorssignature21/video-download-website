from django.http import JsonResponse

# Default User-Agent strings of common HTTP libraries/scraping tools.
# Trivially spoofable, so this is a deterrent layer, not real security —
# it filters out the large majority of unattended scripts hitting the
# API directly without going through the site.
BLOCKED_UA_SUBSTRINGS = (
    "python-requests",
    "python-urllib",
    "scrapy",
    "curl/",
    "wget/",
    "httpclient",
    "libwww-perl",
    "go-http-client",
    "okhttp",
    "axios/",
    "node-fetch",
    "phantomjs",
    "headlesschrome",
)


class BlockKnownScrapersMiddleware:
    """Rejects requests to the JSON API from known scraper/HTTP-client
    user agents, and tells search engines not to index API responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            ua = request.META.get("HTTP_USER_AGENT", "").lower()
            if not ua or any(token in ua for token in BLOCKED_UA_SUBSTRINGS):
                return JsonResponse(
                    {"error": "Automated access to this endpoint is not allowed."},
                    status=403,
                )

        response = self.get_response(request)
        if request.path.startswith("/api/"):
            response["X-Robots-Tag"] = "noindex, nofollow"
        return response
