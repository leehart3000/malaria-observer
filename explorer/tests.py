import tempfile
from pathlib import Path
from typing import cast
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from datasets.factories import DatasetFactory
from datasets.models import Dataset

from .factories import SampleRecordFactory
from .models import SampleRecord


class ExplorerTableSortingTests(TestCase):
    def setUp(self):
        self.dataset = cast(Dataset, DatasetFactory(dataset_id="pf7", name="Pf7"))
        self.url = reverse("explorer_table")

        # Deliberately created out of alphabetical/numeric order, so a
        # passing sort test can't be an accident of insertion order.
        cast(
            SampleRecord,
            SampleRecordFactory(
                dataset=self.dataset, sample="QN0003", country="Ghana", year=2016
            ),
        )
        cast(
            SampleRecord,
            SampleRecordFactory(
                dataset=self.dataset, sample="QN0001", country="Vietnam", year=2012
            ),
        )
        cast(
            SampleRecord,
            SampleRecordFactory(
                dataset=self.dataset, sample="QN0002", country="Laos", year=2014
            ),
        )

    def test_no_sort_params_returns_default_ordering(self):
        response = self.client.get(self.url, {"set": "pf7"})
        samples = list(response.context["samples"])
        # Default (unsorted) ordering isn't guaranteed to be anything in
        # particular -- just confirm no sort was silently applied and
        # all three rows come back.
        self.assertEqual(len(samples), 3)
        self.assertIsNone(response.context["view"].sort)
        self.assertIsNone(response.context["view"].order)

    def test_sort_ascending_by_sample(self):
        response = self.client.get(
            self.url, {"set": "pf7", "sort": "sample", "order": "asc"}
        )
        samples = list(response.context["samples"])
        self.assertEqual([s.sample for s in samples], ["QN0001", "QN0002", "QN0003"])

    def test_sort_descending_by_sample(self):
        response = self.client.get(
            self.url, {"set": "pf7", "sort": "sample", "order": "desc"}
        )
        samples = list(response.context["samples"])
        self.assertEqual([s.sample for s in samples], ["QN0003", "QN0002", "QN0001"])

    def test_sort_ascending_by_year(self):
        response = self.client.get(
            self.url, {"set": "pf7", "sort": "year", "order": "asc"}
        )
        samples = list(response.context["samples"])
        self.assertEqual([s.year for s in samples], [2012, 2014, 2016])

    def test_invalid_sort_column_is_ignored(self):
        # "country" is a real column but not on the sort whitelist in
        # this test's intent -- use a genuinely bogus name to confirm
        # the whitelist check in the view actually rejects it, rather
        # than blowing up with a FieldError.
        response = self.client.get(
            self.url, {"set": "pf7", "sort": "not_a_real_column", "order": "asc"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["samples"]), 3)

    def test_invalid_order_value_is_ignored(self):
        response = self.client.get(
            self.url, {"set": "pf7", "sort": "sample", "order": "sideways"}
        )
        self.assertEqual(response.status_code, 200)
        # Sort should not have been applied since order isn't asc/desc.
        samples = list(response.context["samples"])
        self.assertEqual(len(samples), 3)

    def test_no_sort_params_uses_source_order(self):
        # Clear out setUp's samples so this test controls source_order
        # explicitly, independent of creation order.
        SampleRecord.objects.filter(dataset=self.dataset).delete()

        SampleRecordFactory(dataset=self.dataset, sample="ZZZ", source_order=2)
        SampleRecordFactory(dataset=self.dataset, sample="AAA", source_order=0)
        SampleRecordFactory(dataset=self.dataset, sample="MMM", source_order=1)

        response = self.client.get(self.url, {"set": "pf7"})
        samples = list(response.context["samples"])
        self.assertEqual([s.sample for s in samples], ["AAA", "MMM", "ZZZ"])


