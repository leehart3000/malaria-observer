"""
Shared StreamField block definitions.

Blocks live here rather than being duplicated per-app (see CONTRIBUTING.md).
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class ParagraphBlock(blocks.RichTextBlock):
    class Meta:
        icon = "pilcrow"
        label = "Paragraph"


class NarrativeImageBlock(ImageChooserBlock):
    class Meta:
        icon = "image"
        label = "Image"


# Reusable "paragraphs and images" block set, for any page model that
# needs simple narrative content (e.g. StudyPage, ArticlePage).
NARRATIVE_BLOCKS = [
    ("paragraph", ParagraphBlock()),
    ("image", NarrativeImageBlock()),
]
