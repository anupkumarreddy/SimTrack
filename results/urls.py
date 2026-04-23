
from django.urls import path
from . import views

urlpatterns = [
    path('', views.ResultListView.as_view(), name='result-list'),
    path('<int:pk>/', views.ResultDetailView.as_view(), name='result-detail'),
]
