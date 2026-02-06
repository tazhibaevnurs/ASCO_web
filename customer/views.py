import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password

from plugin.paginate_queryset import paginate_queryset
from store import models as store_models
from store.context import WISHLIST_SESSION_KEY
from customer import models as customer_models

@login_required
def dashboard(request):
    orders = store_models.Order.objects.filter(customer=request.user)
    total_spent = store_models.Order.objects.filter(customer=request.user).aggregate(total = models.Sum("total"))['total']
    notis = customer_models.Notifications.objects.filter(user=request.user, seen=False)

    context = {
        "orders": orders,
        "total_spent": total_spent,
        "notis": notis,
    }

    return render(request, "customer/dashboard.html", context)

@login_required
def orders(request):
    orders = store_models.Order.objects.filter(customer=request.user)

    context = {
        "orders": orders,
    }

    return render(request, "customer/orders.html", context)

@login_required
def order_detail(request, order_id):
    order = store_models.Order.objects.get(customer=request.user, order_id=order_id)

    context = {
        "order": order,
    }

    return render(request, "customer/order_detail.html", context)

@login_required
def order_item_detail(request, order_id, item_id):
    order = store_models.Order.objects.get(customer=request.user, order_id=order_id)
    item = store_models.OrderItem.objects.get(order=order, item_id=item_id)
    
    context = {
        "order": order,
        "item": item,
    }

    return render(request, "customer/order_item_detail.html", context)



@login_required
def wishlist(request):
    wishlist_list = customer_models.Wishlist.objects.filter(user=request.user)
    wishlist = paginate_queryset(request, wishlist_list, 6)

    context = {
        "wishlist": wishlist,
        "wishlist_list": wishlist_list,
        "wishlist_count": wishlist_list.count(),
    }

    return render(request, "customer/wishlist.html", context)

@login_required
def remove_from_wishlist(request, id):
    wishlist_entry = get_object_or_404(customer_models.Wishlist, user=request.user, id=id)
    wishlist_entry.delete()

    if request.headers.get("HX-Request"):
        wishlist_count = customer_models.Wishlist.objects.filter(user=request.user).count()
        html = render(
            request,
            "customer/includes/wishlist_remove_response.html",
            {"wishlist_count": wishlist_count},
        ).content.decode()
        response = HttpResponse(html)
        response["HX-Trigger"] = json.dumps({"showWishlistToast": {"text": "Товар удалён из избранного", "tag": "success"}})
        return response

    messages.success(request, "Товар удалён из избранного")
    return redirect("customer:wishlist")


def sync_wishlist_from_storage(request):
    """Для гостей: принимает ids из LocalStorage (GET ids=1,2,3) и записывает в сессию. reload=True только если сессия была пуста и мы что-то записали."""
    if request.user.is_authenticated:
        return JsonResponse({"ok": True, "reload": False})
    ids_str = request.GET.get("ids", "")
    if not ids_str:
        return JsonResponse({"ok": True, "reload": False})
    try:
        ids = [int(x.strip()) for x in ids_str.split(",") if x.strip()]
    except ValueError:
        ids = []
    current = list(request.session.get(WISHLIST_SESSION_KEY) or [])
    need_reload = not current and ids
    request.session[WISHLIST_SESSION_KEY] = ids
    request.session.modified = True
    return JsonResponse({"ok": True, "count": len(ids), "reload": need_reload})


def add_to_wishlist(request, id):
    """Legacy endpoint; prefer toggle_wishlist for HTMX."""
    return toggle_wishlist(request, id)


