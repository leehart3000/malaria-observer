from wagtail.models import Page
from wagtail.test.utils import WagtailPageTestCase

from .models import StudyIndexPage


class StudyIndexPageTests(WagtailPageTestCase):
    def test_can_create_page(self) -> None:
        root = Page.get_first_root_node()

        page = StudyIndexPage(title="Studies", slug="studies")
        root.add_child(instance=page)

        self.assertEqual(page.title, "Studies")
        self.assertEqual(page.slug, "studies")
        self.assertEqual(page.get_parent(), root)
