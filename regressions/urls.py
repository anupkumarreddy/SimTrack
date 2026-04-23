
from django.urls import path
from . import views

urlpatterns = [
    path('', views.RegressionListView.as_view(), name='regression-list'),
    path('create/', views.RegressionCreateView.as_view(), name='regression-create'),
    path('<int:pk>/', views.RegressionDetailView.as_view(), name='regression-detail'),
    path('<int:pk>/edit/', views.RegressionUpdateView.as_view(), name='regression-update'),
    path('<int:pk>/delete/', views.RegressionDeleteView.as_view(), name='regression-delete'),
]
