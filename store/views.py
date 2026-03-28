import hmac

from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives, send_mail
from django.utils import timezone

from decimal import Decimal
from urllib.parse import urlencode
import logging
import uuid
import requests
import stripe
from plugin.service_fee import calculate_service_fee
import razorpay
from razorpay.errors import SignatureVerificationError
from django_ratelimit.decorators import ratelimit

from plugin.paginate_queryset import paginate_queryset
from plugin.input_validation import (
    MAX_CART_COLOR_SIZE_LEN,
    MAX_CONTACT_FIELD,
    clamp_text,
    parse_bounded_decimal,
    parse_category_slug,
    parse_filter_tokens,
    parse_int_id_list,
    parse_product_qty,
    parse_positive_int,
    parse_rating_list,
    parse_search_q,
)
from store import models as store_models
from store.forms import ContactForm
from store import order_access
from store.cart_utils import clear_cart_items
from store.stripe_fulfillment import try_fulfill_stripe_checkout_session
from customer import models as customer_models
from vendor import models as vendor_models
from userauths import models as userauths_models
from plugin.tax_calculation import tax_calculation
from plugin.exchange_rate import convert_usd_to_inr, convert_usd_to_kobo, convert_usd_to_ngn, get_usd_to_ngn_rate

logger = logging.getLogger(__name__)


def _apply_search(queryset, query):
    """Применяет поиск по названию товара (подстрока, без учёта регистра)."""
    if not query or not query.strip():
        return queryset
    return queryset.filter(name__icontains=query.strip())


def search_suggestions(request):
    """JSON-ответ для подсказок поиска: превью, название, цена, ссылка на товар."""
    q = parse_search_q(request.GET.get("q"))
    if not q:
        return JsonResponse({"results": []})
    products = store_models.Product.objects.filter(status="Published")
    products = _apply_search(products, q)[:8]
    results = []
    for p in products:
        results.append({
            "name": p.name,
            "url": reverse("store:product_detail", args=[p.slug]),
            "image": request.build_absolute_uri(p.image.url) if p.image else None,
            "price": str(p.price),
            "category": p.category.title if p.category else "",
        })
    return JsonResponse({"results": results})


# stripe.api_key = settings.STRIPE_SECRET_KEY
# razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def index(request):
    # Если в URL есть поисковый запрос — показываем результаты на странице магазина
    q_redirect = parse_search_q(request.GET.get("q"))
    if q_redirect:
        from urllib.parse import urlencode

        return redirect(
            "{}?{}".format(reverse("store:search"), urlencode({"q": q_redirect}))
        )
    products = store_models.Product.objects.filter(status="Published")
    categories = store_models.Category.objects.all()
    hero_slides = store_models.HeroSlide.objects.filter(is_active=True).order_by("order")
    context = {
        "products": products,
        "categories": categories,
        "hero_slides": hero_slides,
    }
    return render(request, "store/index.html", context)

def _shop_queryset(request):
    """Единая база запроса для магазина: q, category, min_price, max_price, sort."""
    qs = store_models.Product.objects.filter(status="Published")

    q = parse_search_q(request.GET.get("q", ""))
    if q:
        qs = qs.filter(name__icontains=q)

    category = parse_category_slug(request.GET.get("category"))
    if category:
        qs = qs.filter(category__slug=category)
    categories_ids = parse_int_id_list(request.GET.getlist("categories[]"))
    if categories_ids:
        qs = qs.filter(category__id__in=categories_ids)

    min_price = parse_bounded_decimal(request.GET.get("min_price"))
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    max_price = parse_bounded_decimal(request.GET.get("max_price"))
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)

    sort = (request.GET.get("sort") or "").strip()
    if sort not in ("price_asc", "price_desc", "newest", "name", ""):
        sort = ""
    if sort == "price_asc":
        qs = qs.order_by("price")
    elif sort == "price_desc":
        qs = qs.order_by("-price")
    elif sort == "newest":
        qs = qs.order_by("-date")
    elif sort == "name":
        qs = qs.order_by("name")
    else:
        price_order = (request.GET.get("prices") or "").strip()
        if price_order not in ("lowest", "highest"):
            price_order = ""
        if price_order == "lowest":
            qs = qs.order_by("-price")
        elif price_order == "highest":
            qs = qs.order_by("price")

    return qs


