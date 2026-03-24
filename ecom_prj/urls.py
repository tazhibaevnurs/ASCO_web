"""
URL configuration for ecom_prj project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView, RedirectView
from userauths import views as userauths_views
from store.sitemaps import StaticViewSitemap, ProductSitemap, BlogSitemap


sitemaps = {
    "static": StaticViewSitemap,
    "products": ProductSitemap,
    "blog": BlogSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('manager-login/', userauths_views.ManagerLoginView.as_view(), name='manager-login'),
    path('', include("store.urls")),
    path('auth/', include("userauths.urls")),
    path('customer/', include("customer.urls")),
    path('vendor/', include("vendor.urls")),
    path('blog/', include("blog.urls")),

    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='userauths/password/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='userauths/password/password_reset_done.html'), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='userauths/password/password_reset_confirmation.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='userauths/password/password_reset_complete.html'), name='password_reset_complete'),


    path("ckeditor5/", include('django_ckeditor_5.urls')),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path("google34daf5010f2256e5.html", TemplateView.as_view(template_name="google34daf5010f2256e5.html", content_type="text/html")),
    path("favicon.ico", RedirectView.as_view(url="/static/assets/img/favicon-v2.png", permanent=True)),

]

# Serve static and media files in development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)