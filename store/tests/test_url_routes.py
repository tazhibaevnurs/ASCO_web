"""
Смоук-тесты: каждый зарегистрированный URL получает хотя бы один запрос.

Запуск:
  python manage.py test store.tests.test_url_routes

Для локального запуска без PostgreSQL: USE_SQLITE=1 (см. ecom_prj/settings.py).
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from blog import models as blog_models
from customer import models as customer_models
from store import models as store_models
from userauths import models as userauths_models
from vendor import models as vendor_models


User = get_user_model()

PAYMENT_SETTINGS = dict(
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
    # Тесты не требуют argon2-cffi (в production может быть Argon2 в PASSWORD_HASHERS).
    PASSWORD_HASHERS=[
        "django.contrib.auth.hashers.PBKDF2PasswordHasher",
        "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    ],
)


@override_settings(**PAYMENT_SETTINGS)
class ProjectURLTestCase(TestCase):
    """Базовый кейс: фикстуры БД + клиент без CSRF."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.customer = User.objects.create_user(
            "buyer_username",
            email="buyer@example.com",
            password="test-pass-123",
            first_name="Buyer",
            last_name="One",
        )
        userauths_models.Profile.objects.get_or_create(
            user=cls.customer,
            defaults={"user_type": "guest", "full_name": "Buyer One"},
        )

        cls.manager = User.objects.create_user(
            "manager_username",
            email="manager@example.com",
            password="test-pass-123",
            first_name="Mgr",
            last_name="One",
            is_staff=True,
        )
        userauths_models.Profile.objects.update_or_create(
            user=cls.manager,
            defaults={"user_type": "manager", "full_name": "Manager One"},
        )

        cls.superuser = User.objects.create_user(
            "super_username",
            email="super@example.com",
            password="test-pass-123",
            first_name="Super",
            last_name="One",
            is_staff=True,
            is_superuser=True,
        )
        userauths_models.Profile.objects.update_or_create(
            user=cls.superuser,
            defaults={"user_type": "superadmin", "full_name": "Super One"},
        )

        cls.category = store_models.Category.objects.create(
            title="Test Cat",
            slug="test-cat",
        )
        cls.product = store_models.Product.objects.create(
            name="Test Product",
            slug="test-product",
            description="<p>ok</p>",
            category=cls.category,
            price=Decimal("10.00"),
            stock=5,
            shipping=Decimal("1.00"),
            status="Published",
            vendor=cls.manager,
            created_by=cls.manager,
        )

        cls.address = customer_models.Address.objects.create(
            user=cls.customer,
            full_name="Buyer One",
            email="buyer@example.com",
            mobile="+996 700 000 000",
            country="United States",
            address="Line 1",
        )

        cls.order = store_models.Order.objects.create(
            customer=cls.customer,
            address=cls.address,
            sub_total=Decimal("10.00"),
            shipping=Decimal("1.00"),
            tax=Decimal("0.00"),
            service_fee=Decimal("0.00"),
            total=Decimal("11.00"),
            payment_status="Processing",
        )
        cls.order_item = store_models.OrderItem.objects.create(
            order=cls.order,
            product=cls.product,
            qty=1,
            price=Decimal("10.00"),
            sub_total=Decimal("10.00"),
            shipping=Decimal("1.00"),
            tax=Decimal("0.00"),
            total=Decimal("11.00"),
            initial_total=Decimal("11.00"),
            vendor=cls.manager,
        )
        cls.order.vendors.add(cls.manager)

        blog_cat = blog_models.Category.objects.create(name="News", slug="news")
        cls.blog = blog_models.Blog.objects.create(
            title="Hello",
            slug="hello-post",
            author=cls.customer,
            status="Published",
            category=blog_cat,
        )

        cls.coupon = store_models.Coupon.objects.create(
            vendor=cls.manager,
            code="SAVE10",
            discount=10,
        )

    def setUp(self):
        super().setUp()
        self.client = Client(enforce_csrf_checks=False)