def shop(request):
    products_list = _shop_queryset(request)
    categories = store_models.Category.objects.all()
    colors = store_models.VariantItem.objects.filter(variant__name='Color').values('title', 'content').distinct()
    sizes = store_models.VariantItem.objects.filter(variant__name='Size').values('title', 'content').distinct()
    item_display = [
        {"id": "1", "value": 1},
        {"id": "2", "value": 2},
        {"id": "3", "value": 3},
        {"id": "40", "value": 40},
        {"id": "50", "value": 50},
        {"id": "100", "value": 100},
    ]
    ratings = [
        {"id": "1", "value": "★☆☆☆☆"},
        {"id": "2", "value": "★★☆☆☆"},
        {"id": "3", "value": "★★★☆☆"},
        {"id": "4", "value": "★★★★☆"},
        {"id": "5", "value": "★★★★★"},
    ]
    prices = [
        {"id": "lowest", "value": "От высокой к низкой"},
        {"id": "highest", "value": "От низкой к высокой"},
    ]

    products = paginate_queryset(request, products_list, 9)

    # HTMX: вернуть только фрагмент со списком товаров
    if request.headers.get("HX-Request"):
        from store.context import default as store_default
        wishlist_context = store_default(request) if hasattr(request, "user") else {}
        context = {
            "products": products,
            "wishlist_product_ids": wishlist_context.get("wishlist_product_ids", set()),
            "product_count": products_list.count(),
        }
        return render(request, "store/product_list_partial.html", context)

    # Чипсы активных фильтров (для снятия по клику)
    from urllib.parse import urlencode
    filter_chips = []
    get = request.GET.copy()
    if get.get("q"):
        g = get.copy()
        g.pop("q", None)
        filter_chips.append({"type": "q", "label": get.get("q"), "remove_url": request.path + ("?" + g.urlencode() if g else "")})
    for cat_id in get.getlist("categories[]"):
        cat = store_models.Category.objects.filter(id=cat_id).first()
        if cat:
            g = get.copy()
            g.setlist("categories[]", [x for x in g.getlist("categories[]") if x != cat_id])
            filter_chips.append({"type": "category", "label": cat.title, "remove_url": request.path + ("?" + g.urlencode() if g else "")})
    if get.get("prices"):
        p_label = next((x["value"] for x in prices if str(x["id"]) == str(get.get("prices"))), None)
        if p_label:
            g = get.copy()
            g.pop("prices", None)
            filter_chips.append({"type": "price", "label": p_label, "remove_url": request.path + ("?" + g.urlencode() if g else "")})
    sort_labels = {"newest": "Сначала новинки", "price_asc": "Сначала дешевые", "price_desc": "Сначала дорогие", "name": "По названию"}
    if get.get("sort") and get.get("sort") in sort_labels:
        g = get.copy()
        g.pop("sort", None)
        filter_chips.append({"type": "sort", "label": sort_labels[get.get("sort")], "remove_url": request.path + ("?" + g.urlencode() if g else "")})

    context = {
        "products": products,
        "products_list": products_list,
        "categories": categories,
        "colors": colors,
        "sizes": sizes,
        "item_display": item_display,
        "ratings": ratings,
        "prices": prices,
        "filter_chips": filter_chips,
    }
    return render(request, "store/shop.html", context)

def category_legacy_redirect(request, legacy_id):
    cat = get_object_or_404(store_models.Category, pk=legacy_id)
    return redirect("store:category", slug=cat.slug, permanent=True)


def category(request, slug):
    category = get_object_or_404(store_models.Category, slug=slug)
    products_list = store_models.Product.objects.filter(status="Published", category=category)
    query = request.GET.get("q")
    products_list = _apply_search(products_list, query)
    products = paginate_queryset(request, products_list, 9)

    context = {
        "products": products,
        "products_list": products_list,
        "category": category,
    }
    return render(request, "store/category.html", context)

def vendors(request):
    vendors = userauths_models.Profile.objects.filter(user_type="manager")
    
    context = {
        "vendors": vendors
    }
    return render(request, "store/vendors.html", context)

def product_detail(request, slug):
    product = store_models.Product.objects.get(status="Published", slug=slug)
    product_stock_range = range(1, max(1, product.stock) + 1)
    related_products = store_models.Product.objects.filter(category=product.category).exclude(id=product.id)
    has_specs = any(
        v.name not in ("Color", "Size") and v.variant_items.exists()
        for v in product.variants()
    )
    context = {
        "product": product,
        "product_stock_range": product_stock_range,
        "related_products": related_products,
        "has_specs": has_specs,
    }
    return render(request, "store/product_detail.html", context)

