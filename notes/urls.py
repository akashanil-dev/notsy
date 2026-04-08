from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('notes/', views.dashboard, name='dashboard'),

    # Note CRUD
    path('notes/new/', views.note_create, name='note_create'),
    path('notes/<int:pk>/edit/', views.note_edit, name='note_edit'),
    path('notes/<int:pk>/delete/', views.note_delete, name='note_delete'),
    path('notes/<int:pk>/pin/', views.note_toggle_pin, name='note_toggle_pin'),
    path('notes/<int:pk>/color/', views.note_update_color, name='note_update_color'),

    # Account
    path('settings/', views.account_settings, name='account_settings'),
]
