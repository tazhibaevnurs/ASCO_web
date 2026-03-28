from django.urls import path

from userauths import views

app_name = "userauths"

urlpatterns = [
    path("sign-up/", views.register_view, name="sign-up"),
    path(
        "verify-email/<uidb64>/<token>/",
        views.verify_email_view,
        name="verify-email",
    ),
    path("sign-in/", views.login_view, name="sign-in"),
    path("sign-out/", views.logout_view, name="sign-out"),
    # Сброс пароля: единые маршруты в ecom_prj/urls.py (password-reset/...), без дубликатов под /auth/.
]