class ExplorerTableFilteringTests(TestCase):
    def setUp(self):
        self.dataset = cast(Dataset, DatasetFactory(dataset_id="pf7", name="Pf7"))
        self.url = reverse("explorer_table")

        cast(
            SampleRecord,
            SampleRecordFactory(
                dataset=self.dataset,
                sample="QN0001",
                country="Ghana",
                study="1147-PF-MR-CONWAY",
                year=2012,
                qc_pass=True,
            ),
        )
        cast(
            SampleRecord,
            SampleRecordFactory(
                dataset=self.dataset,
                sample="QN0002",
                country="Vietnam",
                study="1147-PF-MR-CONWAY",
                year=2014,
                qc_pass=False,
            ),
        )
        cast(
            SampleRecord,
            SampleRecordFactory(
                dataset=self.dataset,
                sample="QN0003",
                country="Ghana",
                study="1156-PF-KH-BAKER",
                year=2016,
                qc_pass=True,
            ),
        )

    def test_general_filter_matches_country(self):
        response = self.client.get(self.url, {"set": "pf7", "q": "Ghana"})
        samples = list(response.context["samples"])
        self.assertEqual({s.sample for s in samples}, {"QN0001", "QN0003"})

    def test_general_filter_is_case_insensitive_partial_match(self):
        response = self.client.get(self.url, {"set": "pf7", "q": "ghan"})
        samples = list(response.context["samples"])
        self.assertEqual({s.sample for s in samples}, {"QN0001", "QN0003"})

    def test_general_filter_matches_study(self):
        response = self.client.get(self.url, {"set": "pf7", "q": "BAKER"})
        samples = list(response.context["samples"])
        self.assertEqual([s.sample for s in samples], ["QN0003"])

    def test_general_filter_matches_sample_id(self):
        response = self.client.get(self.url, {"set": "pf7", "q": "QN0002"})
        samples = list(response.context["samples"])
        self.assertEqual([s.sample for s in samples], ["QN0002"])

    def test_filter_by_year_is_exact(self):
        response = self.client.get(self.url, {"set": "pf7", "year": "2014"})
        samples = list(response.context["samples"])
        self.assertEqual([s.sample for s in samples], ["QN0002"])

    def test_filter_by_qc_pass_boolean(self):
        response = self.client.get(self.url, {"set": "pf7", "qc_pass": "false"})
        samples = list(response.context["samples"])
        self.assertEqual([s.sample for s in samples], ["QN0002"])

    def test_combining_general_filter_and_sort(self):
        response = self.client.get(
            self.url,
            {"set": "pf7", "q": "Ghana", "sort": "sample", "order": "desc"},
        )
        samples = list(response.context["samples"])
        self.assertEqual([s.sample for s in samples], ["QN0003", "QN0001"])

    def test_no_matches_returns_empty_queryset(self):
        response = self.client.get(self.url, {"set": "pf7", "q": "Nowhere"})
        samples = list(response.context["samples"])
        self.assertEqual(samples, [])

    def test_empty_general_filter_returns_all(self):
        response = self.client.get(self.url, {"set": "pf7", "q": ""})
        samples = list(response.context["samples"])
        self.assertEqual(len(samples), 3)

    def test_missingness_with_matches_rows_with_null_country(self):
        SampleRecordFactory(
            dataset=self.dataset, sample="QN0004", country=None, year=2018
        )
        response = self.client.get(self.url, {"set": "pf7", "missingness": "with"})
        samples = list(response.context["samples"])
        self.assertIn("QN0004", [s.sample for s in samples])

    def test_missingness_with_matches_rows_with_null_year(self):
        SampleRecordFactory(
            dataset=self.dataset, sample="QN0005", country="Ghana", year=None
        )
        response = self.client.get(self.url, {"set": "pf7", "missingness": "with"})
        samples = list(response.context["samples"])
        self.assertIn("QN0005", [s.sample for s in samples])

    def test_missingness_with_excludes_complete_rows(self):
        # setUp's three samples are all complete, so none should match.
        response = self.client.get(self.url, {"set": "pf7", "missingness": "with"})
        samples = list(response.context["samples"])
        self.assertEqual(samples, [])

    def test_missingness_without_returns_only_complete_rows(self):
        SampleRecordFactory(
            dataset=self.dataset, sample="QN0007", country=None, year=2018
        )
        response = self.client.get(self.url, {"set": "pf7", "missingness": "without"})
        samples = list(response.context["samples"])
        self.assertNotIn("QN0007", [s.sample for s in samples])
        self.assertEqual(len(samples), 3)  # setUp's three complete rows

    def test_missingness_blank_returns_all_rows(self):
        response = self.client.get(self.url, {"set": "pf7", "missingness": ""})
        samples = list(response.context["samples"])
        self.assertEqual(len(samples), 3)

    def test_missingness_combined_with_general_filter(self):
        SampleRecordFactory(
            dataset=self.dataset,
            sample="QN0006",
            country="Ghana",
            year=None,
            study="1147-PF-MR-CONWAY",
        )
        response = self.client.get(
            self.url, {"set": "pf7", "missingness": "with", "q": "Ghana"}
        )
        samples = list(response.context["samples"])
        self.assertEqual([s.sample for s in samples], ["QN0006"])


