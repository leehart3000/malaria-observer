from typing import cast

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase
from wagtail.models import Page, Site
from wagtail.snippets.models import get_snippet_models
from wagtail.test.utils import WagtailPageTestCase

from explorer.factories import SampleRecordFactory

from .factories import DatasetFactory, DatasetIndexPageFactory
from .models import Dataset, DatasetIndexPage, DatasetPage


class DatasetIndexPageTests(WagtailPageTestCase):
    def test_can_create_page(self) -> None:
        root = Page.get_first_root_node()

        page = DatasetIndexPage(title="Datasets", slug="datasets")
        root.add_child(instance=page)

        self.assertEqual(page.title, "Datasets")
        self.assertEqual(page.slug, "datasets")
        self.assertEqual(page.get_parent(), root)


class DatasetTests(TestCase):
    def test_dataset_can_exist_without_a_page(self) -> None:
        dataset = Dataset.objects.create(dataset_id="pf7", name="Pf7")

        self.assertEqual(dataset.dataset_id, "pf7")
        self.assertFalse(hasattr(dataset, "page"))

    def test_dataset_can_have_sample_records(self) -> None:
        dataset = cast(Dataset, DatasetFactory())
        SampleRecordFactory(dataset=dataset, sample="ABC")
        SampleRecordFactory(dataset=dataset, sample="DEF")

        self.assertEqual(dataset.sample_records.count(), 2)

    def test_same_sample_identifier_can_exist_in_two_datasets(self) -> None:
        dataset_a = cast(Dataset, DatasetFactory(dataset_id="pf7"))
        dataset_b = cast(Dataset, DatasetFactory(dataset_id="pf8"))

        SampleRecordFactory(dataset=dataset_a, sample="ABC")
        SampleRecordFactory(dataset=dataset_b, sample="ABC")

        self.assertEqual(dataset_a.sample_records.get(sample="ABC").dataset, dataset_a)
        self.assertEqual(dataset_b.sample_records.get(sample="ABC").dataset, dataset_b)

    def test_same_sample_identifier_cannot_occur_twice_within_one_dataset(self) -> None:
        dataset = cast(Dataset, DatasetFactory())
        SampleRecordFactory(dataset=dataset, sample="ABC")

        with self.assertRaises(IntegrityError):
            SampleRecordFactory(dataset=dataset, sample="ABC")

    def test_dataset_page_can_point_to_a_dataset(self) -> None:
        root = Page.get_first_root_node()
        index_page = DatasetIndexPageFactory.build()
        root.add_child(instance=index_page)

        dataset = cast(Dataset, DatasetFactory())
        page = DatasetPage(title=dataset.name, dataset=dataset)
        index_page.add_child(instance=page)

        self.assertEqual(page.dataset, dataset)
        self.assertEqual(dataset.page, page)

    def test_a_dataset_cannot_have_two_dataset_pages(self) -> None:
        root = Page.get_first_root_node()
        index_page = DatasetIndexPageFactory.build()
        root.add_child(instance=index_page)

        dataset = cast(Dataset, DatasetFactory())
        first_page = DatasetPage(title=f"{dataset.name} (1)", dataset=dataset)
        index_page.add_child(instance=first_page)

        second_page = DatasetPage(title=f"{dataset.name} (2)", dataset=dataset)
        # DatasetPage.save() sets the slug and Wagtail's Page.save() runs
        # full_clean() before hitting the database, so the duplicate
        # (both slug and OneToOne dataset) is caught as a ValidationError
        # here, not a raw IntegrityError.
        with self.assertRaises(ValidationError):
            index_page.add_child(instance=second_page)

    def test_dataset_is_registered_as_a_snippet(self) -> None:
        self.assertIn(Dataset, get_snippet_models())

    def test_dataset_index_page_only_lists_dataset_pages(self) -> None:
        # Rooted under the default Site's actual homepage (not the raw
        # tree root) so the page has a resolvable URL -- .url is None,
        # and any request 404s, for a page with no associated Site.
        home_page = Site.objects.get(is_default_site=True).root_page
        index_page = DatasetIndexPageFactory.build()
        home_page.add_child(instance=index_page)

        # An orphan Dataset (no DatasetPage) must never appear.
        DatasetFactory(dataset_id="pf7", name="Pf7 Orphan")

        # A Dataset with a published DatasetPage must appear.
        published_dataset = cast(Dataset, DatasetFactory(dataset_id="pf8", name="Pf8"))
        published_page = DatasetPage(title="Pf8 Published", dataset=published_dataset)
        index_page.add_child(instance=published_page)

        response = self.client.get(index_page.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Pf7 Orphan")
        self.assertContains(response, "Pf8 Published")

    def test_cannot_delete_dataset_with_sample_records(self) -> None:
        dataset = cast(Dataset, DatasetFactory())
        SampleRecordFactory(dataset=dataset)

        with self.assertRaises(ProtectedError):
            dataset.delete()

    def test_cannot_delete_dataset_with_a_page(self) -> None:
        root = Page.get_first_root_node()
        index_page = DatasetIndexPageFactory.build()
        root.add_child(instance=index_page)

        dataset = cast(Dataset, DatasetFactory())
        page = DatasetPage(title=dataset.name, dataset=dataset)
        index_page.add_child(instance=page)

        with self.assertRaises(ProtectedError):
            dataset.delete()
