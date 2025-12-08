from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.views import View
from django.urls import reverse

from userauths import models as userauths_models
from userauths import forms as userauths_forms


def register_view(request):
    messages.error(request, "Регистрация через сайт отключена. Обратитесь к администратору.")
    return redirect('store:index')

def login_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "Вы уже вошли в систему")
        return redirect('store:index')
    
    if request.method == 'POST':
        form = userauths_forms.LoginForm(request.POST)  
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            captcha_verified = form.cleaned_data.get('captcha', False)  

            if captcha_verified:
                try:
                    user_instance = userauths_models.User.objects.get(email=email, is_active=True)
                    user_authenticate = authenticate(request, email=email, password=password)

                    if user_instance is not None:
                        login(request, user_authenticate)
                        messages.success(request, "Вы вошли в систему")
                        next_url = request.GET.get("next", 'store:index')

                        print("next_url ========", next_url)
                        if next_url == '/undefined/':
                            return redirect('store:index')
                        
                        if next_url == 'undefined':
                            return redirect('store:index')

                        if next_url is None or not next_url.startswith('/'):
                            return redirect('store:index')

                        return redirect(next_url)

                    else:
                        messages.error(request, 'Неверное имя пользователя или пароль')
                except userauths_models.User.DoesNotExist:
                    messages.error(request, 'Пользователь не существует')
            else:
                messages.error(request, 'Проверка капчи не удалась. Пожалуйста, попробуйте снова.')

    else:
        form = userauths_forms.LoginForm()  

    return render(request, "userauths/sign-in.html", {'form': form})

def logout_view(request):
    if "cart_id" in request.session:
        cart_id = request.session['cart_id']
    else:
        cart_id = None
    logout(request)
    request.session['cart_id'] = cart_id
    messages.success(request, 'Вы вышли из системы.')
    return redirect("userauths:sign-in")

def handler404(request, exception, *args, **kwargs):
    context = {}
    response = render(request, 'userauths/404.html', context)
    response.status_code = 404
    return response

def handler500(request, *args, **kwargs):
    context = {}
    response = render(request, 'userauths/500.html', context)
    response.status_code = 500
    return response


class ManagerLoginView(View):
    template_name = "userauths/manager_login.html"

    def get(self, request):
        if (
            request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser or getattr(request.user, "role", None) in ("manager", "superadmin"))
        ):
            return redirect('vendor:dashboard')

        form = userauths_forms.ManagerLoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = userauths_forms.ManagerLoginForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user = authenticate(request, email=email, password=password)

            if user and user.is_active:
                if not (user.is_staff or user.is_superuser):
                    form.add_error(None, "У вас нет прав доступа к панели менеджера.")
                    messages.error(request, "У вас нет прав доступа к панели менеджера.")
                else:
                    login(request, user)
                    messages.success(request, "Вы вошли в панель менеджера.")
                    next_url = request.GET.get("next")
                    if not next_url:
                        next_url = reverse("vendor:dashboard")
                    return redirect(next_url)
            else:
                form.add_error(None, "Неверный email или пароль.")
                messages.error(request, "Неверный email или пароль.")

        return render(request, self.template_name, {"form": form})

