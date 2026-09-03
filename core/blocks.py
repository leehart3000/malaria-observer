"""
Shared StreamField block definitions.

Blocks live here rather than being duplicated per-app (see CONTRIBUTING.md).
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock

from core.markdown import render_markdown


class ParagraphBlock(blocks.RichTextBlock):
    class Meta:
        icon = "pilcrow"
        label = "Paragraph"


class NarrativeImageBlock(ImageChooserBlock):
    class Meta:
        icon = "image"
        label = "Image"


class MarkdownBlock(blocks.TextBlock):
    class Meta:
        icon = "code"
        template = "core/blocks/markdown_block.html"

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        context["html"] = render_markdown(value)
        return context


# Reusable "paragraphs and images" block set, for any page model that
# needs simple narrative content (e.g. ArticlePage).
NARRATIVE_BLOCKS = [
    ("markdown", MarkdownBlock()),
    ("paragraph", ParagraphBlock()),
    ("image", NarrativeImageBlock()),
]

SUMMARY_BLOCKS = [
    ("markdown", MarkdownBlock()),
    ("paragraph", ParagraphBlock()),
]
