from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_privacypage"),
    ]
    operations = [
        migrations.RenameField(
            model_name="basepage",
            old_name="intro",
            new_name="body",
        ),
    ]