class TestPublicAndStoreURLs(ProjectURLTestCase):
    def test_admin_redirects(self):
        r = self.client.get("/admin/")
        self.assertIn(r.status_code, (301, 302))

    def test_manager_login_get(self):
        r = self.client.get(reverse("manager-login"))
        self.assertEqual(r.status_code, 200)

    def test_store_index(self):
        self.assertEqual(self.client.get(reverse("store:index")).status_code, 200)

    def test_blog_create_comment_get_not_allowed(self):
        url = reverse("blog:create_comment", args=[self.blog.slug])
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_store_shop_and_search(self):
        self.assertEqual(self.client.get(reverse("store:shop")).status_code, 200)
        self.assertEqual(self.client.get(reverse("store:search")).status_code, 200)

    def test_search_suggestions_json(self):
        r = self.client.get(reverse("store:search_suggestions"), {"q": "Test"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/json")

    def test_category(self):
        url = reverse("store:category", kwargs={"slug": self.category.slug})
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_category_legacy_redirect(self):
        url = reverse("store:category_legacy", args=[self.category.pk])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 301)
        self.assertIn(self.category.slug, r.url)

    def test_api_ai_generate_requires_login(self):
        r = self.client.post(
            "/api/ai/generate/",
            data=json.dumps({"prompt": "x"}),
            content_type="application/json",
        )
        self.assertIn(r.status_code, (302, 401))

    def test_api_ai_generate_ok(self):
        self.client.force_login(self.customer)
        r = self.client.post(
            "/api/ai/generate/",
            data=json.dumps({"prompt": "hello"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_stripe_webhook_disabled_without_secret(self):
        r = self.client.post("/webhooks/stripe/", b"{}", content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_product_detail(self):
        url = reverse("store:product_detail", args=[self.product.slug])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_cart(self):
        self.assertEqual(self.client.get(reverse("store:cart")).status_code, 200)

    def test_checkout_requires_owner(self):
        url = reverse("store:checkout", args=[self.order.order_id])
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_checkout_ok_when_logged_in(self):
        self.client.force_login(self.customer)
        url = reverse("store:checkout", args=[self.order.order_id])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_update_checkout_phone_post(self):
        self.client.force_login(self.customer)
        url = reverse("store:update_checkout_phone", args=[self.order.order_id])
        r = self.client.post(url, {"phone": "0700123456"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_coupon_apply_get_redirect(self):
        self.client.force_login(self.customer)
        url = reverse("store:coupon_apply", args=[self.order.order_id])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 302)

    def test_payment_status_requires_owner(self):
        url = reverse("store:payment_status", args=[self.order.order_id])
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_filter_products(self):
        r = self.client.get(reverse("store:filter_products"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/json")

    def test_add_to_cart_json(self):
        cart_id = "test-cart-uuid-1"
        self.client.session["cart_id"] = cart_id
        self.client.session.save()
        url = reverse("store:add_to_cart")
        r = self.client.get(
            url,
            {
                "id": self.product.pk,
                "qty": 1,
                "cart_id": cart_id,
                "color": "red",
                "size": "M",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/json")

    def test_add_to_cart_new_session_gets_server_cart_id(self):
        """Первая привязка корзины — только серверный UUID (защита от подстановки чужого cart_id)."""
        url = reverse("store:add_to_cart")
        r = self.client.get(
            url,
            {
                "id": self.product.pk,
                "qty": 1,
                "cart_id": "attacker-trying-foreign-cart",
                "color": "red",
                "size": "M",
            },
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("cart_id", data)
        self.assertNotEqual(data["cart_id"], "attacker-trying-foreign-cart")
        self.assertEqual(self.client.session.get("cart_id"), data["cart_id"])

    def test_delete_cart_item(self):
        self.client.get(reverse("store:index"))
        cart_id = "test-cart-uuid-2"
        s = self.client.session
        s["cart_id"] = cart_id
        s.save()
        line = store_models.Cart.objects.create(
            cart_id=cart_id,
            product=self.product,
            qty=1,
            price=self.product.price,
            color="c",
            size="s",
            sub_total=self.product.price,
            shipping=Decimal("0"),
            total=self.product.price,
        )
        url = reverse("store:delete_cart_item")
        r = self.client.get(
            url,
            {"id": self.product.pk, "item_id": line.pk, "cart_id": cart_id},
        )
        self.assertEqual(r.status_code, 200)

    @mock.patch("store.views.stripe.checkout.Session.create")
    def test_stripe_payment_post_json(self, m_create):
        m_create.return_value = SimpleNamespace(id="cs_test_123")
        self.client.force_login(self.customer)
        url = reverse("store:stripe_payment", args=[self.order.order_id])
        r = self.client.post(url, {}, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("sessionId"), "cs_test_123")

    @mock.patch("store.stripe_fulfillment.stripe.checkout.Session.retrieve")
    def test_stripe_payment_verify_get(self, m_ret):
        m_ret.return_value = SimpleNamespace(
            payment_status="unpaid",
            metadata={
                "order_id": str(self.order.order_id),
                "order_pk": str(self.order.pk),
            },
            amount_total=1100,
        )
        self.client.force_login(self.customer)
        url = reverse("store:stripe_payment_verify", args=[self.order.order_id])
        r = self.client.get(url, {"session_id": "cs_x"})
        self.assertEqual(r.status_code, 302)

    @mock.patch("store.views.requests.get")
    @mock.patch("store.views.get_paypal_access_token", return_value="test_token")
    def test_paypal_payment_verify_get(self, m_token, m_get):
        del m_token  # patch object for get_paypal_access_token
        m_get.return_value = mock.Mock(status_code=404)
        self.client.force_login(self.customer)
        url = reverse("store:paypal_payment_verify", args=[self.order.order_id])
        r = self.client.get(url, {"transaction_id": "fake"})
        self.assertEqual(r.status_code, 302)

    def test_razorpay_payment_verify_get_redirect(self):
        self.client.force_login(self.customer)
        url = reverse("store:razorpay_payment_verify", args=[self.order.order_id])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 302)

    @mock.patch("store.views.requests.get")
    def test_paystack_payment_verify(self, m_get):
        m_get.return_value = mock.Mock(
            status_code=200,
            json=lambda: {"status": False},
        )
        self.client.force_login(self.customer)
        url = reverse("store:paystack_payment_verify", args=[self.order.order_id])
        r = self.client.get(url, {"reference": "ref"})
        self.assertEqual(r.status_code, 302)

    @mock.patch("store.views.requests.get")
    def test_flutterwave_payment_callback(self, m_get):
        m_get.return_value = mock.Mock(status_code=404)
        self.client.force_login(self.customer)
        url = reverse("store:flutterwave_payment_callback", args=[self.order.order_id])
        r = self.client.get(url, {"tx_ref": "x", "status": "ok"})
        self.assertEqual(r.status_code, 302)

    def test_order_tracker_page_get(self):
        self.assertEqual(
            self.client.get(reverse("store:order_tracker_page")).status_code, 200
        )

    def test_order_tracker_page_post_redirect(self):
        r = self.client.post(
            reverse("store:order_tracker_page"),
            {"item_id": self.order_item.item_id},
        )
        self.assertEqual(r.status_code, 302)

    def test_order_tracker_detail(self):
        self.client.force_login(self.customer)
        url = reverse("store:order_tracker_detail", args=[self.order_item.item_id])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_static_pages(self):
        for name in (
            "store:about",
            "store:contact",
            "store:faqs",
            "store:privacy_policy",
            "store:terms_conditions",
        ):
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_password_reset_root_routes(self):
        self.assertEqual(self.client.get(reverse("password_reset")).status_code, 200)
        self.assertEqual(self.client.get(reverse("password_reset_done")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("password_reset_complete")).status_code, 200
        )
        u = reverse(
            "password_reset_confirm",
            kwargs={"uidb64": "MQ", "token": "dead-beef"},
        )
        self.assertIn(self.client.get(u).status_code, (200, 302))

    def test_sitemap_robots_favicon(self):
        self.assertEqual(
            self.client.get(
                reverse("django.contrib.sitemaps.views.sitemap")
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get("/robots.txt").status_code, 200)
        self.assertIn(self.client.get("/favicon.ico").status_code, (301, 302))

    def test_google_verification_file(self):
        self.assertEqual(
            self.client.get("/google34daf5010f2256e5.html").status_code, 200
        )

    def test_ckeditor5_include(self):
        log = logging.getLogger("django.request")
        prev = log.level
        log.setLevel(logging.ERROR)
        try:
            r = self.client.get("/ckeditor5/")
        finally:
            log.setLevel(prev)
        self.assertIn(r.status_code, (200, 302, 404))


class TestUserauthsURLs(ProjectURLTestCase):
    def test_sign_up_redirect_when_disabled(self):
        r = self.client.get(reverse("userauths:sign-up"))
        self.assertEqual(r.status_code, 302)

    def test_sign_in_get(self):
        self.assertEqual(self.client.get(reverse("userauths:sign-in")).status_code, 200)

    def test_sign_out(self):
        self.client.force_login(self.customer)
        r = self.client.get(reverse("userauths:sign-out"))
        self.assertEqual(r.status_code, 302)

    def test_verify_email_invalid_token(self):
        url = reverse(
            "userauths:verify-email",
            kwargs={"uidb64": "xx", "token": "yy-yy"},
        )
        self.assertEqual(self.client.get(url).status_code, 302)

class TestCustomerURLs(ProjectURLTestCase):
    def test_customer_routes_redirect_anonymous(self):
        names = [
            "customer:dashboard",
            "customer:orders",
            "customer:wishlist",
            "customer:addresses",
            "customer:notis",
            "customer:profile",
            "customer:change_password",
        ]
        for name in names:
            with self.subTest(name=name):
                r = self.client.get(reverse(name))
                self.assertEqual(r.status_code, 302, msg=name)

    def test_customer_order_detail_authenticated(self):
        self.client.force_login(self.customer)
        url = reverse("customer:order_detail", args=[self.order.order_id])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_wishlist_public_endpoints(self):
        self.assertEqual(
            self.client.get(reverse("customer:sync_wishlist_from_storage")).status_code,
            200,
        )
        url = reverse("customer:toggle_wishlist", args=[self.product.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_add_to_wishlist_legacy(self):
        url = reverse("customer:add_to_wishlist", args=[self.product.pk])
        self.assertEqual(self.client.get(url).status_code, 200)


class TestVendorURLs(ProjectURLTestCase):
    def test_vendor_anonymous_redirect(self):
        r = self.client.get(reverse("vendor:dashboard"))
        self.assertEqual(r.status_code, 302)

    def test_vendor_dashboard_as_manager(self):
        self.client.force_login(self.manager)
        self.assertEqual(
            self.client.get(reverse("vendor:dashboard")).status_code, 200
        )
        self.assertEqual(self.client.get(reverse("vendor:products")).status_code, 200)
        self.assertEqual(self.client.get(reverse("vendor:orders")).status_code, 200)

    def test_vendor_order_detail(self):
        self.client.force_login(self.manager)
        url = reverse("vendor:order_detail", args=[self.order.order_id])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_vendor_order_item_detail(self):
        self.client.force_login(self.manager)
        url = reverse(
            "vendor:order_item_detail",
            args=[self.order.order_id, self.order_item.item_id],
        )
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_vendor_coupons_and_reviews(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("vendor:coupons")).status_code, 200)
        self.assertEqual(self.client.get(reverse("vendor:reviews")).status_code, 200)

    def test_vendor_categories_profile(self):
        self.client.force_login(self.manager)
        self.assertEqual(
            self.client.get(reverse("vendor:categories")).status_code, 200
        )
        self.assertEqual(self.client.get(reverse("vendor:profile")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("vendor:change_password")).status_code, 200
        )

    def test_vendor_create_product_get(self):
        self.client.force_login(self.manager)
        self.assertEqual(
            self.client.get(reverse("vendor:create_product")).status_code, 200
        )

    def test_vendor_update_product_get(self):
        self.client.force_login(self.manager)
        url = reverse("vendor:update_product", args=[self.product.pk])
        self.assertEqual(self.client.get(url).status_code, 200)


class TestBlogURLs(ProjectURLTestCase):
    def test_blog_list(self):
        self.assertEqual(self.client.get(reverse("blog:blog_list")).status_code, 200)

    def test_blog_detail(self):
        url = reverse("blog:blog_detail", args=[self.blog.slug])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_like_blog_requires_login(self):
        r = self.client.post(reverse("blog:like_blog"), {"blog_id": self.blog.pk})
        self.assertEqual(r.status_code, 302)

    def test_like_blog_authenticated(self):
        self.client.force_login(self.customer)
        r = self.client.post(reverse("blog:like_blog"), {"blog_id": self.blog.pk})
        self.assertIn(r.status_code, (200, 302))


class TestCreateOrderAndDelivery(ProjectURLTestCase):
    def test_create_order_requires_login(self):
        r = self.client.post(reverse("store:create_order"), {"address": self.address.pk})
        self.assertEqual(r.status_code, 302)

    def test_create_order_authenticated(self):
        cart_id = "order-test-cart"
        self.client.session["cart_id"] = cart_id
        self.client.session.save()
        store_models.Cart.objects.create(
            cart_id=cart_id,
            product=self.product,
            qty=1,
            price=self.product.price,
            color="c",
            size="s",
            sub_total=self.product.price,
            shipping=Decimal("0"),
            total=self.product.price,
            user=self.customer,
        )
        self.client.force_login(self.customer)
        r = self.client.post(
            reverse("store:create_order"),
            {"address": str(self.address.pk)},
        )
        self.assertEqual(r.status_code, 302)

    def test_delivery_request_post_redirect(self):
        cart_id = "delivery-cart"
        self.client.session["cart_id"] = cart_id
        self.client.session.save()
        store_models.Cart.objects.create(
            cart_id=cart_id,
            product=self.product,
            qty=1,
            price=self.product.price,
            color="c",
            size="s",
            sub_total=self.product.price,
            shipping=Decimal("0"),
            total=self.product.price,
        )
        r = self.client.post(
            reverse("store:delivery_request"),
            {
                "full_name": "Guest",
                "phone": "+996700111222",
                "address": "Bishkek",
            },
        )
        self.assertEqual(r.status_code, 302)


class TestVendorMutationsAndCustomerExtras(ProjectURLTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.manager)

    def test_vendor_update_order_status_get_redirect(self):
        url = reverse("vendor:update_order_status", args=[self.order.order_id])
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_vendor_update_order_item_status_get_redirect(self):
        url = reverse(
            "vendor:update_order_item_status",
            args=[self.order.order_id, self.order_item.item_id],
        )
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_vendor_coupon_mutations_and_create(self):
        self.client.post(
            reverse("vendor:update_coupon", args=[self.coupon.pk]),
            {"coupon_code": "SAVE10"},
            follow=False,
        )
        self.assertEqual(self.client.get(reverse("vendor:coupons")).status_code, 200)
        self.client.post(
            reverse("vendor:create_coupon"),
            {"coupon_code": "NEW5", "coupon_discount": "5"},
        )
        self.assertEqual(self.client.get(reverse("vendor:coupons")).status_code, 200)

    def test_vendor_update_reply(self):
        review = store_models.Review.objects.create(
            user=self.customer,
            product=self.product,
            review="nice",
            rating=5,
            active=True,
        )
        url = reverse("vendor:update_reply", args=[review.pk])
        r = self.client.post(url, {"reply": "Thanks"})
        self.assertEqual(r.status_code, 302)

    def test_vendor_notis_and_mark_seen(self):
        n = vendor_models.Notifications.objects.create(
            user=self.manager,
            type="New Order",
            seen=False,
        )
        url = reverse("vendor:mark_noti_seen", args=[n.pk])
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_vendor_category_edit_delete_get(self):
        c = store_models.Category.objects.create(title="Tmp", slug="tmp-cat-v")
        self.client.force_login(self.superuser)
        self.assertEqual(
            self.client.get(reverse("vendor:category_edit", args=[c.pk])).status_code,
            200,
        )
        # Удаление только POST; GET — редирект с сообщением об ошибке метода
        self.assertEqual(
            self.client.get(reverse("vendor:category_delete", args=[c.pk])).status_code,
            302,
        )

    def test_vendor_delete_coupon_url(self):
        c = store_models.Coupon.objects.create(
            vendor=self.manager, code="TMPDEL", discount=1
        )
        self.client.get(reverse("vendor:delete_coupon", args=[c.pk]))

    def test_vendor_json_deletes(self):
        v_items = store_models.Variant.objects.create(product=self.product, name="Color")
        vi = store_models.VariantItem.objects.create(
            variant=v_items, title="Red", content="red"
        )
        self.client.get(
            reverse(
                "vendor:delete_variants_items",
                args=[v_items.pk, vi.pk],
            )
        )
        v_only = store_models.Variant.objects.create(product=self.product, name="Size")
        self.client.get(
            reverse("vendor:delete_variants", args=[self.product.pk, v_only.pk])
        )
        g = store_models.Gallery.objects.create(product=self.product)
        self.client.get(
            reverse(
                "vendor:delete_product_image",
                args=[self.product.pk, g.pk],
            )
        )


class TestCustomerAddressAndNoti(ProjectURLTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.customer)

    def test_addresses_and_create(self):
        self.assertEqual(
            self.client.get(reverse("customer:addresses")).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("customer:address_create")).status_code, 200
        )

    def test_address_detail_and_delete(self):
        url = reverse("customer:address_detail", args=[self.address.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        a2 = customer_models.Address.objects.create(
            user=self.customer,
            full_name="Second",
            address="A",
        )
        self.client.get(reverse("customer:delete_address", args=[a2.pk]))

    def test_order_item_detail(self):
        url = reverse(
            "customer:order_item_detail",
            args=[self.order.order_id, self.order_item.item_id],
        )
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_remove_wishlist_and_notis(self):
        customer_models.Wishlist.objects.create(
            user=self.customer, product=self.product
        )
        w = customer_models.Wishlist.objects.filter(
            user=self.customer, product=self.product
        ).first()
        self.client.get(reverse("customer:remove_from_wishlist", args=[w.pk]))
        n = customer_models.Notifications.objects.create(
            user=self.customer,
            type="New Order",
            seen=False,
        )
        self.client.get(reverse("customer:mark_noti_seen", args=[n.pk]))


class TestBlogCreateComment(ProjectURLTestCase):
    def test_create_comment_post(self):
        r = self.client.post(
            reverse("blog:create_comment", args=[self.blog.slug]),
            {
                "full_name": "Reader",
                "email": "r@example.com",
                "content": "Nice",
            },
        )
        self.assertEqual(r.status_code, 302)
