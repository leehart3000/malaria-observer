from django.core.validators import RegexValidator
from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from core.blocks import SUMMARY_BLOCKS
from core.constants import LICENSE_CHOICES
from core.models import BasePage

# Lowercase, URL-safe slug convention (e.g. "pf7"), distinct from the
# human-readable `name` field (e.g. "Pf7"), which can use whatever
# capitalisation is scientifically conventional.
dataset_id_validator = RegexValidator(
    regex=r"^[a-z0-9]+(-[a-z0-9]+)*$",
    message="Use lowercase letters, numbers, and hyphens only, e.g. 'pf7'.",
)


@register_snippet
class Dataset(index.Indexed, models.Model):
    """
    The authoritative record that a dataset (e.g. "Pf7") exists, and its
    provenance. This is a plain Django model, not a Wagtail Page: a
    Dataset's identity and legal attribution must not depend on whether
    anyone has written editorial content about it yet.

    Registered as a Wagtail Snippet so maintainers can create and edit
    it in the Wagtail admin -- without it being a full page (no URL,
    no tree position, no publish/draft workflow). SampleRecord links
    here, never to DatasetPage.

    Only dataset_id and name are required. Everything else (authors,
    DOI, attribution, licence) can be filled in later, so an unfinished
    dataset entry never blocks importing its sample data.
    """

    dataset_id = models.CharField(
        max_length=10,
        unique=True,
        validators=[dataset_id_validator],
        help_text="Unique, lowercase, URL-safe identifier, e.g. 'pf7'. Used in imports and URLs.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable name, e.g. 'Pf7'.",
    )

    authors = models.CharField(max_length=255, blank=True)
    publication_year = models.IntegerField(null=True, blank=True)
    doi = models.URLField(blank=True)
    attribution = models.TextField(blank=True)
    license = models.CharField(
        max_length=100,
        choices=LICENSE_CHOICES,
        blank=True,
        help_text="Dataset licence, e.g. CC BY 4.0.",
    )

    panels = [  # noqa: RUF012
        FieldPanel("dataset_id"),
        FieldPanel("name"),
        FieldPanel("authors"),
        FieldPanel("publication_year"),
        FieldPanel("doi"),
        FieldPanel("attribution"),
        FieldPanel("license"),
    ]

    # Powers both Wagtail site search and the Snippet admin listing's
    # search box. Keep this list to fields a visitor/editor would
    # plausibly search by -- not every field needs to be indexed.
    search_fields = [  # noqa: RUF012
        index.SearchField("name"),
        index.SearchField("authors"),
        index.SearchField("attribution"),
        index.AutocompleteField("name"),
        index.FilterField("dataset_id"),
    ]

    def __str__(self) -> str:
        return f"{self.dataset_id} -- {self.name}"

    @property
    def has_geographic_data(self) -> bool:
        """Whether this dataset has at least one sample with usable
        coordinates -- used to decide whether a geographic/map explorer
        view makes sense to offer for this dataset."""
        return self.sample_records.filter(country_latitude__isnull=False).exists()


class DatasetIndexPage(BasePage):
    """
    Lists and summarises the datasets in the collection, and is the
    entry point to the data explorer / map explorer.

    Not every Dataset has a corresponding DatasetPage -- a Dataset can
    be imported and browsable before any editorial content exists.
    Templates/views built against this page must handle that case
    (e.g. checking `hasattr(dataset, "page")` before linking to one),
    rather than assuming every Dataset has a page.
    """

    subpage_types = ["datasets.DatasetPage"]  # noqa: RUF012


class DatasetPage(BasePage):
    """
    Optional editorial content describing one Dataset. A Dataset can
    exist and be fully usable (imported, browsable in the explorer)
    without a DatasetPage; this page only adds narrative/presentation.
    """

    parent_page_types = ["datasets.DatasetIndexPage"]  # noqa: RUF012

    dataset = models.OneToOneField(
        Dataset,
        on_delete=models.PROTECT,
        related_name="page",
    )

    summary = StreamField(SUMMARY_BLOCKS, blank=True, use_json_field=True, max_num=1)

    content_panels = BasePage.content_panels + [
        FieldPanel("dataset"),
        FieldPanel("summary"),
    ]

    def save(self, *args, **kwargs):
        # Keep the page's slug in lockstep with its Dataset's identifier,
        # so /datasets/<dataset_id>/ is always correct and never depends
        # on an editor typing (or mistyping) a matching slug by hand.
        self.slug = self.dataset.dataset_id
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title