def add_to_cart(request):
    # Get parameters from the request (ID, color, size, quantity, cart_id)
    id = request.GET.get("id")
    qty_raw = request.GET.get("qty")
    color = clamp_text(request.GET.get("color"), MAX_CART_COLOR_SIZE_LEN)
    size = clamp_text(request.GET.get("size"), MAX_CART_COLOR_SIZE_LEN)
    client_cart = request.GET.get("cart_id")

    product_pk = parse_positive_int(id, default=None)
    if product_pk is None:
        return JsonResponse({"error": "Некорректный товар"}, status=400)
    qty = parse_product_qty(qty_raw)
    if qty is None:
        return JsonResponse({"error": "Некорректное количество"}, status=400)

    session_cart = request.session.get("cart_id")
    new_cart_assigned = False
    if session_cart:
        if client_cart and (
            len(str(client_cart)) > 80 or client_cart != session_cart
        ):
            return JsonResponse({"error": "Некорректная корзина"}, status=403)
        cart_id = session_cart
    else:
        # Не доверяем cart_id с клиента при первой привязке: иначе можно подставить UUID чужой корзины.
        cart_id = str(uuid.uuid4())
        request.session["cart_id"] = cart_id
        request.session.modified = True
        new_cart_assigned = True

    # Try to fetch the product, return an error if it doesn't exist
    try:
        product = store_models.Product.objects.get(status="Published", id=product_pk)
    except store_models.Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    # Check if the item is already in the cart
    existing_cart_item = store_models.Cart.objects.filter(cart_id=cart_id, product=product).first()

    # Check if quantity that user is adding exceed item stock qty
    if int(qty) > product.stock:
        return JsonResponse({"error": "Qty exceed current stock amount"}, status=404)

    # If the item is not in the cart, create a new cart entry
    if not existing_cart_item:
        cart = store_models.Cart()
        cart.product = product
        cart.qty = qty
        cart.price = product.price
        cart.color = color
        cart.size = size
        cart.sub_total = Decimal(product.price) * Decimal(qty)
        cart.shipping = Decimal(product.shipping) * Decimal(qty)
        cart.total = cart.sub_total + cart.shipping
        cart.user = request.user if request.user.is_authenticated else None
        cart.cart_id = cart_id
        cart.save()

        message = "Товар добавлен в корзину"
    else:
        # If the item exists in the cart, update the existing entry
        existing_cart_item.color = color
        existing_cart_item.size = size
        existing_cart_item.qty = qty
        existing_cart_item.price = product.price
        existing_cart_item.sub_total = Decimal(product.price) * Decimal(qty)
        existing_cart_item.shipping = Decimal(product.shipping) * Decimal(qty)
        existing_cart_item.total = existing_cart_item.sub_total +  existing_cart_item.shipping
        existing_cart_item.user = request.user if request.user.is_authenticated else None
        existing_cart_item.cart_id = cart_id
        existing_cart_item.save()

        message = "Корзина обновлена"

    # Count the total number of items in the cart
    total_cart_items = store_models.Cart.objects.filter(cart_id=cart_id)
    cart_sub_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(sub_total = models.Sum("sub_total"))['sub_total']

    # Return the response with the cart update message and total cart items
    payload = {
        "message": message,
        "total_cart_items": total_cart_items.count(),
        "cart_sub_total": "{:,.2f}".format(cart_sub_total),
        "item_sub_total": "{:,.2f}".format(existing_cart_item.sub_total)
        if existing_cart_item
        else "{:,.2f}".format(cart.sub_total),
    }
    if new_cart_assigned:
        payload["cart_id"] = cart_id
    return JsonResponse(payload)

def cart(request):
    if "cart_id" in request.session:
        cart_id = request.session['cart_id']
    else:
        cart_id = None

    items = store_models.Cart.objects.filter(cart_id=cart_id)
    cart_sub_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(sub_total=models.Sum("sub_total"))['sub_total']
    cart_sub_total = cart_sub_total or Decimal("0.00")

    context = {
        "items": items,
        "cart_sub_total": cart_sub_total,
    }
    return render(request, "store/cart.html", context)


