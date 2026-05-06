from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('users/', views.user_list, name='admin_user_list'),
    path('users/<int:pk>/', views.user_detail, name='admin_user_detail'),
    path('users/<int:pk>/toggle-active/', views.user_toggle_active, name='admin_user_toggle_active'),
    path('users/<int:pk>/toggle-staff/', views.user_toggle_staff, name='admin_user_toggle_staff'),
    path('users/<int:pk>/delete/', views.user_delete, name='admin_user_delete'),
    path('announcements/', views.announcement_list, name='admin_announcements'),
    path('announcements/create/', views.announcement_create, name='admin_announcement_create'),
    path('announcements/<int:pk>/toggle/', views.announcement_toggle, name='admin_announcement_toggle'),
    path('announcements/<int:pk>/delete/', views.announcement_delete, name='admin_announcement_delete'),
    path('logs/', views.activity_logs, name='admin_activity_logs'),
]
