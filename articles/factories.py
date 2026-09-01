import factory
import wagtail_factories

from .models import ArticleIndexPage, ArticlePage


class ArticleIndexPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = ArticleIndexPage


class ArticlePageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = ArticlePage

    title = factory.Sequence(lambda n: f"Article {n}")
