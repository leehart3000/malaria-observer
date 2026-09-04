from django.db import migrations


def create_homepage(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    Page = apps.get_model("wagtailcore.Page")
    Site = apps.get_model("wagtailcore.Site")
    Locale = apps.get_model("wagtailcore.Locale")
    HomePage = apps.get_model("home.HomePage")

    page_content_type = ContentType.objects.get(
        model="page", app_label="wagtailcore"
    )
    Page.objects.filter(
        content_type=page_content_type, slug="home", depth=2
    ).delete()

    homepage_content_type, __ = ContentType.objects.get_or_create(
        model="homepage", app_label="home"
    )

    default_locale, __ = Locale.objects.get_or_create(
        language_code="en",
        defaults={"language_code": "en"},
    )

    homepage = HomePage.objects.create(
        title="Home",
        draft_title="Home",
        slug="home",
        content_type=homepage_content_type,
        locale=default_locale,
        path="00010001",
        depth=2,
        numchild=0,
        url_path="/home/",
    )

    Site.objects.create(hostname="localhost", root_page=homepage, is_default_site=True)


def remove_homepage(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    HomePage = apps.get_model("home.HomePage")

    HomePage.objects.filter(slug="home", depth=2).delete()
    ContentType.objects.filter(model="homepage", app_label="home").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_homepage, remove_homepage),
    ]