from django.test import TestCase

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class IndexViewTests(TestCase):
    def test_index_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SnagReel")

    def test_fetch_requires_url(self):
        response = self.client.post(
            "/api/fetch/",
            data="{}",
            content_type="application/json",
            HTTP_USER_AGENT=BROWSER_UA,
        )
        self.assertEqual(response.status_code, 400)

    def test_download_requires_url(self):
        response = self.client.get("/api/download/", HTTP_USER_AGENT=BROWSER_UA)
        self.assertEqual(response.status_code, 400)

    def test_download_rejects_bad_quality(self):
        response = self.client.get(
            "/api/download/",
            {"url": "https://example.com/video", "quality": "9999p"},
            HTTP_USER_AGENT=BROWSER_UA,
        )
        self.assertEqual(response.status_code, 400)


class AntiScrapingTests(TestCase):
    def test_blocks_known_scraper_user_agents(self):
        response = self.client.get(
            "/api/download/", HTTP_USER_AGENT="python-requests/2.31.0"
        )
        self.assertEqual(response.status_code, 403)

    def test_blocks_empty_user_agent(self):
        response = self.client.get("/api/fetch/")
        self.assertEqual(response.status_code, 403)

    def test_robots_txt_disallows_api(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Disallow: /api/", response.content)

    def test_rate_limit_returns_429_after_threshold(self):
        from django.test import override_settings

        with override_settings(RATE_LIMIT_DOWNLOAD_PER_MIN=2):
            for _ in range(2):
                self.client.get("/api/download/", HTTP_USER_AGENT=BROWSER_UA)
            response = self.client.get("/api/download/", HTTP_USER_AGENT=BROWSER_UA)
        self.assertEqual(response.status_code, 429)
