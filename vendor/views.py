from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.db.models.functions import TruncMonth
from django.db.models import Count
from django.utils import timezone
from django.utils.text import slugify
import uuid

import json

from plugin.paginate_queryset import paginate_queryset
from plugin.input_validation import (
    clamp_text,
    parse_positive_int,
    validate_uploaded_image,
)
from store import models as store_models
from store import order_access
from vendor import models as vendor_models
from permissions import (
    ManagerPermission,
    OwnerOrReadOnlyPermission,
    SuperAdminPermission,
    permission_required,
    check_object_permission,
)
 
 
def _generate_unique_category_slug(title: str, exclude_id: int | None = None) -> str:
    base_slug = slugify(title).strip("-")
    if not base_slug:
        base_slug = f"category-{uuid.uuid4().hex[:6]}"

    slug = base_slug
    counter = 1
    qs = store_models.Category.objects.all()
    if exclude_id:
        qs = qs.exclude(id=exclude_id)

    while qs.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug

def get_monthly_sales(user):
    qs = store_models.OrderItem.objects.all()
    if not (user.is_superuser or getattr(user, "role", None) == "superadmin"):
        qs = qs.filter(vendor=user)
    return (
        qs.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(order_count=Count("id"))
        .order_by("month")
    )

@login_required
@permission_required(ManagerPermission)
def dashboard(request):
    if request.user.role == "superadmin" or request.user.is_superuser:
        products = store_models.Product.objects.all()
        revenue = store_models.OrderItem.objects.filter(order__payment_status="Paid").aggregate(
            total=models.Sum("total")
        )['total']
    else:
        products = store_models.Product.objects.filter(created_by=request.user)
        revenue = store_models.OrderItem.objects.filter(vendor=request.user, order__payment_status="Paid").aggregate(
            total=models.Sum("total")
        )['total']
    orders = order_access.orders_queryset_for_vendor_user(request.user)
    notis = vendor_models.Notifications.objects.filter(user=request.user, seen=False)
    reviews = store_models.Review.objects.filter(product__vendor=request.user)
    rating = store_models.Review.objects.filter(product__vendor=request.user).aggregate(avg = models.Avg("rating"))['avg']
    monthly_sales = get_monthly_sales(request.user)

    # Extract months and order counts
    labels = [sale['month'].strftime('%B %Y') for sale in monthly_sales]  # Format the month
    data = [sale['order_count'] for sale in monthly_sales]


    context = {
        "products": products,
        "orders": orders,
        "revenue": revenue,
        "notis": notis,
        "reviews": reviews,
        "rating": rating,
        "labels": json.dumps(labels),
        "data": json.dumps(data),
    }

    return render(request, "vendor/dashboard.html", context)

@login_required
@permission_required(ManagerPermission)
def products(request):
    if getattr(request.user, "role", None) == "superadmin" or request.user.is_superuser:
        products_list = store_models.Product.objects.all()
    else:
        products_list = store_models.Product.objects.filter(created_by=request.user)
    products = paginate_queryset(request, products_list, 10)

    context = {
        "products": products,
        "products_list": products_list,
    }
    return render(request, "vendor/products.html", context)

@login_required
@permission_required(ManagerPermission)
def orders(request):
    orders_list = order_access.orders_queryset_for_vendor_user(request.user)
    orders = paginate_queryset(request, orders_list, 10)

    context = {
        "orders": orders,
        "orders_list": orders_list,
    }

    return render(request, "vendor/orders.html", context)

@login_required
@permission_required(ManagerPermission)
def order_detail(request, order_id):
    order = order_access.get_order_for_vendor(request, order_id)

    context = {
        "order": order,
    }

    return render(request, "vendor/order_detail.html", context)

@login_required
@permission_required(ManagerPermission)
def order_item_detail(request, order_id, item_id):
    order = order_access.get_order_for_vendor(request, order_id)
    item = get_object_or_404(store_models.OrderItem, item_id=item_id, order=order)
    context = {
        "order": order,
        "item": item,
    }
    return render(request, "vendor/order_item_detail.html", context)


@login_required
@permission_required(ManagerPermission)
def update_order_status(request, order_id):
    order = order_access.get_order_for_vendor(request, order_id)
    
    if request.method == "POST":
        new_status = request.POST.get("status") or request.POST.get("order_status")
        cancel_comment = request.POST.get("cancel_comment", "").strip()
        payment_status = request.POST.get("payment_status")

        if new_status:
            order.status = new_status
        if new_status == "cancelled" and cancel_comment:
            order.cancel_comment = cancel_comment
        elif new_status != "cancelled":
            order.cancel_comment = ""

        if payment_status:
            order.payment_status = payment_status

        order.status_changed_by = request.user
        order.status_changed_at = timezone.now()
        fields_to_update = ["status", "cancel_comment", "status_changed_by", "status_changed_at"]
        if payment_status:
            fields_to_update.append("payment_status")
        order.save(update_fields=fields_to_update)

        messages.success(request, "Статус заказа обновлён")
        return redirect("vendor:order_detail", order.order_id)

    return redirect("vendor:order_detail", order.order_id)

