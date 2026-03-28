from django.urls import path

from store import api_views

urlpatterns = [
    path("ai/generate/", api_views.ai_generate, name="ai_generate"),
]
