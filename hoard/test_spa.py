from django.test import SimpleTestCase

from hoard.spa import project_version


class ReleaseManifestTests(SimpleTestCase):
    def test_manifest_exposes_project_version_without_caching(self) -> None:
        response = self.client.get("/release-manifest.json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"version": project_version()})
        self.assertEqual(
            response.headers["Cache-Control"],
            "no-store, no-cache, must-revalidate",
        )
        self.assertEqual(response.headers["Pragma"], "no-cache")