@login_required
@permission_required(ManagerPermission)
def update_order_item_status(request, order_id, item_id):
    order = order_access.get_order_for_vendor(request, order_id)
    item = get_object_or_404(store_models.OrderItem, item_id=item_id, order=order)
    
    if request.method == "POST":
        
        order_status = request.POST.get("status") or request.POST.get("order_status")
        payment_status = request.POST.get("payment_status")
        
        if order_status:
            item.status = order_status
        item.shipping_service = request.POST.get("shipping_service")
        item.tracking_id = request.POST.get("tracking_id")
        item.save(update_fields=["status", "shipping_service", "tracking_id"])

        if payment_status:
            order.payment_status = payment_status
            order.status_changed_by = request.user
            order.status_changed_at = timezone.now()
            order.save(update_fields=["payment_status", "status_changed_by", "status_changed_at"])

        messages.success(request, "Статус товара обновлён")
        return redirect("vendor:order_item_detail", order.order_id, item.item_id)
    return redirect("vendor:order_item_detail", order.order_id, item.item_id)


@login_required
@permission_required(ManagerPermission)
def coupons(request):
    coupons_list = store_models.Coupon.objects.filter(vendor=request.user)
    coupons = paginate_queryset(request, coupons_list, 10)

    context = {
        "coupons": coupons,
        "coupons_list": coupons_list,
    }
    return render(request, "vendor/coupons.html", context)

@login_required
@permission_required(ManagerPermission)
def update_coupon(request, id):
    coupon = get_object_or_404(store_models.Coupon, vendor=request.user, id=id)
    
    if request.method == "POST":
        code = request.POST.get("coupon_code")
        coupon.code = code
        coupon.save()

    messages.success(request, "Купон обновлён")
    return redirect("vendor:coupons")


@login_required
@permission_required(ManagerPermission)
def delete_coupon(request, id):
    coupon = get_object_or_404(store_models.Coupon, vendor=request.user, id=id)
    coupon.delete()
    messages.success(request, "Купон удалён")
    return redirect("vendor:coupons")


@login_required
@permission_required(ManagerPermission)
def create_coupon(request):
    if request.method == "POST":
        code = request.POST.get("coupon_code")
        discount = request.POST.get("coupon_discount")
        store_models.Coupon.objects.create(vendor=request.user, code=code, discount=discount)

    messages.success(request, "Купон создан")
    return redirect("vendor:coupons")


@login_required
@permission_required(ManagerPermission)
def reviews(request):
    reviews_list = store_models.Review.objects.filter(product__vendor=request.user)

    rating = request.GET.get("rating")
    date = request.GET.get("date")

    # Apply filtering and ordering to reviews_list
    if rating:
        reviews_list = reviews_list.filter(rating=rating)  # Apply filter to the reviews_list

    if date:
        reviews_list = reviews_list.order_by(date)  # Ensure this refers to a valid model field

    # Paginate after filtering and ordering
    reviews = paginate_queryset(request, reviews_list, 10)

    context = {
        "reviews": reviews,
        "reviews_list": reviews_list,
    }
    return render(request, "vendor/reviews.html", context)


@login_required
@permission_required(ManagerPermission)
def update_reply(request, id):
    if request.user.is_superuser or getattr(request.user, "role", None) == "superadmin":
        review = get_object_or_404(store_models.Review, id=id)
    else:
        review = get_object_or_404(
            store_models.Review, id=id, product__vendor=request.user
        )
    
    if request.method == "POST":
        reply = request.POST.get("reply")
        review.reply = reply
        review.save()

    messages.success(request, "Ответ добавлен")
    return redirect("vendor:reviews")



@login_required
@permission_required(ManagerPermission)
def notis(request):
    notis_list = vendor_models.Notifications.objects.filter(user=request.user, seen=False)
    notis = paginate_queryset(request, notis_list, 10)

    context = {
        "notis": notis,
        "notis_list": notis_list,
    }
    return render(request, "vendor/notis.html", context)

@login_required
@permission_required(ManagerPermission)
def mark_noti_seen(request, id):
    noti = get_object_or_404(vendor_models.Notifications, user=request.user, id=id)
    noti.seen = True
    noti.save()

    messages.success(request, "Уведомление отмечено как прочитанное")
    return redirect("vendor:notis")

