from typing import cast

from wagtail.models import Site
from wagtail.rich_text import RichText
from wagtail.test.utils import WagtailPageTestCase

from home.models import HomePage

from .factories import ArticleIndexPageFactory, ArticlePageFactory
from .models import ArticleIndexPage, ArticlePage


class ArticleIndexPageTests(WagtailPageTestCase):
    def setUp(self):
        root = Site.objects.get(is_default_site=True).root_page
        self.home = HomePage(title="Welcome")
        root.add_child(instance=self.home)
        self.home.save_revision().publish()

        self.index = cast(
            ArticleIndexPage,
            ArticleIndexPageFactory(title="Articles", parent=self.home),
        )
        self.index.save_revision().publish()

    def test_lists_only_published_articles(self):
        published = cast(
            ArticlePage,
            ArticlePageFactory(title="Published Article", parent=self.index),
        )
        published.save_revision().publish()

        unpublished = cast(
            ArticlePage,
            ArticlePageFactory(title="Draft Article", parent=self.index, live=False),
        )
        unpublished.save_revision()  # saved as a draft, never published

        response = self.client.get(self.index.url)
        self.assertContains(response, "Published Article")
        self.assertNotContains(response, "Draft Article")

    def test_shows_no_articles_message_when_empty(self):
        response = self.client.get(self.index.url)
        self.assertContains(response, "No articles have been published yet.")

    def test_summary_renders_as_formatted_html_not_raw_markup(self):
        article = cast(
            ArticlePage,
            ArticlePageFactory(
                title="Formatted Article",
                parent=self.index,
                summary=RichText("<p>A rich summary.</p>"),
            ),
        )
        article.save_revision().publish()

        response = self.client.get(self.index.url)
        self.assertContains(response, "<p>A rich summary.</p>", html=True)
        self.assertNotContains(response, "data-block-key")


class ArticlePageTests(WagtailPageTestCase):
    def setUp(self):
        root = Site.objects.get(is_default_site=True).root_page
        self.home = HomePage(title="Welcome")
        root.add_child(instance=self.home)
        self.home.save_revision().publish()

        self.index = cast(
            ArticleIndexPage,
            ArticleIndexPageFactory(title="Articles", parent=self.home),
        )
        self.index.save_revision().publish()

    def test_article_page_renders_intro(self):
        article = cast(
            ArticlePage,
            ArticlePageFactory(
                title="My Article",
                parent=self.index,
                intro=[("paragraph", RichText("<p>Article body text.</p>"))],
            ),
        )
        article.save_revision().publish()

        response = self.client.get(article.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Article body text.")

    def test_article_page_does_not_show_summary_on_its_own_page(self):
        article = cast(
            ArticlePage,
            ArticlePageFactory(
                title="My Article",
                parent=self.index,
                summary=RichText("<p>Summary text that should not appear here.</p>"),
            ),
        )
        article.save_revision().publish()

        response = self.client.get(article.url)
        self.assertNotContains(response, "Summary text that should not appear here.")

    def test_article_page_cannot_be_created_at_home(self):
        self.assertFalse(ArticlePage.can_create_at(self.home))

    def test_article_page_can_be_created_under_article_index(self):
        self.assertTrue(ArticlePage.can_create_at(self.index))


class NavigationArticlesLinkTests(WagtailPageTestCase):
    def test_nav_hides_articles_link_when_no_index_exists(self):
        root = Site.objects.get(is_default_site=True).root_page
        home = HomePage(title="Welcome")
        root.add_child(instance=home)
        home.save_revision().publish()

        response = self.client.get(home.url)
        self.assertNotContains(response, ">Articles<")

    def test_nav_shows_articles_link_when_index_exists(self):
        root = Site.objects.get(is_default_site=True).root_page
        home = HomePage(title="Welcome")
        root.add_child(instance=home)
        home.save_revision().publish()

        index = cast(
            ArticleIndexPage,
            ArticleIndexPageFactory(title="Articles", parent=home),
        )
        index.save_revision().publish()

        response = self.client.get(home.url)
        self.assertContains(response, 'href="' + index.url + '"')