class ExplorerTableMessagingTests(TestCase):
    def setUp(self):
        self.dataset = cast(Dataset, DatasetFactory(dataset_id="pf7", name="Pf7"))
        self.url = reverse("explorer_table")

    def test_empty_dataset_shows_unfiltered_empty_message(self):
        response = self.client.get(self.url, {"set": "pf7"})
        self.assertContains(response, "No samples found for this dataset.")
        self.assertNotContains(response, "No samples in this dataset match the filter.")

    def test_empty_dataset_shows_plain_count_wording(self):
        cast(SampleRecord, SampleRecordFactory(dataset=self.dataset, sample="QN0001"))
        response = self.client.get(self.url, {"set": "pf7"})
        self.assertContains(response, "of 1 samples.")
        self.assertNotContains(response, "matching samples.")

    def test_filtered_with_no_matches_shows_filtered_empty_message(self):
        cast(
            SampleRecord,
            SampleRecordFactory(dataset=self.dataset, sample="QN0001", country="Ghana"),
        )
        response = self.client.get(self.url, {"set": "pf7", "q": "Nowhere"})
        self.assertContains(response, "No samples in this dataset match the filter.")
        self.assertNotContains(response, "No samples found for this dataset.")

    def test_filtered_with_matches_shows_matching_count_wording(self):
        cast(
            SampleRecord,
            SampleRecordFactory(dataset=self.dataset, sample="QN0001", country="Ghana"),
        )
        cast(
            SampleRecord,
            SampleRecordFactory(
                dataset=self.dataset, sample="QN0002", country="Vietnam"
            ),
        )
        response = self.client.get(self.url, {"set": "pf7", "q": "Ghana"})
        self.assertContains(response, "of 1 matching samples.")

    def test_blank_filter_params_are_not_treated_as_filtered(self):
        # Empty q/year/qc_pass params (e.g. left over from an untouched
        # filter form) shouldn't count as "a filter is active".
        cast(SampleRecord, SampleRecordFactory(dataset=self.dataset, sample="QN0001"))
        response = self.client.get(self.url, {"set": "pf7", "q": "", "year": ""})
        self.assertContains(response, "of 1 samples.")
        self.assertNotContains(response, "matching samples.")