@login_required
@permission_required(ManagerPermission)
def profile(request):
    profile = request.user.profile

    if request.method == "POST":
        image = request.FILES.get("image")
        full_name = request.POST.get("full_name")
        mobile = request.POST.get("mobile")
    
        if image is not None:
            err = validate_uploaded_image(image, field_name="Фото")
            if err:
                messages.error(request, err)
                return redirect("vendor:profile")
            profile.image = image

        profile.full_name = full_name
        profile.mobile = mobile

        request.user.save()
        profile.save()

        messages.success(request, "Профиль успешно обновлён")
        return redirect("vendor:profile")
    
    context = {
        'profile':profile,
    }
    return render(request, "vendor/profile.html", context)

@login_required
@permission_required(ManagerPermission)
def change_password(request):
    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_new_password = request.POST.get("confirm_new_password")

        if confirm_new_password != new_password:
            messages.error(request, "Подтверждение пароля и новый пароль не совпадают")
            return redirect("vendor:change_password")
        
        if check_password(old_password, request.user.password):
            request.user.set_password(new_password)
            request.user.save()
            messages.success(request, "Пароль успешно изменён")
            return redirect("vendor:profile")
        else:
            messages.error(request, "Старый пароль неверный")
            return redirect("vendor:change_password")
    
    return render(request, "vendor/change_password.html")


@login_required
@permission_required(ManagerPermission)
def create_product(request):
    categories = store_models.Category.objects.all()

    if request.method == "POST":
        image = request.FILES.get("image")
        name = clamp_text(request.POST.get("name"), 500)
        category_pk = parse_positive_int(request.POST.get("category_id"), default=None)
        description = clamp_text(request.POST.get("description"), 50000)
        price = request.POST.get("price")
        regular_price = request.POST.get("regular_price")
        shipping = request.POST.get("shipping")
        stock = request.POST.get("stock")

        if not name:
            messages.error(request, "Укажите название товара.")
            return render(request, "vendor/create_product.html", {"categories": categories})
        if category_pk is None:
            messages.error(request, "Выберите категорию.")
            return render(request, "vendor/create_product.html", {"categories": categories})
        if image is not None:
            err = validate_uploaded_image(image, field_name="Изображение товара")
            if err:
                messages.error(request, err)
                return render(request, "vendor/create_product.html", {"categories": categories})

        product = store_models.Product.objects.create(
            vendor=request.user,
            created_by=request.user,
            image=image,
            name=name,
            category_id=category_pk,
            description=description,
            price=price,
            regular_price=regular_price,
            shipping=shipping,
            stock=stock,
        )
        return redirect("vendor:update_product", product.id)
    context = {
        'categories': categories
    }
    return render(request, "vendor/create_product.html", context)
@login_required
@permission_required(ManagerPermission)
def update_product(request, id):
    product = get_object_or_404(store_models.Product, id=id)
    check_object_permission(request, OwnerOrReadOnlyPermission, product)

    categories = store_models.Category.objects.all()

    if request.method == "POST":
        # Get data from the form submission
        image = request.FILES.get("image")
        name = request.POST.get("name")
        category_id = request.POST.get("category_id")
        description = request.POST.get("description")
        price = request.POST.get("price")
        regular_price = request.POST.get("regular_price")
        shipping = request.POST.get("shipping")
        stock = request.POST.get("stock")

        # Update the product details
        product.name = name
        product.category_id = category_id
        product.description = description
        product.price = price
        product.regular_price = regular_price
        product.shipping = shipping
        product.stock = stock

        if image:
            err = validate_uploaded_image(image, field_name="Изображение товара")
            if err:
                messages.error(request, err)
                return redirect("vendor:update_product", product.id)
            product.image = image

        if not product.created_by:
            product.created_by = request.user

        product.save()


        # Handle product variants and items
        variant_ids = request.POST.getlist('variant_id[]')
        variant_titles = request.POST.getlist('variant_title[]')

        if variant_ids and variant_titles:

            # Loop through variants
            for i, variant_id in enumerate(variant_ids):
                variant_name = variant_titles[i]
                
                if variant_id:  # If variant exists, update it (только вариант этого товара)
                    variant = store_models.Variant.objects.filter(
                        id=variant_id, product=product
                    ).first()
                    if not variant:
                        continue
                    variant.name = variant_name
                    variant.save()
                else:  # Create new variant
                    variant = store_models.Variant.objects.create(
                        product=product, name=variant_name
                    )
                
                # Now handle items for this variant
                item_ids = request.POST.getlist(f'item_id_{i}[]')
                item_titles = request.POST.getlist(f'item_title_{i}[]')
                item_descriptions = request.POST.getlist(f'item_description_{i}[]')

                if item_ids and item_titles and item_descriptions:

                    for j in range(len(item_titles)):
                        item_id = item_ids[j]
                        item_title = item_titles[j]
                        item_description = item_descriptions[j]
                        
                        if item_id:  # Update existing item (только в рамках этого товара)
                            variant_item = store_models.VariantItem.objects.filter(
                                id=item_id, variant=variant
                            ).first()
                            if variant_item:
                                variant_item.title = item_title
                                variant_item.content = item_description
                                variant_item.save()
                        else:  # Create new item
                            store_models.VariantItem.objects.create(
                                variant=variant,
                                title=item_title,
                                content=item_description
                            )
        # Handle product gallery images
        # Get all dynamically added image inputs
        for file_key, image_file in request.FILES.items():
            if file_key.startswith("image_"):
                err = validate_uploaded_image(
                    image_file, field_name="Изображение галереи"
                )
                if err:
                    messages.error(request, err)
                    return redirect("vendor:update_product", product.id)
                store_models.Gallery.objects.create(product=product, image=image_file)


        # Redirect back to the update page after saving
        return redirect("vendor:update_product", product.id)

    # Prepare context for the template
    context = {
        'product': product,
        'categories': categories,
        'variants': store_models.Variant.objects.filter(product=product),
        'gallery_images': store_models.Gallery.objects.filter(product=product),  # Pass existing gallery images to the template
    }

    return render(request, "vendor/update_product.html", context)


