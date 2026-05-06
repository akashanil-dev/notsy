from django.db import models
from django.contrib.auth.models import User


class Tag(models.Model):
    TAG_COLOR_CHOICES = [
        ('coral', 'Coral'),
        ('peach', 'Peach'),
        ('sand', 'Sand'),
        ('sage', 'Sage'),
        ('fog', 'Fog'),
        ('storm', 'Storm'),
        ('dusk', 'Dusk'),
        ('rose', 'Rose'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=10, choices=TAG_COLOR_CHOICES, default='fog')

    class Meta:
        ordering = ['name']
        unique_together = ['user', 'name']

    def __str__(self):
        return self.name


class Note(models.Model):
    NOTE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('checklist', 'Checklist'),
    ]

    COLOR_CHOICES = [
        ('default', 'Default'),
        ('coral', 'Coral'),
        ('peach', 'Peach'),
        ('sand', 'Sand'),
        ('sage', 'Sage'),
        ('fog', 'Fog'),
        ('storm', 'Storm'),
        ('dusk', 'Dusk'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=255, blank=True, default='')
    content = models.TextField(blank=True, default='')
    note_type = models.CharField(max_length=10, choices=NOTE_TYPE_CHOICES, default='text')
    color = models.CharField(max_length=10, choices=COLOR_CHOICES, default='default')
    pinned = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True, related_name='notes')
    is_trashed = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    preview = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pinned', '-updated_at']

    def __str__(self):
        return self.title or f'Note #{self.pk}'


class ChecklistItem(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='checklist_items')
    text = models.CharField(max_length=500)
    is_checked = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text
