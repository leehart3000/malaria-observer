from modelcluster.fields import ParentalManyToManyField
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField

from core.blocks import SUMMARY_BLOCKS
from core.models import BasePage


class ArticleIndexPage(BasePage):
    """
    Lists published ArticlePages. Mirrors DatasetIndexPage's pattern:
    only live children are shown, and creating an ArticlePage doesn't
    make it appear here until it's actually published.
    """

    subpage_types = ["articles.ArticlePage"]  # noqa: RUF012
    is_creatable = True


class ArticlePage(BasePage):
    """
    A single editorial article. Uses BasePage's `body` StreamField for
    the body content, plus a short `summary` field (shown on the index
    listing), mirroring DatasetPage's summary/body split.
    """

    parent_page_types = ["articles.ArticleIndexPage"]  # noqa: RUF012
    is_creatable = True

    summary = StreamField(SUMMARY_BLOCKS, blank=True, use_json_field=True, max_num=1)

    related_datasets = ParentalManyToManyField(
        "datasets.Dataset",
        blank=True,
        related_name="related_articles",
    )

    content_panels = BasePage.content_panels + [
        FieldPanel("summary"),
        FieldPanel("related_datasets"),
    ]
