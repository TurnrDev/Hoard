from pathlib import Path
from tempfile import TemporaryDirectory

from asgiref.sync import async_to_sync
from channels.routing import ProtocolTypeRouter
from channels.testing import HttpCommunicator, WebsocketCommunicator
from django.test import SimpleTestCase, override_settings

from hoard.staticfiles import serve_static_files


async def fallback(scope, receive, send):
    await send({"type": "http.response.start", "status": 202, "headers": []})
    await send({"type": "http.response.body", "body": b"django"})


async def websocket(scope, receive, send):
    await receive()
    await send({"type": "websocket.accept"})
    await receive()


class StaticFilesTests(SimpleTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "assets").mkdir()
        (self.root / "assets" / "index-AbCd1234.js").write_text("console.log('hoard')")
        (self.root / "favicon.svg").write_text("<svg></svg>")
        self.http = serve_static_files(fallback, self.root)

    def request(self, method, path):
        communicator = HttpCommunicator(self.http, method, path)
        communicator.scope["root_path"] = ""
        return communicator

    async def test_hashed_javascript_has_correct_type_and_immutable_cache(self):
        response = await self.request(
            "GET", "/static/assets/index-AbCd1234.js"
        ).get_response()
        headers = dict(response["headers"])
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["body"], b"console.log('hoard')")
        self.assertIn(b"javascript", headers[b"content-type"])
        self.assertIn(b"immutable", headers[b"cache-control"])

    async def test_stable_filename_has_short_cache_and_supports_head(self):
        response = await self.request("HEAD", "/static/favicon.svg").get_response()
        headers = dict(response["headers"])
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["body"], b"")
        self.assertNotIn(b"immutable", headers[b"cache-control"])

    async def test_missing_static_returns_404_instead_of_spa(self):
        response = await self.request("GET", "/static/missing.js").get_response()
        self.assertEqual(response["status"], 404)

    async def test_other_http_requests_reach_django(self):
        response = await self.request("GET", "/release-manifest.json").get_response()
        self.assertEqual(response["status"], 202)
        self.assertEqual(response["body"], b"django")

    def test_websocket_route_remains_independent(self):
        async def check():
            application = ProtocolTypeRouter(
                {"http": self.http, "websocket": websocket}
            )
            communicator = WebsocketCommunicator(application, "/ws/")
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.disconnect()

        async_to_sync(check)()

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
    def test_retired_media_url_is_not_served(self):
        response = self.client.get("/media/old-portrait.jpg")
        self.assertEqual(response.status_code, 404)