class ExplorerTablePageSizeTests(TestCase):
    def setUp(self):
        self.dataset = cast(Dataset, DatasetFactory(dataset_id="pf7", name="Pf7"))
        self.url = reverse("explorer_table")
        for i in range(75):
            cast(
                SampleRecord,
                SampleRecordFactory(dataset=self.dataset, sample=f"QN{i:04d}"),
            )

    def test_default_page_size_is_fifty(self):
        response = self.client.get(self.url, {"set": "pf7"})
        self.assertEqual(len(response.context["samples"]), 50)
        self.assertTrue(response.context["is_paginated"])

    def test_page_size_100_shows_all_75_on_one_page(self):
        response = self.client.get(self.url, {"set": "pf7", "page_size": "100"})
        self.assertEqual(len(response.context["samples"]), 75)

    def test_page_size_25_paginates_into_three_pages(self):
        response = self.client.get(self.url, {"set": "pf7", "page_size": "25"})
        self.assertEqual(len(response.context["samples"]), 25)
        self.assertEqual(response.context["paginator"].num_pages, 3)

    def test_page_size_all_disables_pagination(self):
        response = self.client.get(self.url, {"set": "pf7", "page_size": "all"})
        self.assertEqual(len(response.context["samples"]), 75)
        self.assertFalse(response.context["is_paginated"])
        self.assertContains(response, "Showing all 75 samples.")

    def test_invalid_page_size_falls_back_to_default(self):
        response = self.client.get(self.url, {"set": "pf7", "page_size": "999"})
        self.assertEqual(len(response.context["samples"]), 50)

    def test_show_all_option_hidden_above_threshold(self):
        with mock.patch("explorer.views.SHOW_ALL_THRESHOLD", 10):
            response = self.client.get(self.url, {"set": "pf7"})
        self.assertFalse(response.context["show_all_available"])
        self.assertNotContains(response, ">All<")

    def test_page_size_all_ignored_above_threshold(self):
        # Even if "all" is requested directly via the URL, it must not
        # bypass the threshold -- this protects against someone hand-
        # editing the query string, not just hiding the UI option.
        with mock.patch("explorer.views.SHOW_ALL_THRESHOLD", 10):
            response = self.client.get(self.url, {"set": "pf7", "page_size": "all"})
        self.assertEqual(len(response.context["samples"]), 50)
        self.assertTrue(response.context["is_paginated"])


class ImportDatasetCommandTests(TestCase):
    def setUp(self):
        self.dataset = cast(Dataset, DatasetFactory(dataset_id="pf7", name="Pf7"))

    def _write_tsv(self, rows: list[str], header: str | None = None) -> str:
        """Write a small fixture TSV to a temp file and return its path.
        Uses the real Pf7 column set/order by default."""
        if header is None:
            header = (
                "Sample\tStudy\tCountry\tAdmin level 1\tCountry latitude\t"
                "Country longitude\tAdmin level 1 latitude\tAdmin level 1 longitude\t"
                "Year\tENA\tAll samples same case\tPopulation\t% callable\t"
                "QC pass\tExclusion reason\tSample type\tSample was in Pf6"
            )
        fd, path = tempfile.mkstemp(suffix=".txt")
        with open(fd, "w", encoding="utf-8") as f:
            f.write(header + "\n")
            for row in rows:
                f.write(row + "\n")
        return path

    def test_import_creates_expected_rows_with_conversions(self):
        path = self._write_tsv(
            [
                "FP0001\t1147-PF-MR-CONWAY\tGhana\tAshanti\t6.0\t-1.0\t6.1\t-1.1\t"
                "2014.0\tERR001\tFP0001\tAF-W\t82.16\tTrue\tAnalysis_set\tgDNA\tTrue",
                "FP0002\t1147-PF-MR-CONWAY\t\t\t\t\t\t\t"
                "\t\tFP0002\tAF-W\t88.85\tFalse\tAnalysis_set\tgDNA\tFalse",
            ]
        )

        call_command("import_dataset", "pf7", path)

        records = list(
            SampleRecord.objects.filter(dataset=self.dataset).order_by("source_order")
        )
        self.assertEqual(len(records), 2)

        first = records[0]
        self.assertEqual(first.sample, "FP0001")
        self.assertEqual(first.year, 2014)  # "2014.0" -> integer 2014
        self.assertIs(first.qc_pass, True)
        self.assertIs(first.was_in_previous_release, True)
        self.assertEqual(first.country, "Ghana")
        self.assertEqual(first.source_order, 0)

        second = records[1]
        self.assertIsNone(second.country)  # empty string -> NULL
        self.assertIsNone(second.year)
        self.assertIsNone(second.ena)
        self.assertIs(second.qc_pass, False)
        self.assertEqual(second.source_order, 1)

        Path(path).unlink()

    def test_reimport_replaces_rather_than_duplicates(self):
        path = self._write_tsv(
            [
                "FP0001\t1147-PF-MR-CONWAY\tGhana\tAshanti\t6.0\t-1.0\t6.1\t-1.1\t"
                "2014\tERR001\tFP0001\tAF-W\t82.16\tTrue\tAnalysis_set\tgDNA\tTrue",
            ]
        )

        call_command("import_dataset", "pf7", path)
        call_command("import_dataset", "pf7", path)

        self.assertEqual(SampleRecord.objects.filter(dataset=self.dataset).count(), 1)
        Path(path).unlink()

    def test_missing_previous_release_column_raises_clear_error(self):
        header = (
            "Sample\tStudy\tCountry\tAdmin level 1\tCountry latitude\t"
            "Country longitude\tAdmin level 1 latitude\tAdmin level 1 longitude\t"
            "Year\tENA\tAll samples same case\tPopulation\t% callable\t"
            "QC pass\tExclusion reason\tSample type"  # no "Sample was in ..." column
        )
        path = self._write_tsv(
            [
                "FP0001\t1147-PF-MR-CONWAY\tGhana\tAshanti\t6.0\t-1.0\t6.1\t-1.1\t"
                "2014\tERR001\tFP0001\tAF-W\t82.16\tTrue\tAnalysis_set\tgDNA"
            ],
            header=header,
        )

        with self.assertRaises(CommandError):
            call_command("import_dataset", "pf7", path)

        Path(path).unlink()

    def test_invalid_boolean_value_raises_clear_error(self):
        path = self._write_tsv(
            [
                "FP0001\t1147-PF-MR-CONWAY\tGhana\tAshanti\t6.0\t-1.0\t6.1\t-1.1\t"
                "2014\tERR001\tFP0001\tAF-W\t82.16\tMaybe\tAnalysis_set\tgDNA\tTrue",
            ]
        )

        with self.assertRaises(CommandError):
            call_command("import_dataset", "pf7", path)

        Path(path).unlink()

    def test_unknown_dataset_id_raises_clear_error(self):
        path = self._write_tsv(
            [
                "FP0001\t1147-PF-MR-CONWAY\tGhana\tAshanti\t6.0\t-1.0\t6.1\t-1.1\t"
                "2014\tERR001\tFP0001\tAF-W\t82.16\tTrue\tAnalysis_set\tgDNA\tTrue",
            ]
        )

        with self.assertRaises(CommandError):
            call_command("import_dataset", "not-a-real-dataset", path)

        Path(path).unlink()

    def test_missing_file_raises_clear_error(self):
        with self.assertRaises(CommandError):
            call_command("import_dataset", "pf7", "/tmp/definitely-does-not-exist.txt")


