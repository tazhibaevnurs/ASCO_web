from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0023_alter_category_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="StripeWebhookEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("event_id", models.CharField(db_index=True, max_length=255, unique=True)),
                ("event_type", models.CharField(blank=True, default="", max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Stripe webhook event",
                "verbose_name_plural": "Stripe webhook events",
            },
        ),
    ]
