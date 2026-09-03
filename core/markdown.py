import re

import markdown as md
from django.utils.safestring import mark_safe


def render_markdown(value):
    if not value:
        return ""
    html = md.markdown(value, extensions=["extra"])
    html = re.sub(
        r'<a href="(https?://[^"]+)"',
        r'<a href="\1" target="_blank" rel="noopener noreferrer"',
        html,
    )
    return mark_safe(html)
