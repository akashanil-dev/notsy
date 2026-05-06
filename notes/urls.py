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
    path('notes/<int:pk>/archive/', views.note_archive, name='note_archive'),
    path('notes/<int:pk>/restore/', views.note_restore, name='note_restore'),
    path('notes/<int:pk>/pin/', views.note_toggle_pin, name='note_toggle_pin'),
    path('notes/<int:pk>/color/', views.note_update_color, name='note_update_color'),

    # Tags
    path('tags/create/', views.tag_create, name='tag_create'),
    path('tags/<int:pk>/delete/', views.tag_delete, name='tag_delete'),

    # Account
    path('settings/', views.account_settings, name='account_settings'),
]
