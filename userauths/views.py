from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django_ratelimit.decorators import ratelimit

from userauths import forms as userauths_forms
from userauths import models as userauths_models
from userauths.redirects import redirect_after_login
from userauths.tokens import account_activation_token
from store.context import WISHLIST_SESSION_KEY
from customer import models as customer_models
from store import models as store_models


@ratelimit(key="ip", rate="3/h", method="POST", block=False, group="register")
def register_view(request):
    if not getattr(settings, "REGISTRATION_ENABLED", False):
        messages.error(
            request,
            "Регистрация через сайт отключена. Обратитесь к администратору.",
        )
        return redirect("store:index")

    if request.user.is_authenticated:
        return redirect("store:index")

    if getattr(request, "limited", False) and request.method == "POST":
        messages.error(
            request,
            "Слишком много попыток регистрации с этого адреса. Попробуйте позже.",
        )
        form = userauths_forms.UserRegisterForm()
        return render(request, "userauths/sign-up.html", {"form": form})

    if request.method == "POST":
        form = userauths_forms.UserRegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            if userauths_models.User.objects.filter(email__iexact=email).exists():
                messages.success(
                    request,
                    "Если этот адрес можно использовать для регистрации, на него отправлены инструкции. "
                    "Проверьте почту и папку «Спам». Если письма нет, возможно, аккаунт уже существует.",
                )
                return redirect("userauths:sign-in")
            else:
                user = userauths_models.User(email=email, is_active=False)
                user.set_password(form.cleaned_data["password1"])
                full = form.cleaned_data["full_name"].strip().split(" ", 1)
                user.first_name = full[0]
                user.last_name = full[1] if len(full) > 1 else ""
                user.save()
                userauths_models.Profile.objects.create(
                    user=user,
                    full_name=form.cleaned_data["full_name"],
                    mobile=form.cleaned_data["mobile"],
                    user_type="guest",
                )
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = account_activation_token.make_token(user)
                link = request.build_absolute_uri(
                    reverse(
                        "userauths:verify-email",
                        kwargs={"uidb64": uid, "token": token},
                    )
                )
                subject = "Подтвердите регистрацию на ASCO.KG"
                body = (
                    "Здравствуйте,\n\n"
                    "Для завершения регистрации перейдите по ссылке (действительна ограниченное время):\n"
                    f"{link}\n\n"
                    "Если вы не регистрировались, проигнорируйте это письмо.\n"
                )
                try:
                    send_mail(
                        subject,
                        body,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                    messages.success(
                        request,
                        "Аккаунт создан. Проверьте почту и перейдите по ссылке для активации.",
                    )
                    return redirect("userauths:sign-in")
                except Exception:
                    user.delete()
                    messages.error(
                        request,
                        "Не удалось отправить письмо. Проверьте настройки почты и попробуйте позже.",
                    )
    else:
        form = userauths_forms.UserRegisterForm()

    return render(request, "userauths/sign-up.html", {"form": form})


def verify_email_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = userauths_models.User.objects.get(pk=uid)
    except (
        TypeError,
        ValueError,
        OverflowError,
        userauths_models.User.DoesNotExist,
    ):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save(update_fields=["is_active"])
        messages.success(request, "Email подтверждён. Теперь вы можете войти.")
        return redirect("userauths:sign-in")

    messages.error(
        request,
        "Ссылка подтверждения недействительна или устарела. Запросите новую регистрацию или обратитесь в поддержку.",
    )
    return redirect("userauths:sign-in")


@ratelimit(key="ip", rate="5/m", method="POST", block=False)
def login_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "Вы уже вошли в систему")
        return redirect("store:index")

    if getattr(request, "limited", False) and request.method == "POST":
        messages.error(
            request,
            "Слишком много попыток входа с этого адреса. Подождите около минуты.",
        )
        form = userauths_forms.LoginForm()
        return render(request, "userauths/sign-in.html", {"form": form})

    if request.method == "POST":
        form = userauths_forms.LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            captcha_verified = form.cleaned_data.get("captcha", False)

            if not captcha_verified:
                messages.error(
                    request,
                    "Проверка капчи не удалась. Пожалуйста, попробуйте снова.",
                )
            else:
                user = authenticate(request, email=email, password=password)
                if user is not None:
                    if not user.is_active:
                        messages.error(
                            request,
                            "Аккаунт не активирован. Подтвердите email по ссылке из письма.",
                        )
                    else:
                        login(request, user)
                        session_ids = list(
                            request.session.get(WISHLIST_SESSION_KEY) or []
                        )
                        try:
                            for pid in session_ids:
                                pid = int(pid)
                                product = store_models.Product.objects.filter(
                                    id=pid
                                ).first()
                                if product:
                                    customer_models.Wishlist.objects.get_or_create(
                                        product=product, user=request.user
                                    )
                        except (TypeError, ValueError):
                            pass
                        if WISHLIST_SESSION_KEY in request.session:
                            del request.session[WISHLIST_SESSION_KEY]
                            request.session.modified = True
                        messages.success(request, "Вы вошли в систему")
                        next_url = request.GET.get("next", "store:index")
                        return redirect_after_login(request, next_url, "store:index")
                else:
                    messages.error(
                        request,
                        "Неверный email или пароль.",
                    )
    else:
        form = userauths_forms.LoginForm()

    return render(request, "userauths/sign-in.html", {"form": form})


def logout_view(request):
    if "cart_id" in request.session:
        cart_id = request.session["cart_id"]
    else:
        cart_id = None
    logout(request)
    if cart_id is not None:
        request.session["cart_id"] = cart_id
        request.session.modified = True
    messages.success(request, "Вы вышли из системы.")
    return redirect("userauths:sign-in")


def handler404(request, exception, *args, **kwargs):
    context = {}
    response = render(request, "userauths/404.html", context)
    response.status_code = 404
    return response


def handler500(request, *args, **kwargs):
    context = {}
    response = render(request, "userauths/500.html", context)
    response.status_code = 500
    return response


@method_decorator(
    ratelimit(key="ip", rate="5/m", method="POST", block=False),
    name="post",
)
class ManagerLoginView(View):
    template_name = "userauths/manager_login.html"

    def get(self, request):
        if (
            request.user.is_authenticated
            and (
                request.user.is_staff
                or request.user.is_superuser
                or getattr(request.user, "role", None)
                in ("manager", "superadmin")
            )
        ):
            return redirect("vendor:dashboard")

        form = userauths_forms.ManagerLoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        if getattr(request, "limited", False):
            messages.error(
                request,
                "Слишком много попыток входа с этого адреса. Подождите около минуты.",
            )
            form = userauths_forms.ManagerLoginForm()
            return render(request, self.template_name, {"form": form})

        form = userauths_forms.ManagerLoginForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user = authenticate(request, email=email, password=password)

            if user and user.is_active:
                if not (user.is_staff or user.is_superuser):
                    form.add_error(
                        None,
                        "У вас нет прав доступа к панели менеджера.",
                    )
                    messages.error(
                        request,
                        "У вас нет прав доступа к панели менеджера.",
                    )
                else:
                    login(request, user)
                    messages.success(request, "Вы вошли в панель менеджера.")
                    next_url = request.GET.get("next") or reverse("vendor:dashboard")
                    return redirect_after_login(request, next_url, "vendor:dashboard")
            else:
                form.add_error(None, "Неверный email или пароль.")
                messages.error(request, "Неверный email или пароль.")

        return render(request, self.template_name, {"form": form})
