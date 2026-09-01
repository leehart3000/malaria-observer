from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField

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
    A single editorial article. Uses BasePage's `intro` StreamField for
    the body content, plus a short `summary` field (shown on the index
    listing), mirroring DatasetPage's summary/intro split.
    """

    parent_page_types = ["articles.ArticleIndexPage"]  # noqa: RUF012
    is_creatable = True

    summary = RichTextField(blank=True)

    content_panels = BasePage.content_panels + [
        FieldPanel("summary"),
    ]
