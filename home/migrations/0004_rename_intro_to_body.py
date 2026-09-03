from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0003_homepage_intro"),
    ]
    operations = [
        migrations.RenameField(
            model_name="homepage",
            old_name="intro",
            new_name="body",
        ),
    ]