def delivery_request(request):
    if request.method != "POST":
        messages.error(request, "Пожалуйста, заполните форму оформления доставки")
        return redirect("store:cart")

    full_name = clamp_text(request.POST.get("full_name"), MAX_CONTACT_FIELD)
    phone = clamp_text(request.POST.get("phone"), 40)
    address = clamp_text(request.POST.get("address"), 2000)

    if not full_name or not phone or not address:
        messages.error(request, "Пожалуйста, заполните все поля формы")
        return redirect("store:cart")

    cart_id = request.session.get('cart_id')
    items = store_models.Cart.objects.filter(cart_id=cart_id)

    if not items:
        messages.warning(request, "В корзине нет товаров")
        return redirect("store:index")

    cart_sub_total = items.aggregate(total=models.Sum("sub_total"))['total'] or Decimal("0.00")
    cart_shipping_total = items.aggregate(total=models.Sum("shipping"))['total'] or Decimal("0.00")

    # Снимок корзины до удаления (для писем после commit).
    # product.vendor — это User; у User нет цепочки __user (было бы FieldError → 500 до try).
    # OneToOne vendor.Vendor: user.vendor → профиль магазина (store_name).
    cart_rows = list(
        items.select_related("product", "product__vendor", "product__vendor__vendor")
    )

    def _d(v):
        """PostgreSQL не принимает NULL в DecimalField без null=True — в корзине иногда бывают пустые суммы."""
        return v if v is not None else Decimal("0.00")

    order_pk_for_telegram = None
    order_for_email = None
    try:
        with transaction.atomic():
            # Создаём адрес заявки (может быть без авторизации)
            address_obj = customer_models.Address.objects.create(
                user=request.user if request.user.is_authenticated else None,
                full_name=full_name,
                mobile=phone,
                address=address,
            )

            order = store_models.Order.objects.create(
                customer=request.user if request.user.is_authenticated else None,
                address=address_obj,
                sub_total=cart_sub_total,
                shipping=cart_shipping_total,
                tax=Decimal("0.00"),
                service_fee=Decimal("0.00"),
                total=cart_sub_total + cart_shipping_total,
                payment_status="Processing",
                status="new",
                status_changed_by=request.user if request.user.is_authenticated else None,
                status_changed_at=timezone.now(),
                cancel_comment="",
            )

            # Чтобы в Telegram ушло одно сообщение с товарами, отправляем из view после создания позиций
            import orders.services as orders_services
            orders_services.TELEGRAM_SKIP_ORDER_IDS.add(order.pk)
            order_pk_for_telegram = order.pk
            order_for_email = order

            for cart_item in cart_rows:
                line_total = _d(cart_item.total)
                store_models.OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    qty=int(cart_item.qty or 0),
                    color=cart_item.color,
                    size=cart_item.size,
                    price=_d(cart_item.price),
                    sub_total=_d(cart_item.sub_total),
                    shipping=_d(cart_item.shipping),
                    tax=Decimal("0.00"),
                    total=line_total,
                    initial_total=line_total,
                    vendor=cart_item.product.vendor,
                    status="new",
                )
                # ManyToMany нельзя вызывать с None — у части товаров vendor не задан
                v_user = cart_item.product.vendor
                if v_user is not None:
                    order.vendors.add(v_user)

            clear_cart_items(request)
    except Exception:
        logger.exception("delivery_request: ошибка при создании заказа")
        messages.error(
            request,
            "Не удалось оформить заявку. Попробуйте ещё раз или свяжитесь с нами по телефону.",
        )
        return redirect("store:cart")

    # Письма после успешного commit: сбой шаблона/SMTP не должен откатывать заказ
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", getattr(settings, "EMAIL_HOST_USER", "noreply@asco.kg"))
    vendor_items_map = {}
    for row in cart_rows:
        vendor = getattr(row.product, "vendor", None)
        vendor_items_map.setdefault(vendor, []).append(row)

    for vendor, vendor_items in vendor_items_map.items():
        # vendor здесь — userauths.User (FK с товара), письмо на vendor.email
        if not vendor or not getattr(vendor, "email", None):
            continue
        try:
            try:
                v_shop = vendor.vendor
            except Exception:
                v_shop = None
            vendor_greeting = (
                (v_shop.store_name if v_shop and v_shop.store_name else None)
                or vendor.get_full_name()
                or vendor.email
            )
            context = {
                "vendor": vendor,
                "vendor_greeting": vendor_greeting,
                "items": vendor_items,
                "full_name": full_name,
                "phone": phone,
                "address": address,
                "cart_total": cart_sub_total,
                "order": order_for_email,
            }
            subject = "Новая заявка на доставку"
            text_body = render_to_string("email/order/vendor/delivery_request.txt", context)
            html_body = render_to_string("email/order/vendor/delivery_request.html", context)
            email = EmailMultiAlternatives(subject=subject, body=text_body, from_email=from_email, to=[vendor.email])
            email.attach_alternative(html_body, "text/html")
            email.send(fail_silently=True)
        except Exception:
            logger.exception("delivery_request: ошибка письма продавцу %s", getattr(vendor, "pk", vendor))

    # После коммита — Telegram (сеть не держит блокировку БД)
    if order_pk_for_telegram:
        try:
            from orders.services import send_order_to_telegram

            if not send_order_to_telegram(order_pk_for_telegram):
                logger.warning(
                    "delivery_request: уведомление в Telegram не отправлено (см. логи orders.services / проверьте .env и api.telegram.org)."
                )
        except Exception:
            logger.exception("delivery_request: исключение при отправке в Telegram")

    if order_for_email:
        order_access.register_order_session_access(request, order_for_email.pk)

    messages.success(request, "Заявка успешно отправлена. Мы свяжемся с вами в ближайшее время!")
    return redirect("store:shop")


