from django.db import models


class SampleRecord(models.Model):
    # Fields confirmed complete (no missing values) during dataset
    # validation -- non-nullable, since the schema should reflect what's
    # actually been observed rather than being looser than the evidence.
    sample = models.CharField(max_length=50, db_index=True)

    # The raw "Study" value from the source file -- the contributing
    # partner study/project that provided this sample. Not a
    # relationship to anything in this codebase; kept as plain
    # descriptive text.
    source_study = models.CharField(max_length=100)

    all_samples_same_case = models.CharField(max_length=50)
    population = models.CharField(max_length=50)
    qc_pass = models.BooleanField()
    exclusion_reason = models.CharField(max_length=100)
    sample_type = models.CharField(max_length=50)

    # Unifies each release's "was this sample in the previous release"
    # column, which is named differently per release in the source data.
    was_in_previous_release = models.BooleanField()

    # Fields with genuine missingness in the source data -- nullable.
    country = models.CharField(max_length=100, null=True, blank=True)
    admin_level_1 = models.CharField(max_length=100, null=True, blank=True)
    country_latitude = models.FloatField(null=True, blank=True)
    country_longitude = models.FloatField(null=True, blank=True)
    admin_level_1_latitude = models.FloatField(null=True, blank=True)
    admin_level_1_longitude = models.FloatField(null=True, blank=True)
    year = models.IntegerField(
        null=True, blank=True
    )  # normalised from source's numeric-string form
    ena = models.CharField(max_length=50, null=True, blank=True)
    pct_callable = models.FloatField(null=True, blank=True)

    # Relationship to the Dataset (plain model, not a Wagtail page).
    # A SampleRecord always belongs to a dataset regardless of whether
    # that dataset has any editorial content page yet. PROTECT: a
    # Dataset must not be deletable while it still has samples attached.
    dataset = models.ForeignKey(
        "datasets.Dataset",
        on_delete=models.PROTECT,
        related_name="sample_records",
    )

    class Meta:
        # RUF012 (mutable class attribute) is a false positive here --
        # this is Django's standard Meta.constraints/indexes pattern.
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["dataset", "sample"],
                name="unique_sample_per_dataset",
            ),
        ]
        indexes = [  # noqa: RUF012
            models.Index(fields=["country"]),
            models.Index(fields=["year"]),
            models.Index(fields=["qc_pass"]),
        ]

    def __str__(self) -> str:
        return f"{self.sample} ({self.dataset.dataset_id})"