@login_required
@permission_required(ManagerPermission)
def delete_variants(request, product_id, variant_id):
    product = get_object_or_404(store_models.Product, id=product_id)
    check_object_permission(request, OwnerOrReadOnlyPermission, product)
    variant = get_object_or_404(store_models.Variant, id=variant_id, product=product)
    variant.delete()
    return JsonResponse({"message": "Вариант удалён"})


@login_required
@permission_required(ManagerPermission)
def delete_variants_items(request, variant_id, item_id):
    variant = get_object_or_404(store_models.Variant, id=variant_id)
    product = variant.product
    check_object_permission(request, OwnerOrReadOnlyPermission, product)
    item = get_object_or_404(store_models.VariantItem, variant=variant, id=item_id)
    item.delete()
    return JsonResponse({"message": "Элемент варианта удалён"})


@login_required
@permission_required(ManagerPermission)
def delete_product_image(request, product_id, image_id):
    product = get_object_or_404(store_models.Product, id=product_id)
    check_object_permission(request, OwnerOrReadOnlyPermission, product)
    image = get_object_or_404(store_models.Gallery, product=product, id=image_id)
    image.delete()
    return JsonResponse({"message": "Изображение удалено"})


@login_required
@permission_required(ManagerPermission)
def delete_product(request, product_id):
    product = get_object_or_404(store_models.Product, id=product_id)
    check_object_permission(request, OwnerOrReadOnlyPermission, product)
    product.delete()

    messages.success(request, "Товар удалён")
    return redirect("vendor:products")


@login_required
@permission_required(ManagerPermission)
def categories(request):
    categories_qs = store_models.Category.objects.order_by("-id")

    if request.method == "POST":
        if not SuperAdminPermission.has_permission(request):
            messages.error(
                request,
                "Создание категорий доступно только суперадминистратору.",
            )
            return redirect("vendor:categories")

        title = request.POST.get("title", "").strip()
        image = request.FILES.get("image")

        if not title:
            messages.error(request, "Название категории обязательно.")
            return redirect("vendor:categories")

        if image is not None:
            err = validate_uploaded_image(image, field_name="Изображение категории")
            if err:
                messages.error(request, err)
                return redirect("vendor:categories")

        slug = _generate_unique_category_slug(title)
        category = store_models.Category(title=title, slug=slug)
        if image:
            category.image = image
        category.save()
        messages.success(request, "Категория успешно создана.")
        return redirect("vendor:categories")

    context = {"categories": categories_qs}
    return render(request, "vendor/categories.html", context)


@login_required
@permission_required(ManagerPermission)
@permission_required(SuperAdminPermission)
def category_edit(request, category_id):
    category = get_object_or_404(store_models.Category, id=category_id)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        image = request.FILES.get("image")

        if not title:
            messages.error(request, "Название категории обязательно.")
        else:
            category.title = title
            category.slug = _generate_unique_category_slug(title, exclude_id=category.id)
            if image is not None:
                err = validate_uploaded_image(image, field_name="Изображение категории")
                if err:
                    messages.error(request, err)
                    return redirect("vendor:category_edit", category_id=category.id)
                category.image = image
            category.save()
            messages.success(request, "Категория обновлена.")
            return redirect("vendor:categories")

    context = {"category": category}
    return render(request, "vendor/category_form.html", context)


@login_required
@permission_required(ManagerPermission)
@permission_required(SuperAdminPermission)
def category_delete(request, category_id):
    category = get_object_or_404(store_models.Category, id=category_id)

    if request.method == "POST":
        category.delete()
        messages.success(request, "Категория удалена.")
        return redirect("vendor:categories")

    messages.error(request, "Недопустимый метод запроса.")
    return redirect("vendor:categories")