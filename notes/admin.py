from django.contrib import admin
from .models import Note, ChecklistItem


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 0


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'note_type', 'color', 'pinned', 'updated_at')
    list_filter = ('note_type', 'color', 'pinned')
    search_fields = ('title', 'content')
    inlines = [ChecklistItemInline]


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ('text', 'note', 'is_checked', 'order')
