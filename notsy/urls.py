from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('notes.urls')),
    path('workspaces/', include('workspaces.urls')),
    path('manage/', include('custom_admin.urls')),
]
