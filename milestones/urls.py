
from django.urls import path
from . import views

urlpatterns = [
    path('', views.MilestoneListView.as_view(), name='milestone-list'),
    path('create/', views.MilestoneCreateView.as_view(), name='milestone-create'),
    path('<int:pk>/', views.MilestoneDetailView.as_view(), name='milestone-detail'),
    path('<int:pk>/edit/', views.MilestoneUpdateView.as_view(), name='milestone-update'),
    path('<int:pk>/delete/', views.MilestoneDeleteView.as_view(), name='milestone-delete'),
    path('<int:pk>/update/', views.MilestoneUpdateCreateView.as_view(), name='milestone-update-create'),
]