def delete_cart_item(request):
    id = request.GET.get("id")
    item_id = request.GET.get("item_id")
    cart_id = request.GET.get("cart_id")
    session_cart = request.session.get("cart_id")

    product_pk = parse_positive_int(id, default=None)
    line_pk = parse_positive_int(item_id, default=None)
    if product_pk is None or line_pk is None or not cart_id:
        return JsonResponse({"error": "Item or Product id not found"}, status=400)
    if len(str(cart_id)) > 80 or not session_cart or cart_id != session_cart:
        return JsonResponse({"error": "Forbidden"}, status=403)

    try:
        product = store_models.Product.objects.get(status="Published", id=product_pk)
    except store_models.Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    try:
        item = store_models.Cart.objects.get(
            product=product, id=line_pk, cart_id=cart_id
        )
    except store_models.Cart.DoesNotExist:
        return JsonResponse({"error": "Cart item not found"}, status=404)
    item.delete()

    # Count the total number of items in the cart
    total_cart_items = store_models.Cart.objects.filter(cart_id=cart_id)
    cart_sub_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(sub_total = models.Sum("sub_total"))['sub_total']

    return JsonResponse({
        "message": "Товар удалён из корзины",
        "total_cart_items": total_cart_items.count(),
        "cart_sub_total": "{:,.2f}".format(cart_sub_total) if cart_sub_total else 0.00
    })


@login_required
def create_order(request):
    if request.method != "POST":
        return redirect("store:cart")

    address_id = parse_positive_int(request.POST.get("address"), default=None)
    if address_id is None:
        messages.warning(request, "Пожалуйста, выберите адрес для продолжения")
        return redirect("store:cart")

    address = customer_models.Address.objects.filter(
        user=request.user, id=address_id
    ).first()
    if not address:
        messages.warning(request, "Адрес не найден")
        return redirect("store:cart")

    cart_id = request.session.get("cart_id")
    items = store_models.Cart.objects.filter(cart_id=cart_id)
    if not items.exists():
        messages.warning(request, "Корзина пуста")
        return redirect("store:cart")

    cart_sub_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(
        sub_total=models.Sum("sub_total")
    )["sub_total"]
    cart_shipping_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(
        shipping=models.Sum("shipping")
    )["shipping"]

    order = store_models.Order()
    order.sub_total = cart_sub_total
    order.customer = request.user
    order.address = address
    order.shipping = cart_shipping_total
    order.tax = tax_calculation(address.country, cart_sub_total)
    order.total = order.sub_total + order.shipping + Decimal(order.tax)
    order.service_fee = calculate_service_fee(order.total)
    order.total += order.service_fee
    order.status = "new"
    order.status_changed_by = request.user
    order.status_changed_at = timezone.now()
    order.cancel_comment = ""
    order.save()

    for i in items:
        store_models.OrderItem.objects.create(
            order=order,
            product=i.product,
            qty=i.qty,
            color=i.color,
            size=i.size,
            price=i.price,
            sub_total=i.sub_total,
            shipping=i.shipping,
            tax=tax_calculation(address.country, i.sub_total),
            total=i.total,
            initial_total=i.total,
            vendor=i.product.vendor,
            status="new",
        )

        v_user = i.product.vendor
        if v_user is not None:
            order.vendors.add(v_user)

    order_access.register_order_session_access(request, order.pk)
    return redirect("store:checkout", order.order_id)


