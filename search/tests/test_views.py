import pytest
from django.urls import reverse
from wagtail.models import Page


@pytest.fixture
def root_page() -> Page:
    """Return the Wagtail root page."""
    return Page.get_first_root_node()


@pytest.fixture
def searchable_page(root_page: Page) -> Page:
    """Create a single published Wagtail page that can be found by the search view."""
    page = root_page.add_child(
        instance=Page(
            title="Malaria Prevention Tips",
            slug="malaria-prevention",
        )
    )
    page.save_revision().publish()
    return page


def create_matching_pages(root_page: Page, count: int) -> None:
    """Create multiple published pages to test pagination behaviour."""
    for index in range(count):
        page = root_page.add_child(
            instance=Page(
                title=f"Malaria Page {index}",
                slug=f"malaria-page-{index}",
            )
        )
        page.save_revision().publish()


@pytest.mark.django_db
def test_search_without_query_returns_no_results(client) -> None:
    response = client.get(reverse("search"))

    assert response.status_code == 200
    assert response.context["search_query"] is None
    assert response.context["search_results"].paginator.count == 0


@pytest.mark.django_db
def test_search_with_matching_query_returns_results(
    client,
    searchable_page: Page,
) -> None:
    response = client.get(reverse("search"), {"query": "Malaria"})

    assert response.status_code == 200
    assert response.context["search_query"] == "Malaria"
    assert response.context["search_results"].paginator.count == 1
    assert response.context["search_results"][0].id == searchable_page.id


@pytest.mark.django_db
def test_search_with_non_matching_query_returns_no_results(
    client,
    searchable_page: Page,
) -> None:
    response = client.get(reverse("search"), {"query": "nonexistent-xyz"})

    assert response.status_code == 200
    assert response.context["search_results"].paginator.count == 0


@pytest.mark.django_db
def test_search_with_non_integer_page_falls_back_to_first_page(
    client,
    root_page: Page,
) -> None:
    create_matching_pages(root_page, 15)

    response = client.get(
        reverse("search"),
        {"query": "Malaria", "page": "not-a-number"},
    )

    assert response.status_code == 200
    assert response.context["search_results"].number == 1


@pytest.mark.django_db
def test_search_with_out_of_range_page_falls_back_to_last_page(
    client,
    root_page: Page,
) -> None:
    create_matching_pages(root_page, 15)

    response = client.get(
        reverse("search"),
        {"query": "Malaria", "page": 999},
    )

    assert response.status_code == 200
    # 15 results at 10 per page = 2 pages → fallback should land on page 2
    assert response.context["search_results"].number == 2
