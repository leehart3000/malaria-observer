from .base_page import BasePage as BasePage


class PrivacyPage(BasePage):
    """A simple general content page for privacy/cookie policy information,
    editable via the `body` StreamField inherited from BasePage."""

    is_creatable = True
    parent_page_types = ["home.HomePage"]  # noqa: RUF012
    subpage_types: list[str] = []  # noqa: RUF012

    class Meta:
        verbose_name = "Privacy Page"
