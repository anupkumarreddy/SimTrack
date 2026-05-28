from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import HealthView

router = DefaultRouter()

urlpatterns = [
    path("health/", HealthView.as_view(), name="api-health"),
    path("", include(router.urls)),
]