@login_required
def coupon_apply(request, order_id):
    try:
        order = order_access.get_order_for_customer(request, order_id)
    except Http404:
        messages.error(request, "Заказ не найден")
        return redirect("store:cart")

    order_items = store_models.OrderItem.objects.filter(order=order)

    if request.method == 'POST':
        coupon_code = clamp_text(request.POST.get("coupon_code"), 64)
        
        if not coupon_code:
            messages.error(request, "Купон не введён")
            return redirect("store:checkout", order.order_id)
            
        try:
            coupon = store_models.Coupon.objects.get(code=coupon_code)
        except store_models.Coupon.DoesNotExist:
            messages.error(request, "Купон не существует")
            return redirect("store:checkout", order.order_id)
        
        if coupon in order.coupons.all():
            messages.warning(request, "Купон уже активирован")
            return redirect("store:checkout", order.order_id)
        else:
            # Assuming coupon applies to specific vendor items, not globally
            total_discount = 0
            for item in order_items:
                if coupon.vendor == item.product.vendor and coupon not in item.coupon.all():
                    item_discount = item.total * coupon.discount / 100  # Discount for this item
                    total_discount += item_discount

                    item.coupon.add(coupon) 
                    item.total -= item_discount
                    item.saved += item_discount
                    item.save()

            # Apply total discount to the order after processing all items
            if total_discount > 0:
                order.coupons.add(coupon)
                order.total -= total_discount
                order.sub_total -= total_discount
                order.saved += total_discount
                order.save()
        
        messages.success(request, "Купон активирован")
        return redirect("store:checkout", order.order_id)

    return redirect("store:checkout", order.order_id)


@login_required
def checkout(request, order_id):
    try:
        order = order_access.get_order_for_customer(request, order_id)
    except Http404:
        messages.error(request, "Заказ не найден")
        return redirect("store:cart")
    
    amount_in_inr = convert_usd_to_inr(order.total)
    amount_in_kobo = convert_usd_to_kobo(order.total)
    amount_in_ngn = convert_usd_to_ngn(order.total)

    try:
        razorpay_order = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)).order.create({
            "amount": int(amount_in_inr),
            "currency": "INR",
            "payment_capture": "1"
        })
    except Exception:
        razorpay_order = None
    flutterwave_cb = reverse("store:flutterwave_payment_callback", args=[order.order_id])
    flutterwave_redirect_url = (
        request.build_absolute_uri(flutterwave_cb) + "?" + urlencode({"payment_method": "Flutterwave"})
    )
    context = {
        "order": order,
        "amount_in_inr":amount_in_inr,
        "amount_in_kobo":amount_in_kobo,
        "amount_in_ngn":round(amount_in_ngn, 2),
        "razorpay_order_id": razorpay_order['id'] if razorpay_order else None,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
        "paypal_client_id": settings.PAYPAL_CLIENT_ID,
        "razorpay_key_id":settings.RAZORPAY_KEY_ID,
        "paystack_public_key":settings.PAYSTACK_PUBLIC_KEY,
        "flutterwave_public_key":settings.FLUTTERWAVE_PUBLIC_KEY,
        "flutterwave_redirect_url": flutterwave_redirect_url,
    }

    return render(request, "store/checkout.html", context)


