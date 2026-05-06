from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import json

from notes.models import Note, Tag, ChecklistItem
from workspaces.models import Workspace, WorkspaceMember, WorkspaceTask
from .models import SystemAnnouncement, AdminActivityLog


def is_admin(user):
    return user.is_authenticated and user.is_staff


def admin_required(view_func):
    return login_required(user_passes_test(is_admin, login_url='/')(view_func))


def log_admin_action(admin, action, target=''):
    AdminActivityLog.objects.create(admin=admin, action=action, target=target)


# ── Dashboard ────────────────────────────────────────────

@admin_required
def admin_dashboard(request):
    now = timezone.now()
    today = now.date()

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_notes = Note.objects.count()
    total_tasks = WorkspaceTask.objects.count()
    total_workspaces = Workspace.objects.count()
    total_tags = Tag.objects.count()

    # New users in last 7 days
    week_ago = now - timedelta(days=7)
    new_users_week = User.objects.filter(date_joined__gte=week_ago).count()
    new_notes_week = Note.objects.filter(created_at__gte=week_ago).count()

    # Most active users (by note count)
    top_users = (
        User.objects.annotate(note_count=Count('notes'))
        .filter(note_count__gt=0)
        .order_by('-note_count')[:5]
    )

    # Users who haven't logged in for 30+ days
    thirty_days_ago = now - timedelta(days=30)
    inactive_users = User.objects.filter(
        last_login__lt=thirty_days_ago, is_active=True
    ).count()

    # Recent admin activity
    recent_logs = AdminActivityLog.objects.select_related('admin')[:10]

    # Active announcements
    announcements = SystemAnnouncement.objects.filter(
        is_active=True
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )[:5]

    # Chart data: notes per day last 7 days
    notes_chart = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = Note.objects.filter(created_at__date=day).count()
        notes_chart.append({'date': day.strftime('%b %d'), 'count': count})

    # User registrations last 7 days
    users_chart = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = User.objects.filter(date_joined__date=day).count()
        users_chart.append({'date': day.strftime('%b %d'), 'count': count})

    return render(request, 'custom_admin/dashboard.html', {
        'total_users': total_users,
        'active_users': active_users,
        'total_notes': total_notes,
        'total_tasks': total_tasks,
        'total_workspaces': total_workspaces,
        'total_tags': total_tags,
        'new_users_week': new_users_week,
        'new_notes_week': new_notes_week,
        'top_users': top_users,
        'inactive_users': inactive_users,
        'recent_logs': recent_logs,
        'announcements': announcements,
        'notes_chart_json': json.dumps(notes_chart),
        'users_chart_json': json.dumps(users_chart),
    })


# ── User Management ──────────────────────────────────────

@admin_required
def user_list(request):
    q = request.GET.get('q', '').strip()
    filter_type = request.GET.get('filter', 'all')

    users = User.objects.annotate(
        note_count=Count('notes', distinct=True),
        workspace_count=Count('owned_workspaces', distinct=True),
    ).order_by('-date_joined')

    if q:
        users = users.filter(
            Q(username__icontains=q) | Q(email__icontains=q)
        )

    if filter_type == 'active':
        users = users.filter(is_active=True)
    elif filter_type == 'inactive':
        users = users.filter(is_active=False)
    elif filter_type == 'staff':
        users = users.filter(is_staff=True)

    return render(request, 'custom_admin/user_list.html', {
        'users': users,
        'q': q,
        'filter_type': filter_type,
        'total': users.count(),
    })


@admin_required
def user_detail(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    notes = Note.objects.filter(user=target_user).order_by('-updated_at')[:10]
    workspaces_owned = Workspace.objects.filter(owner=target_user)
    memberships = WorkspaceMember.objects.filter(user=target_user).select_related('workspace')
    return render(request, 'custom_admin/user_detail.html', {
        'target_user': target_user,
        'notes': notes,
        'workspaces_owned': workspaces_owned,
        'memberships': memberships,
    })


@admin_required
@require_POST
def user_toggle_active(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if target_user == request.user:
        messages.error(request, "You can't deactivate yourself.")
        return redirect('admin_user_list')
    target_user.is_active = not target_user.is_active
    target_user.save()
    status = 'activated' if target_user.is_active else 'deactivated'
    log_admin_action(request.user, f'User {status}', target_user.username)
    messages.success(request, f'{target_user.username} {status}.')
    return redirect('admin_user_list')


@admin_required
@require_POST
def user_toggle_staff(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if target_user == request.user:
        messages.error(request, "You can't change your own staff status.")
        return redirect('admin_user_list')
    target_user.is_staff = not target_user.is_staff
    target_user.save()
    status = 'granted staff' if target_user.is_staff else 'revoked staff from'
    log_admin_action(request.user, f'Admin {status} user', target_user.username)
    messages.success(request, f'Staff status updated for {target_user.username}.')
    return redirect('admin_user_list')


@admin_required
@require_POST
def user_delete(request, pk):
    target_user = get_object_or_404(User, pk=pk)
    if target_user == request.user:
        messages.error(request, "You can't delete yourself.")
        return redirect('admin_user_list')
    username = target_user.username
    target_user.delete()
    log_admin_action(request.user, 'Deleted user', username)
    messages.success(request, f'User "{username}" deleted permanently.')
    return redirect('admin_user_list')


# ── Announcements ────────────────────────────────────────

@admin_required
def announcement_list(request):
    announcements = SystemAnnouncement.objects.all()
    return render(request, 'custom_admin/announcements.html', {
        'announcements': announcements,
    })


@admin_required
@require_POST
def announcement_create(request):
    title = request.POST.get('title', '').strip()
    message = request.POST.get('message', '').strip()
    level = request.POST.get('level', 'info')
    expires_at = request.POST.get('expires_at') or None

    if not title or not message:
        messages.error(request, 'Title and message are required.')
        return redirect('admin_announcements')

    ann = SystemAnnouncement.objects.create(
        title=title, message=message, level=level,
        created_by=request.user, expires_at=expires_at
    )
    log_admin_action(request.user, 'Created announcement', title)
    messages.success(request, 'Announcement created.')
    return redirect('admin_announcements')


@admin_required
@require_POST
def announcement_toggle(request, pk):
    ann = get_object_or_404(SystemAnnouncement, pk=pk)
    ann.is_active = not ann.is_active
    ann.save()
    messages.success(request, 'Announcement updated.')
    return redirect('admin_announcements')


@admin_required
@require_POST
def announcement_delete(request, pk):
    ann = get_object_or_404(SystemAnnouncement, pk=pk)
    ann.delete()
    messages.success(request, 'Announcement deleted.')
    return redirect('admin_announcements')


# ── Activity Logs ─────────────────────────────────────────

@admin_required
def activity_logs(request):
    logs = AdminActivityLog.objects.select_related('admin').all()
    return render(request, 'custom_admin/activity_logs.html', {'logs': logs})
