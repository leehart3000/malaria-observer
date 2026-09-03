from typing import cast

from django.test import TestCase
from wagtail.models import Site
from wagtail.rich_text import RichText
from wagtail.test.utils import WagtailPageTestCase

from core.models import ContactPage
from datasets.factories import DatasetIndexPageFactory
from datasets.models import DatasetIndexPage
from home.models import HomePage


class ContactPageTests(WagtailPageTestCase):
    def test_contact_page_renders_body(self):
        root = Site.objects.get(is_default_site=True).root_page
        home = HomePage(title="Welcome")
        root.add_child(instance=home)
        home.save_revision().publish()

        contact = ContactPage(
            title="Contact", body=[("paragraph", RichText("<p>Get in touch.</p>"))]
        )
        home.add_child(instance=contact)
        contact.save_revision().publish()

        response = self.client.get(contact.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Get in touch.")

    def test_contact_page_can_be_created_under_home_page(self):
        home = HomePage(title="Welcome")
        Site.objects.get(is_default_site=True).root_page.add_child(instance=home)
        self.assertTrue(ContactPage.can_create_at(home))

    def test_contact_page_cannot_be_created_under_dataset_index_page(self):
        home = HomePage(title="Welcome")
        Site.objects.get(is_default_site=True).root_page.add_child(instance=home)
        index = cast(
            "DatasetIndexPage",
            DatasetIndexPageFactory(title="Datasets", parent=home),
        )
        self.assertFalse(ContactPage.can_create_at(index))


class NavigationTests(TestCase):
    def setUp(self):
        self.root = Site.objects.get(is_default_site=True).root_page
        self.home = HomePage(title="Welcome")
        self.root.add_child(instance=self.home)
        self.home.save_revision().publish()

    def test_nav_shows_home_link(self):
        response = self.client.get(self.home.url)
        self.assertContains(response, 'href="/"')

    def test_nav_hides_datasets_link_when_no_index_page_exists(self):
        response = self.client.get(self.home.url)
        self.assertNotContains(response, ">Datasets<")

    def test_nav_shows_datasets_link_when_index_page_exists(self):
        index = cast(
            "DatasetIndexPage",
            DatasetIndexPageFactory(title="Datasets", parent=self.home),
        )
        index.save_revision().publish()

        response = self.client.get(self.home.url)
        self.assertContains(response, 'href="' + index.url + '"')

    def test_nav_hides_contact_link_when_no_contact_page_exists(self):
        response = self.client.get(self.home.url)
        self.assertNotContains(response, ">Contact<")

    def test_nav_shows_contact_link_when_contact_page_exists(self):
        contact = ContactPage(title="Contact")
        self.home.add_child(instance=contact)
        contact.save_revision().publish()

        response = self.client.get(self.home.url)
        self.assertContains(response, 'href="' + contact.url + '"')

    def test_footer_shows_copyright(self):
        response = self.client.get(self.home.url)
        self.assertContains(response, "Malaria Observer")