@login_required
def update_checkout_phone(request, order_id):
    """Обновление телефона на странице checkout (нормализация +996 для Telegram)."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST only"}, status=405)
    try:
        order = order_access.get_order_for_customer(request, order_id)
    except Http404:
        return JsonResponse({"ok": False, "error": "Order not found"}, status=404)
    if not order.address:
        return JsonResponse({"ok": False, "error": "No address"}, status=400)
    raw = (request.POST.get("phone") or "").strip()
    digits = "".join(c for c in raw if c.isdigit())
    if digits.startswith("996"):
        digits = digits[3:]
    digits = digits[:9]
    if len(digits) < 9:
        return JsonResponse({"ok": False, "error": "Введите 9 цифр номера Кыргызстана (+996)"})
    normalized = f"+996 {digits[:3]} {digits[3:6]} {digits[6:]}"
    order.address.mobile = normalized
    order.address.save(update_fields=["mobile"])
    return JsonResponse({"ok": True, "phone": normalized})


@login_required
@csrf_exempt
def stripe_payment(request, order_id):
    try:
        order = order_access.get_order_for_customer(request, order_id)
    except Http404:
        return JsonResponse({"error": "Order not found"}, status=404)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    unit_cents = int((order.total * Decimal("100")).quantize(Decimal("1")))

    checkout_session = stripe.checkout.Session.create(
        customer_email=order.address.email,
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "USD",
                    "product_data": {
                        "name": order.address.full_name,
                    },
                    "unit_amount": unit_cents,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        metadata={
            "order_id": str(order.order_id),
            "order_pk": str(order.pk),
        },
        success_url=request.build_absolute_uri(
            reverse("store:stripe_payment_verify", args=[order.order_id])
        )
        + "?session_id={CHECKOUT_SESSION_ID}"
        + "&payment_method=Stripe",
        cancel_url=request.build_absolute_uri(
            reverse("store:stripe_payment_verify", args=[order.order_id])
        ),
    )

    return JsonResponse({"sessionId": checkout_session.id})


@login_required
def stripe_payment_verify(request, order_id):
    try:
        order = order_access.get_order_for_customer(request, order_id)
    except Http404:
        return redirect("store:cart")

    session_id = request.GET.get("session_id")
    if not session_id:
        return redirect(f"/payment_status/{order_id}/?payment_status=failed")

    result = try_fulfill_stripe_checkout_session(
        order_pk=order.pk,
        session_id=session_id,
        request=request,
        clear_cart=True,
    )
    if result in ("fulfilled", "already_fulfilled"):
        return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
    return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
    
def get_paypal_access_token():
    token_url = 'https://api.sandbox.paypal.com/v1/oauth2/token'
    data = {'grant_type': 'client_credentials'}
    auth = (settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET_ID)
    response = requests.post(token_url, data=data, auth=auth)

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f'Failed to get access token from PayPal. Status code: {response.status_code}')


@login_required
def paypal_payment_verify(request, order_id):
    try:
        order = order_access.get_order_for_customer(request, order_id)
    except Http404:
        return redirect("store:cart")

    transaction_id = request.GET.get("transaction_id")
    paypal_api_url = f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{transaction_id}'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {get_paypal_access_token()}',
    }
    response = requests.get(paypal_api_url, headers=headers)

    if response.status_code == 200:
        paypal_order_data = response.json()
        paypal_payment_status = paypal_order_data['status']
        if paypal_payment_status == 'COMPLETED':
            if order.payment_status == "Processing":
                order.payment_status = "Paid"
                payment_method = request.GET.get("payment_method")
                order.payment_method = payment_method
                order.save()
                clear_cart_items(request)
                return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
    else:
        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")


@login_required
@csrf_exempt
def razorpay_payment_verify(request, order_id):
    try:
        order = order_access.get_order_for_customer(request, order_id)
    except Http404:
        return redirect("store:cart")
    payment_method = request.GET.get("payment_method")

    if request.method == "POST":
        data = request.POST
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_signature = data.get("razorpay_signature")
        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        }
        if not all(
            [razorpay_order_id, razorpay_payment_id, razorpay_signature]
        ) or not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            return redirect(
                f"/payment_status/{order.order_id}/?payment_status=failed"
            )
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        try:
            client.utility.verify_payment_signature(params_dict)
        except SignatureVerificationError:
            return redirect(
                f"/payment_status/{order.order_id}/?payment_status=failed"
            )

        if order.payment_status == "Processing":
            order.payment_status = "Paid"
            order.payment_method = payment_method
            order.save()
            clear_cart_items(request)
            customer_models.Notifications.objects.create(
                type="New Order",
                user=order.customer if order.customer_id else None,
            )
            for item in order.order_items():
                if item.vendor_id:
                    vendor_models.Notifications.objects.create(
                        type="New Order", user=item.vendor
                    )

            return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")

    return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")


@login_required
def paystack_payment_verify(request, order_id):
    try:
        order = order_access.get_order_for_customer(request, order_id)
    except Http404:
        return redirect("store:cart")
    reference = request.GET.get('reference', '')

    if reference:
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_PRIVATE_KEY}",
            "Content-Type": "application/json"
        }

        # Verify the transaction
        response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
        response_data = response.json()

        if response_data['status']:
            if response_data['data']['status'] == 'success':
                if order.payment_status == "Processing":
                    order.payment_status = "Paid"
                    payment_method = request.GET.get("payment_method")
                    order.payment_method = payment_method
                    order.save()
                    clear_cart_items(request)
                    return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
                else:
                    return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
            else:
                # Payment failed
                return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
        else:
            return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
    else:
        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")


@login_required
def flutterwave_payment_callback(request, order_id):
    try:
        order = order_access.get_order_for_customer(request, order_id)
    except Http404:
        return redirect("store:cart")

    expected_hash = (getattr(settings, "FLUTTERWAVE_SECRET_HASH", "") or "").strip()
    if expected_hash:
        sig = request.headers.get("Verif-Hash") or request.headers.get("verif-hash")
        if not sig or not hmac.compare_digest(sig, expected_hash):
            messages.error(request, "Некорректная подпись платежа.")
            return redirect("store:cart")

    payment_id = request.GET.get('tx_ref')
    status = request.GET.get('status')

    headers = {
        'Authorization': f'Bearer {settings.FLUTTERWAVE_PRIVATE_KEY}'
    }
    response = requests.get(f'https://api.flutterwave.com/v3/charges/verify_by_id/{payment_id}', headers=headers)

    if response.status_code == 200:
        if order.payment_status == "Processing":
            order.payment_status = "Paid"
            payment_method = request.GET.get("payment_method")
            order.payment_method = payment_method
            order.save()
            clear_cart_items(request)
            return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
        else:
            return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")
    else:
        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")


@login_required
def payment_status(request, order_id):
    try:
        order = order_access.get_order_for_customer(request, order_id)
    except Http404:
        return redirect("store:cart")
    payment_status = request.GET.get("payment_status")

    context = {
        "order": order,
        "payment_status": payment_status
    }
    return render(request, "store/payment_status.html", context)

def filter_products(request):
    products = store_models.Product.objects.filter(status="Published")

    # Get filters from the AJAX request
    categories = parse_int_id_list(request.GET.getlist("categories[]"))
    rating = parse_rating_list(request.GET.getlist("rating[]"))
    sizes = parse_filter_tokens(request.GET.getlist("sizes[]"))
    colors = parse_filter_tokens(request.GET.getlist("colors[]"))
    price_order = (request.GET.get("prices") or "").strip()
    if price_order not in ("lowest", "highest", ""):
        price_order = ""
    search_filter = parse_search_q(request.GET.get("searchFilter"))
    display = request.GET.get("display")

    # Apply category filtering
    if categories:
        products = products.filter(category__id__in=categories)

    # Apply rating filtering
    if rating:
        products = products.filter(reviews__rating__in=rating).distinct()

    # Apply size filtering
    if sizes:
        products = products.filter(variant__variant_items__content__in=sizes).distinct()

    # Apply color filtering
    if colors:
        products = products.filter(variant__variant_items__content__in=colors).distinct()

    # Apply price ordering
    if price_order == "lowest":
        products = products.order_by("-price")
    elif price_order == "highest":
        products = products.order_by("price")

    products = _apply_search(products, search_filter)

    if display:
        try:
            lim = min(max(int(display), 1), 200)
            products = products[:lim]
        except (TypeError, ValueError):
            pass


    # Wishlist IDs for heart icons in partial
    from store.context import default as store_default
    wishlist_context = store_default(request) if hasattr(request, 'user') else {}
    context = {'products': products, 'wishlist_product_ids': wishlist_context.get('wishlist_product_ids', set())}
    html = render_to_string('partials/_store.html', context)

    return JsonResponse({'html': html, 'product_count': products.count()})

def order_tracker_page(request):
    if request.method == "POST":
        raw = (request.POST.get("item_id") or "").strip()[:128]
        if not raw or any(c in raw for c in "\n\r\x00"):
            messages.error(request, "Укажите корректный номер заказа или трекинга.")
            return redirect("store:order_tracker_page")
        return redirect("store:order_tracker_detail", raw)
    
    return render(request, "store/order_tracker_page.html")

def order_tracker_detail(request, item_id):
    item = store_models.OrderItem.objects.filter(
        models.Q(item_id=item_id) | models.Q(tracking_id=item_id)
    ).first()
    if not item:
        messages.error(request, "Заказ не найден!")
        return redirect("store:order_tracker_page")

    if not order_access.customer_can_access_order(request, item.order):
        messages.error(request, "Заказ не найден!")
        return redirect("store:order_tracker_page")

    context = {
        "item": item,
    }
    return render(request, "store/order_tracker.html", context)

def about(request):
    return render(request, "pages/about.html")

@ratelimit(key="ip", rate="30/h", method="POST", block=False, group="contact_form")
def contact(request):
    if getattr(request, "limited", False) and request.method == "POST":
        messages.error(
            request,
            "Слишком много сообщений с этого адреса. Попробуйте позже.",
        )
        return render(request, "pages/contact.html", {"form": ContactForm()})

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            userauths_models.ContactMessage.objects.create(
                full_name=form.cleaned_data["full_name"].strip(),
                email=form.cleaned_data["email"].strip(),
                subject=form.cleaned_data["subject"].strip(),
                message=form.cleaned_data["message"].strip(),
            )
            messages.success(request, "Сообщение успешно отправлено")
            return redirect("store:contact")
    else:
        form = ContactForm()
    return render(request, "pages/contact.html", {"form": form})

def faqs(request):
    return render(request, "pages/faqs.html")

def privacy_policy(request):
    return render(request, "pages/privacy_policy.html")

def terms_conditions(request):
    return render(request, "pages/terms_conditions.html")