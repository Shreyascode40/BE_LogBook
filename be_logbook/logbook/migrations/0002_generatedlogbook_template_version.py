from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("logbook", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="generatedlogbook",
            name="template_version",
            field=models.CharField(
                blank=True,
                help_text="Version / identifier of the official 40-page template used.",
                max_length=40,
            ),
        ),
    ]
