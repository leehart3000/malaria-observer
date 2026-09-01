from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page

from core.blocks import NARRATIVE_BLOCKS


class HomePage(Page):
    intro = StreamField(NARRATIVE_BLOCKS, blank=True, use_json_field=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]
