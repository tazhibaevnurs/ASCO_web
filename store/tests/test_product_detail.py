"""
Карточка товара: 404 вместо 500, шаблон при отзыве без пользователя.
"""
from __future__ import annotations

from decimal import Decimal

from django.test import Client, TestCase, override_settings

from store import models as store_models
from userauths import models as userauths_models
from django.contrib.auth import get_user_model

User = get_user_model()

_PAYMENT_STUB = dict(
    STRIPE_SECRET_KEY="sk_test_dummy",
    STRIPE_PUBLIC_KEY="pk_test_dummy",
    PAYPAL_CLIENT_ID="cid",
    PAYPAL_SECRET_ID="sec",
    RAZORPAY_KEY_ID="rk",
    RAZORPAY_KEY_SECRET="rs",
    PAYSTACK_PUBLIC_KEY="pk",
    PAYSTACK_PRIVATE_KEY="psk",
    FLUTTERWAVE_PUBLIC_KEY="fk",
    FLUTTERWAVE_PRIVATE_KEY="fsk",
    FROM_EMAIL="orders@test.local",
    DEFAULT_FROM_EMAIL="orders@test.local",
    REGISTRATION_ENABLED=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PASSWORD_HASHERS=[
        "django.contrib.auth.hashers.PBKDF2PasswordHasher",
        "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    ],
)


@override_settings(**_PAYMENT_STUB)
class ProductDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user(
            "pd_mgr",
            email="pd_mgr@example.com",
            password="test-pass-123",
        )
        userauths_models.Profile.objects.update_or_create(
            user=cls.manager,
            defaults={"user_type": "manager", "full_name": "PD Mgr"},
        )
        cls.cat = store_models.Category.objects.create(title="Microwave", slug="micro")
        cls.product = store_models.Product.objects.create(
            name="Midea Microwave",
            slug="mikrovolnovaya-pech-midea",
            description="<p>Test</p>",
            category=cls.cat,
            price=Decimal("5490.00"),
            stock=3,
            status="Published",
            vendor=cls.manager,
            created_by=cls.manager,
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)

    def test_product_detail_ok(self):
        from django.urls import reverse

        url = reverse("store:product_detail", kwargs={"slug": self.product.slug})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Midea Microwave", html=False)

    def test_product_detail_404_unknown_slug(self):
        from django.urls import reverse

        url = reverse("store:product_detail", kwargs={"slug": "no-such-product-slug-xyz"})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_product_detail_with_review_guest_user(self):
        """Отзыв с user=NULL не должен ронять шаблон (VariableDoesNotExist / 500)."""
        from django.urls import reverse

        store_models.Review.objects.create(
            user=None,
            product=self.product,
            review="Норм",
            rating=4,
            active=True,
        )
        url = reverse("store:product_detail", kwargs={"slug": self.product.slug})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Гость", html=False)
        self.assertContains(r, "Норм", html=False)

    def test_product_detail_null_stock_returns_200(self):
        """NULL в product.stock ломал max(1, None) в представлении → TypeError / 500."""
        from django.urls import reverse

        p = store_models.Product.objects.create(
            name="Stock NULL product",
            slug="stock-null-test-product",
            description="<p>x</p>",
            category=self.cat,
            price=Decimal("100.00"),
            stock=None,
            status="Published",
            vendor=self.manager,
            created_by=self.manager,
        )
        url = reverse("store:product_detail", kwargs={"slug": p.slug})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Stock NULL product", html=False)
        self.assertContains(r, "Нет в наличии", html=False)
