import logging

from django.apps import apps
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpRequest
from django.template.response import TemplateResponse
from wagtail.models import Page

logger = logging.getLogger(__name__)

CONTENT_TYPE_MODELS = {
    "articles": "articles.ArticlePage",
    "datasets": "datasets.DatasetPage",
}


def search(request: HttpRequest) -> TemplateResponse:
    search_query = request.GET.get("query", None)
    content_type = request.GET.get("type", None)
    page = request.GET.get("page", 1)

    queryset = Page.objects.live()
    if content_type:
        model_path = CONTENT_TYPE_MODELS.get(content_type)
        if model_path:
            queryset = queryset.type(apps.get_model(model_path))

    if search_query:
        search_results = queryset.search(search_query)
    else:
        search_results = Page.objects.none()

    paginator = Paginator(search_results, 10)
    try:
        search_results = paginator.page(page)
    except PageNotAnInteger:
        search_results = paginator.page(1)
    except EmptyPage:
        search_results = paginator.page(paginator.num_pages)

    return TemplateResponse(
        request,
        "search/search.html",
        {
            "search_query": search_query,
            "search_results": search_results,
            "content_type": content_type,
        },
    )
