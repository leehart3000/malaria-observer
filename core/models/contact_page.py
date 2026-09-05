from .base_page import BasePage as BasePage


class ContactPage(BasePage):
    """A simple general content page for contact information, editable
    via the `body` StreamField inherited from BasePage. No extra
    fields are needed -- this exists purely to give editors a page to
    write contact details into."""

    is_creatable = True  # BasePage sets this False; must be re-enabled here
    parent_page_types = ["home.HomePage"]  # noqa: RUF012
    subpage_types: list[str] = []  # noqa: RUF012

    class Meta:
        verbose_name = "Contact page"
        verbose_name_plural = "Contact pages"