class ExplorerGeoViewTests(TestCase):
    def setUp(self):
        self.dataset = cast(Dataset, DatasetFactory(dataset_id="pf7", name="Pf7"))
        self.url = reverse("explorer_geo")

    def test_aggregates_by_country_with_counts(self):
        SampleRecordFactory.create_batch(
            3,
            dataset=self.dataset,
            country="Ghana",
            country_latitude=6.0,
            country_longitude=-1.0,
        )
        SampleRecordFactory.create_batch(
            2,
            dataset=self.dataset,
            country="Vietnam",
            country_latitude=14.0,
            country_longitude=108.0,
        )

        response = self.client.get(self.url, {"set": "pf7"})
        locations = {
            loc["label"]: loc["count"] for loc in response.context["locations_data"]
        }

        self.assertEqual(locations, {"Ghana": 3, "Vietnam": 2})

    def test_defaults_to_country_level_when_not_specified(self):
        SampleRecordFactory(
            dataset=self.dataset,
            country="Ghana",
            country_latitude=6.0,
            country_longitude=-1.0,
            admin_level_1="Ashanti",
            admin_level_1_latitude=6.7,
            admin_level_1_longitude=-1.6,
        )
        response = self.client.get(self.url, {"set": "pf7"})
        self.assertEqual(response.context["level"], "country")
        self.assertEqual(response.context["locations_data"][0]["label"], "Ghana")

    def test_invalid_level_falls_back_to_country(self):
        SampleRecordFactory(
            dataset=self.dataset,
            country="Ghana",
            country_latitude=6.0,
            country_longitude=-1.0,
        )
        response = self.client.get(
            self.url, {"set": "pf7", "level": "not_a_real_level"}
        )
        self.assertEqual(response.context["level"], "country")

    def test_admin1_level_groups_by_finer_location(self):
        SampleRecordFactory(
            dataset=self.dataset,
            country="Ghana",
            country_latitude=6.0,
            country_longitude=-1.0,
            admin_level_1="Ashanti",
            admin_level_1_latitude=6.7,
            admin_level_1_longitude=-1.6,
        )
        SampleRecordFactory(
            dataset=self.dataset,
            country="Ghana",
            country_latitude=6.0,
            country_longitude=-1.0,
            admin_level_1="Volta",
            admin_level_1_latitude=6.9,
            admin_level_1_longitude=0.5,
        )

        response = self.client.get(self.url, {"set": "pf7", "level": "admin1"})
        locations = {loc["label"] for loc in response.context["locations_data"]}

        self.assertEqual(locations, {"Ashanti", "Volta"})

    def test_excludes_rows_with_null_coordinates_at_chosen_level(self):
        SampleRecordFactory(
            dataset=self.dataset,
            country="Ghana",
            country_latitude=6.0,
            country_longitude=-1.0,
        )
        SampleRecordFactory(
            dataset=self.dataset,
            country=None,
            country_latitude=None,
            country_longitude=None,
        )

        response = self.client.get(self.url, {"set": "pf7"})
        self.assertEqual(len(response.context["locations_data"]), 1)

    def test_respects_general_text_filter(self):
        SampleRecordFactory(
            dataset=self.dataset,
            sample="QN0001",
            country="Ghana",
            country_latitude=6.0,
            country_longitude=-1.0,
        )
        SampleRecordFactory(
            dataset=self.dataset,
            sample="QN0002",
            country="Vietnam",
            country_latitude=14.0,
            country_longitude=108.0,
        )

        response = self.client.get(self.url, {"set": "pf7", "q": "Ghana"})
        locations = {loc["label"] for loc in response.context["locations_data"]}

        self.assertEqual(locations, {"Ghana"})
        self.assertTrue(response.context["is_filtered"])

    def test_respects_qc_pass_filter(self):
        SampleRecordFactory(
            dataset=self.dataset,
            country="Ghana",
            qc_pass=True,
            country_latitude=6.0,
            country_longitude=-1.0,
        )
        SampleRecordFactory(
            dataset=self.dataset,
            country="Vietnam",
            qc_pass=False,
            country_latitude=14.0,
            country_longitude=108.0,
        )

        response = self.client.get(self.url, {"set": "pf7", "qc_pass": "false"})
        locations = {loc["label"] for loc in response.context["locations_data"]}

        self.assertEqual(locations, {"Vietnam"})

    def test_respects_missingness_filter(self):
        SampleRecordFactory(
            dataset=self.dataset,
            country="Ghana",
            year=2014,
            country_latitude=6.0,
            country_longitude=-1.0,
        )
        SampleRecordFactory(
            dataset=self.dataset,
            country="Vietnam",
            year=None,
            country_latitude=14.0,
            country_longitude=108.0,
        )

        response = self.client.get(self.url, {"set": "pf7", "missingness": "with"})
        locations = {loc["label"] for loc in response.context["locations_data"]}

        self.assertEqual(locations, {"Vietnam"})

    def test_unfiltered_request_shows_all_locations(self):
        SampleRecordFactory(
            dataset=self.dataset,
            country="Ghana",
            country_latitude=6.0,
            country_longitude=-1.0,
        )
        SampleRecordFactory(
            dataset=self.dataset,
            country="Vietnam",
            country_latitude=14.0,
            country_longitude=108.0,
        )

        response = self.client.get(self.url, {"set": "pf7"})
        self.assertFalse(response.context["is_filtered"])
        self.assertEqual(len(response.context["locations_data"]), 2)

    def test_unknown_dataset_returns_404(self):
        response = self.client.get(self.url, {"set": "not-a-real-dataset"})
        self.assertEqual(response.status_code, 404)
