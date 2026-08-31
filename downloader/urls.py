from django.urls import path

from . import views

app_name = "downloader"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/fetch/", views.api_fetch_info, name="api_fetch"),
    path("api/download/", views.api_download, name="api_download"),
]