def toggle_wishlist(request, id):
    """Добавляет или удаляет товар из избранного. Для гостей — session, для юзеров — БД. HTMX: возвращает фрагмент кнопки + OOB счётчиков."""
    product = get_object_or_404(store_models.Product, id=id)
    is_in_wishlist = False
    wishlist_count = 0

    if request.user.is_authenticated:
        wishlist_entry, created = customer_models.Wishlist.objects.get_or_create(
            product=product, user=request.user
        )
        if not created:
            wishlist_entry.delete()
            is_in_wishlist = False
        else:
            is_in_wishlist = True
        wishlist_count = customer_models.Wishlist.objects.filter(user=request.user).count()
    else:
        session_ids = list(request.session.get(WISHLIST_SESSION_KEY) or [])
        try:
            session_ids = [int(x) for x in session_ids]
        except (TypeError, ValueError):
            session_ids = []
        if product.id in session_ids:
            session_ids = [x for x in session_ids if x != product.id]
            is_in_wishlist = False
        else:
            session_ids.append(product.id)
            is_in_wishlist = True
        request.session[WISHLIST_SESSION_KEY] = session_ids
        request.session.modified = True
        wishlist_count = len(session_ids)

    if request.headers.get("HX-Request"):
        html = render(
            request,
            "customer/includes/wishlist_response.html",
            {
                "product": product,
                "is_in_wishlist": is_in_wishlist,
                "wishlist_count": wishlist_count,
            },
        ).content.decode()
        response = HttpResponse(html)
        toast_text = "Товар добавлен в избранное" if is_in_wishlist else "Товар удалён из избранного"
        trigger = {"showWishlistToast": {"text": toast_text, "tag": "success"}}
        if not request.user.is_authenticated:
            trigger["wishlistIds"] = list(request.session.get(WISHLIST_SESSION_KEY) or [])
        response["HX-Trigger"] = json.dumps(trigger)
        return response

    return JsonResponse({
        "status": "added" if is_in_wishlist else "removed",
        "message": "Товар добавлен в избранное" if is_in_wishlist else "Товар удалён из избранного",
        "wishlist_count": wishlist_count,
        "is_in_wishlist": is_in_wishlist,
    })




@login_required
def notis(request):
    notis_list = customer_models.Notifications.objects.filter(user=request.user, seen=False)
    notis = paginate_queryset(request, notis_list, 10)

    context = {
        "notis": notis,
        "notis_list": notis_list,
    }
    return render(request, "customer/notis.html", context)

@login_required
def mark_noti_seen(request, id):
    noti = customer_models.Notifications.objects.get(user=request.user, id=id)
    noti.seen = True
    noti.save()

    messages.success(request, "Уведомление отмечено как прочитанное")
    return redirect("customer:notis")


@login_required
def addresses(request):
    addresses = customer_models.Address.objects.filter(user=request.user)
    context = {
        "addresses": addresses,
    }

    return render(request, "customer/addresses.html", context)

@login_required
def address_detail(request, id):
    address = customer_models.Address.objects.get(user=request.user, id=id)
    
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        mobile = request.POST.get("mobile")
        email = request.POST.get("email")
        country = request.POST.get("country")
        state = request.POST.get("state")
        city = request.POST.get("city")
        address_location = request.POST.get("address")
        zip_code = request.POST.get("zip_code")

        address.full_name = full_name
        address.mobile = mobile
        address.email = email
        address.country = country
        address.state = state
        address.city = city
        address.address = address_location
        address.zip_code = zip_code
        address.save()

        messages.success(request, "Адрес обновлён")
        return redirect("customer:address_detail", address.id)
    
    context = {
        "address": address,
    }

    return render(request, "customer/address_detail.html", context)

@login_required
def address_create(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        mobile = request.POST.get("mobile")
        email = request.POST.get("email")
        country = request.POST.get("country")
        state = request.POST.get("state")
        city = request.POST.get("city")
        address = request.POST.get("address")
        zip_code = request.POST.get("zip_code")

        customer_models.Address.objects.create(
            user=request.user,
            full_name=full_name,
            mobile=mobile,
            email=email,
            country=country,
            state=state,
            city=city,
            address=address,
            zip_code=zip_code,
        )

        messages.success(request, "Адрес создан")
        return redirect("customer:addresses")
    
    return render(request, "customer/address_create.html")

def delete_address(request, id):
    address = customer_models.Address.objects.get(user=request.user, id=id)
    address.delete()
    messages.success(request, "Адрес удалён")
    return redirect("customer:addresses")

@login_required
def profile(request):
    profile = request.user.profile

    if request.method == "POST":
        image = request.FILES.get("image")
        full_name = request.POST.get("full_name")
        mobile = request.POST.get("mobile")
    
        if image != None:
            profile.image = image

        profile.full_name = full_name
        profile.mobile = mobile

        request.user.save()
        profile.save()

        messages.success(request, "Профиль успешно обновлён")
        return redirect("customer:profile")
    
    context = {
        'profile':profile,
    }
    return render(request, "customer/profile.html", context)

@login_required
def change_password(request):
    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_new_password = request.POST.get("confirm_new_password")

        if confirm_new_password != new_password:
            messages.error(request, "Подтверждение пароля и новый пароль не совпадают")
            return redirect("customer:change_password")
        
        if check_password(old_password, request.user.password):
            request.user.set_password(new_password)
            request.user.save()
            messages.success(request, "Пароль успешно изменён")
            return redirect("customer:profile")
        else:
            messages.error(request, "Старый пароль неверный")
            return redirect("customer:change_password")
    
    return render(request, "customer/change_password.html")