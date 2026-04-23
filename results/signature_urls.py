
from django.urls import path
from . import views

urlpatterns = [
    path('<int:pk>/', views.FailureSignatureDetailView.as_view(), name='failure-signature-detail'),
]
