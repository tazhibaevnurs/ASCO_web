from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("userauths", "0006_alter_profile_user_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="subscription_plan",
            field=models.CharField(
                choices=[("free", "Free"), ("pro", "Pro")],
                default="free",
                help_text="Лимиты AI и т.п. (free / pro).",
                max_length=16,
            ),
        ),
    ]
