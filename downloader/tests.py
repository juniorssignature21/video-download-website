from django.test import TestCase


class IndexViewTests(TestCase):
    def test_index_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ClipGrab")

    def test_fetch_requires_url(self):
        response = self.client.post(
            "/api/fetch/", data="{}", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_download_requires_url(self):
        response = self.client.get("/api/download/")
        self.assertEqual(response.status_code, 400)

    def test_download_rejects_bad_quality(self):
        response = self.client.get(
            "/api/download/", {"url": "https://example.com/video", "quality": "9999p"}
        )
        self.assertEqual(response.status_code, 400)
