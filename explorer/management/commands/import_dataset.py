"""
Import a MalariaGEN Pf-style tab-delimited sample metadata file into
SampleRecord rows for a given Dataset.

Usage:
    uv run python manage.py import_dataset pf7 data_resources/Pf7_samples.txt

Behaviour:
    - Wipes and reimports: any existing SampleRecord rows for this
      dataset are deleted first, then the file is loaded fresh. This is
      deliberate -- see CONTRIBUTING.md / team discussion: we want a
      single clean replace rather than patched, partially-updated rows.
    - Applies only the lossless representational conversions documented
      in data_resources/DATA_RESOURCES.md (empty -> NULL, "True"/"False"
      -> boolean, "2014.0" -> integer 2014). No scientific/QC filtering
      happens here.
    - Records each row's position in the source file as `source_order`,
      so the explorer table can show source-file order as its default
      (unsorted) view.
    - Deliberately does NOT call data_curation/validate_dataset.py --
      that is a separate, decoupled process a person runs by hand
      beforehand. This command trusts the file it's given.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from datasets.models import Dataset
from explorer.models import SampleRecord

# Maps each source column name to the SampleRecord field it populates.
# Deliberately explicit rather than auto-generated from the header, so
# an unexpected/renamed source column produces a clear error instead of
# silently importing nothing into that field.
COLUMN_TO_FIELD = {
    "Sample": "sample",
    "Study": "study",
    "Country": "country",
    "Admin level 1": "admin_level_1",
    "Country latitude": "country_latitude",
    "Country longitude": "country_longitude",
    "Admin level 1 latitude": "admin_level_1_latitude",
    "Admin level 1 longitude": "admin_level_1_longitude",
    "Year": "year",
    "ENA": "ena",
    "All samples same case": "all_samples_same_case",
    "Population": "population",
    "% callable": "pct_callable",
    "QC pass": "qc_pass",
    "Exclusion reason": "exclusion_reason",
    "Sample type": "sample_type",
    # The "was in previous release" column is named differently per
    # release (e.g. "Sample was in Pf6", "Sample was in Pf7") -- matched
    # by prefix rather than an exact name, see find_previous_release_column().
}

BOOLEAN_FIELDS = {"qc_pass", "was_in_previous_release"}
FLOAT_FIELDS = {
    "country_latitude",
    "country_longitude",
    "admin_level_1_latitude",
    "admin_level_1_longitude",
    "pct_callable",
}
INTEGER_FIELDS = {"year"}

# Columns whose genuine missingness is expected (see explorer/models.py
# docstring comments) -- an empty string here becomes NULL. Any other
# column is required; an empty value there is a hard error, since it
# would indicate the file no longer matches what was validated.
NULLABLE_FIELDS = {
    "country",
    "admin_level_1",
    "country_latitude",
    "country_longitude",
    "admin_level_1_latitude",
    "admin_level_1_longitude",
    "year",
    "ena",
    "pct_callable",
}


def find_previous_release_column(header: list[str]) -> str:
    candidates = [c for c in header if c.startswith("Sample was in ")]
    if len(candidates) != 1:
        raise CommandError(
            f"Expected exactly one 'Sample was in <release>' column, found {candidates!r}"
        )
    return candidates[0]


def convert_value(field: str, raw_value: str) -> Any:
    value = raw_value.strip()

    if field in NULLABLE_FIELDS and value == "":
        return None

    if field in BOOLEAN_FIELDS:
        if value not in ("True", "False"):
            raise ValueError(
                f"expected 'True'/'False' for {field!r}, got {raw_value!r}"
            )
        return value == "True"

    if field in INTEGER_FIELDS:
        # Handles both "2014" (Pf7-style) and "2014.0" (Pf8-style) --
        # a lossless representational conversion, not a scientific one.
        return int(float(value))

    if field in FLOAT_FIELDS:
        return float(value)

    return value


class Command(BaseCommand):
    help = "Import a dataset's sample metadata TSV file into SampleRecord rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "dataset_id", help="The Dataset.dataset_id to import into (e.g. 'pf7')."
        )
        parser.add_argument("file_path", help="Path to the source TSV file.")

    def handle(self, *args, **options):
        dataset_id = options["dataset_id"]
        file_path = Path(options["file_path"])

        try:
            dataset = Dataset.objects.get(dataset_id=dataset_id)
        except Dataset.DoesNotExist as exc:
            raise CommandError(
                f"No Dataset found with dataset_id={dataset_id!r}"
            ) from exc

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        with file_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            header = list(reader.fieldnames or [])
            previous_release_column = find_previous_release_column(header)
            rows = list(reader)

        self.stdout.write(f"Read {len(rows)} rows from {file_path}")

        records = []
        for i, row in enumerate(rows):
            try:
                fields = {
                    field: convert_value(field, row[column])
                    for column, field in COLUMN_TO_FIELD.items()
                }
                fields["was_in_previous_release"] = convert_value(
                    "was_in_previous_release", row[previous_release_column]
                )
            except (KeyError, ValueError) as exc:
                raise CommandError(
                    f"Row {i + 2} (line in file, 1-based incl. header): {exc}"
                ) from exc

            fields["source_order"] = i
            fields["dataset"] = dataset
            records.append(SampleRecord(**fields))

        with transaction.atomic():
            deleted_count, _ = SampleRecord.objects.filter(dataset=dataset).delete()
            self.stdout.write(
                f"Deleted {deleted_count} existing sample record(s) for {dataset_id!r}"
            )
            SampleRecord.objects.bulk_create(records)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(records)} sample record(s) into dataset {dataset_id!r}"
            )
        )
