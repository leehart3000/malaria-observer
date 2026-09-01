from wagtail.models import Site
from wagtail.rich_text import RichText
from wagtail.test.utils import WagtailPageTestCase

from home.models import HomePage


class HomePageTests(WagtailPageTestCase):
    def test_home_page_renders_intro(self):
        root = Site.objects.get(is_default_site=True).root_page
        home = HomePage(
            title="Welcome", intro=[("paragraph", RichText("<p>Test intro text.</p>"))]
        )
        root.add_child(instance=home)
        home.save_revision().publish()

        response = self.client.get(home.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test intro text.")

    def test_home_page_renders_without_intro(self):
        root = Site.objects.get(is_default_site=True).root_page
        home = HomePage(title="Welcome")
        root.add_child(instance=home)
        home.save_revision().publish()

        response = self.client.get(home.url)
        self.assertEqual(response.status_code, 200)
