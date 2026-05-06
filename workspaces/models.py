from django.db import models
from django.contrib.auth.models import User
from notes.models import Note


class Workspace(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_workspaces')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    def get_member_role(self, user):
        """Return the role of a user in this workspace, or None if not a member."""
        if user == self.owner:
            return 'owner'
        try:
            member = self.members.get(user=user)
            return member.role
        except WorkspaceMember.DoesNotExist:
            return None

    def can_edit(self, user):
        role = self.get_member_role(user)
        return role in ('owner', 'editor')

    def can_view(self, user):
        return self.get_member_role(user) is not None

    def is_owner(self, user):
        return self.owner == user


class WorkspaceMember(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workspace_memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='viewer')
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_invitations')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['workspace', 'user']
        ordering = ['joined_at']

    def __str__(self):
        return f'{self.user.username} — {self.role} in {self.workspace.name}'


class WorkspaceNote(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='notes')
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='workspace_links')
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='added_workspace_notes')
    added_at = models.DateTimeField(auto_now_add=True)
    is_shared = models.BooleanField(default=True)

    class Meta:
        unique_together = ['workspace', 'note']
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.note} in {self.workspace.name}'


class WorkspaceTask(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_workspace_tasks')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_workspace_tasks')
    is_done = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['is_done', '-priority', '-created_at']

    def __str__(self):
        return self.title


class WorkspaceActivity(models.Model):
    ACTION_CHOICES = [
        ('note_added', 'Added a note'),
        ('note_removed', 'Removed a note'),
        ('task_created', 'Created a task'),
        ('task_completed', 'Completed a task'),
        ('member_joined', 'Joined workspace'),
        ('member_left', 'Left workspace'),
        ('member_invited', 'Invited a member'),
        ('workspace_created', 'Created workspace'),
    ]

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='workspace_activities')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    detail = models.CharField(max_length=300, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} — {self.action}'
