from django.urls import path

from . import views

urlpatterns = [
    path("", views.RunListView.as_view(), name="run-list"),
    path("create/", views.RunCreateView.as_view(), name="run-create"),
    path("<int:pk>/", views.RunDetailView.as_view(), name="run-detail"),
    path("<int:pk>/edit/", views.RunUpdateView.as_view(), name="run-update"),
    path("<int:pk>/delete/", views.RunDeleteView.as_view(), name="run-delete"),
]
