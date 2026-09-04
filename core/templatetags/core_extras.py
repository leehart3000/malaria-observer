from django import template

from core.markdown import render_markdown
from datasets.models import DatasetIndexPage

register = template.Library()


@register.inclusion_tag("core/includes/dataset_action_buttons.html")
def dataset_action_buttons(dataset):
    return {"dataset": dataset}


@register.inclusion_tag("core/includes/sample_filter_form.html", takes_context=True)
def sample_filter_form(
    context, dataset, filterset, reset_query, show_level_selector=False
):
    request = context["request"]
    return {
        "request": request,
        "dataset": dataset,
        "filter": filterset,
        "reset_query": reset_query,
        "show_level_selector": show_level_selector,
        "current_level": request.GET.get("level", "country"),
        "filters_open": bool(request.GET.get("filters_open")),
    }


@register.simple_tag
def home_page_url():
    from wagtail.models import Site

    site = Site.objects.filter(is_default_site=True).first()
    return site.root_page.url if site else "/"


@register.simple_tag
def dataset_index_url():
    page = DatasetIndexPage.objects.live().first()
    return page.url if page else None


@register.inclusion_tag("core/includes/explorer_nav_buttons.html", takes_context=True)
def explorer_nav_buttons(context, dataset, current_view):
    request = context["request"]
    # Carry over every param except 'level' and 'sort'/'order', which are
    # specific to one view and wouldn't make sense on the other.
    query = request.GET.copy()
    for key in ("level", "sort", "order", "page"):
        query.pop(key, None)
    query["set"] = dataset.dataset_id if dataset else ""
    return {
        "dataset": dataset,
        "current_view": current_view,
        "carried_query": query.urlencode(),
    }


@register.simple_tag
def contact_page_url():
    from core.models import ContactPage

    page = ContactPage.objects.live().first()
    return page.url if page else None


@register.simple_tag
def article_index_url():
    from articles.models import ArticleIndexPage

    page = ArticleIndexPage.objects.live().first()
    return page.url if page else None


@register.simple_tag
def privacy_page_url():
    from core.models import PrivacyPage

    page = PrivacyPage.objects.live().first()
    return page.url if page else None


@register.filter(name="markdown")
def markdown_filter(value):
    return render_markdown(value)
