from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_user_role_facultyprofile_studentprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="te_result",
            field=models.CharField(
                blank=True,
                help_text="Third-year (TE) examination result / percentage.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="exam_seat_number",
            field=models.CharField(
                blank=True,
                help_text="University examination seat number.",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="photo",
            field=models.ImageField(
                blank=True,
                help_text="Passport-style photograph used in the log book.",
                null=True,
                upload_to="student_photos/",
            ),
        ),
    ]
