from django.urls import path
from . import views

urlpatterns = [
    path('', views.workspace_list, name='workspace_list'),
    path('create/', views.workspace_create, name='workspace_create'),
    path('<int:pk>/', views.workspace_detail, name='workspace_detail'),
    path('<int:pk>/edit/', views.workspace_edit, name='workspace_edit'),
    path('<int:pk>/delete/', views.workspace_delete, name='workspace_delete'),
    path('<int:pk>/leave/', views.workspace_leave, name='workspace_leave'),

    # Members
    path('<int:pk>/invite/', views.workspace_invite, name='workspace_invite'),
    path('<int:pk>/members/<int:user_pk>/remove/', views.workspace_remove_member, name='workspace_remove_member'),
    path('<int:pk>/members/<int:user_pk>/role/', views.workspace_change_role, name='workspace_change_role'),

    # Tasks
    path('<int:pk>/tasks/create/', views.task_create, name='task_create'),
    path('<int:pk>/tasks/<int:task_pk>/toggle/', views.task_toggle, name='task_toggle'),
    path('<int:pk>/tasks/<int:task_pk>/delete/', views.task_delete, name='task_delete'),

    # Notes
    path('<int:pk>/notes/add/', views.workspace_add_note, name='workspace_add_note'),
    path('<int:pk>/notes/<int:note_pk>/remove/', views.workspace_remove_note, name='workspace_remove_note'),
]
