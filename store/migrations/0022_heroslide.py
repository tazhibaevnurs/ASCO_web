# Generated manually for Hero banner admin

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0021_alter_order_payment_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="HeroSlide",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(blank=True, null=True, upload_to="hero", verbose_name="Изображение")),
                ("title", models.CharField(default="Техника и гаджеты", max_length=200, verbose_name="Заголовок")),
                ("subtitle", models.CharField(blank=True, default="Лучшие цены и бесплатная доставка", max_length=300, verbose_name="Подзаголовок")),
                ("button_text", models.CharField(blank=True, default="В магазин", max_length=100, verbose_name="Текст кнопки")),
                ("button_url", models.CharField(blank=True, default="/shop/", max_length=255, verbose_name="Ссылка кнопки")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("is_active", models.BooleanField(default=True, verbose_name="Показывать")),
            ],
            options={
                "ordering": ["order"],
                "verbose_name": "Слайд Hero",
                "verbose_name_plural": "Слайды Hero",
            },
        ),
    ]
