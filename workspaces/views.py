import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone

from .models import Workspace, WorkspaceMember, WorkspaceNote, WorkspaceTask, WorkspaceActivity
from notes.models import Note


def log_activity(workspace, user, action, detail=''):
    WorkspaceActivity.objects.create(
        workspace=workspace, user=user, action=action, detail=detail
    )


def get_workspace_or_403(request, pk):
    """Return workspace if user is a member (owner or WorkspaceMember), else 403."""
    workspace = get_object_or_404(Workspace, pk=pk)
    if workspace.owner == request.user:
        return workspace, 'owner'
    try:
        member = workspace.members.get(user=request.user)
        return workspace, member.role
    except WorkspaceMember.DoesNotExist:
        return None, None


# ── Workspace List / Create ──────────────────────────────

@login_required
def workspace_list(request):
    owned = Workspace.objects.filter(owner=request.user)
    memberships = WorkspaceMember.objects.filter(user=request.user).select_related('workspace', 'workspace__owner')
    member_workspaces = [m.workspace for m in memberships]
    return render(request, 'workspaces/workspace_list.html', {
        'owned_workspaces': owned,
        'member_workspaces': member_workspaces,
    })


@login_required
@require_POST
def workspace_create(request):
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    if not name:
        messages.error(request, 'Workspace name is required.')
        return redirect('workspace_list')
    if len(name) > 100:
        messages.error(request, 'Workspace name too long.')
        return redirect('workspace_list')

    ws = Workspace.objects.create(name=name, description=description, owner=request.user)
    log_activity(ws, request.user, 'workspace_created', ws.name)
    messages.success(request, f'Workspace "{ws.name}" created.')
    return redirect('workspace_detail', pk=ws.pk)


# ── Workspace Detail ─────────────────────────────────────

@login_required
def workspace_detail(request, pk):
    workspace, role = get_workspace_or_403(request, pk)
    if workspace is None:
        messages.error(request, 'You do not have access to this workspace.')
        return redirect('workspace_list')

    notes = WorkspaceNote.objects.filter(workspace=workspace).select_related('note', 'added_by')
    tasks = WorkspaceTask.objects.filter(workspace=workspace).select_related('created_by', 'assigned_to')
    members = WorkspaceMember.objects.filter(workspace=workspace).select_related('user')
    activities = WorkspaceActivity.objects.filter(workspace=workspace)[:20]

    # All users for invite (excluding owner and existing members)
    member_ids = [m.user.id for m in members] + [workspace.owner.id]
    available_users = User.objects.exclude(id__in=member_ids).order_by('username')

    return render(request, 'workspaces/workspace_detail.html', {
        'workspace': workspace,
        'role': role,
        'notes': notes,
        'tasks': tasks,
        'members': members,
        'activities': activities,
        'available_users': available_users,
        'can_edit': role in ('owner', 'editor'),
        'is_owner': role == 'owner',
    })


# ── Workspace Edit / Delete ──────────────────────────────

@login_required
@require_POST
def workspace_edit(request, pk):
    workspace = get_object_or_404(Workspace, pk=pk, owner=request.user)
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    if not name:
        messages.error(request, 'Workspace name is required.')
        return redirect('workspace_detail', pk=pk)
    workspace.name = name
    workspace.description = description
    workspace.save()
    messages.success(request, 'Workspace updated.')
    return redirect('workspace_detail', pk=pk)


@login_required
@require_POST
def workspace_delete(request, pk):
    workspace = get_object_or_404(Workspace, pk=pk, owner=request.user)
    name = workspace.name
    workspace.delete()
    messages.success(request, f'Workspace "{name}" deleted.')
    return redirect('workspace_list')


# ── Members ──────────────────────────────────────────────

@login_required
@require_POST
def workspace_invite(request, pk):
    workspace = get_object_or_404(Workspace, pk=pk, owner=request.user)
    username = request.POST.get('username', '').strip()
    role = request.POST.get('role', 'viewer')
    if role not in ('editor', 'viewer'):
        role = 'viewer'

    try:
        user = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        messages.error(request, f'User "{username}" not found.')
        return redirect('workspace_detail', pk=pk)

    if user == workspace.owner:
        messages.error(request, 'Owner is already in the workspace.')
        return redirect('workspace_detail', pk=pk)

    member, created = WorkspaceMember.objects.get_or_create(
        workspace=workspace, user=user,
        defaults={'role': role, 'invited_by': request.user}
    )
    if not created:
        messages.error(request, f'{user.username} is already a member.')
    else:
        log_activity(workspace, request.user, 'member_invited', f'{user.username} as {role}')
        messages.success(request, f'{user.username} added as {role}.')
    return redirect('workspace_detail', pk=pk)


@login_required
@require_POST
def workspace_remove_member(request, pk, user_pk):
    workspace = get_object_or_404(Workspace, pk=pk, owner=request.user)
    user = get_object_or_404(User, pk=user_pk)
    WorkspaceMember.objects.filter(workspace=workspace, user=user).delete()
    log_activity(workspace, request.user, 'member_left', user.username)
    messages.success(request, f'{user.username} removed from workspace.')
    return redirect('workspace_detail', pk=pk)


@login_required
@require_POST
def workspace_leave(request, pk):
    workspace, role = get_workspace_or_403(request, pk)
    if workspace is None or role == 'owner':
        messages.error(request, 'You cannot leave a workspace you own.')
        return redirect('workspace_list')
    WorkspaceMember.objects.filter(workspace=workspace, user=request.user).delete()
    messages.success(request, f'You left "{workspace.name}".')
    return redirect('workspace_list')


@login_required
@require_POST
def workspace_change_role(request, pk, user_pk):
    workspace = get_object_or_404(Workspace, pk=pk, owner=request.user)
    member = get_object_or_404(WorkspaceMember, workspace=workspace, user_id=user_pk)
    new_role = request.POST.get('role', 'viewer')
    if new_role in ('editor', 'viewer'):
        member.role = new_role
        member.save()
        messages.success(request, f'Role updated to {new_role}.')
    return redirect('workspace_detail', pk=pk)


# ── Tasks ────────────────────────────────────────────────

@login_required
@require_POST
def task_create(request, pk):
    workspace, role = get_workspace_or_403(request, pk)
    if workspace is None or role not in ('owner', 'editor'):
        messages.error(request, 'You do not have permission to create tasks.')
        return redirect('workspace_list')

    title = request.POST.get('title', '').strip()
    if not title:
        messages.error(request, 'Task title is required.')
        return redirect('workspace_detail', pk=pk)

    description = request.POST.get('description', '').strip()
    priority = request.POST.get('priority', 'medium')
    due_date = request.POST.get('due_date') or None
    assigned_username = request.POST.get('assigned_to', '').strip()

    assigned_to = None
    if assigned_username:
        try:
            assigned_to = User.objects.get(username__iexact=assigned_username)
        except User.DoesNotExist:
            pass

    task = WorkspaceTask.objects.create(
        workspace=workspace,
        title=title,
        description=description,
        created_by=request.user,
        assigned_to=assigned_to,
        priority=priority,
        due_date=due_date,
    )
    log_activity(workspace, request.user, 'task_created', title)
    messages.success(request, 'Task created.')
    return redirect('workspace_detail', pk=pk)


@login_required
@require_POST
def task_toggle(request, pk, task_pk):
    workspace, role = get_workspace_or_403(request, pk)
    if workspace is None or role not in ('owner', 'editor'):
        return JsonResponse({'error': 'No permission'}, status=403)

    task = get_object_or_404(WorkspaceTask, pk=task_pk, workspace=workspace)
    task.is_done = not task.is_done
    task.save()
    if task.is_done:
        log_activity(workspace, request.user, 'task_completed', task.title)
    return JsonResponse({'is_done': task.is_done})


@login_required
@require_POST
def task_delete(request, pk, task_pk):
    workspace, role = get_workspace_or_403(request, pk)
    if workspace is None or role not in ('owner', 'editor'):
        messages.error(request, 'No permission.')
        return redirect('workspace_detail', pk=pk)

    task = get_object_or_404(WorkspaceTask, pk=task_pk, workspace=workspace)
    task.delete()
    messages.success(request, 'Task deleted.')
    return redirect('workspace_detail', pk=pk)


# ── Notes in Workspace ───────────────────────────────────

@login_required
@require_POST
def workspace_add_note(request, pk):
    workspace, role = get_workspace_or_403(request, pk)
    if workspace is None or role not in ('owner', 'editor'):
        messages.error(request, 'No permission.')
        return redirect('workspace_list')

    note_id = request.POST.get('note_id')
    note = get_object_or_404(Note, pk=note_id, user=request.user)

    _, created = WorkspaceNote.objects.get_or_create(
        workspace=workspace, note=note,
        defaults={'added_by': request.user}
    )
    if created:
        log_activity(workspace, request.user, 'note_added', note.title or f'Note #{note.pk}')
        messages.success(request, 'Note added to workspace.')
    else:
        messages.info(request, 'Note is already in workspace.')
    return redirect('workspace_detail', pk=pk)


@login_required
@require_POST
def workspace_remove_note(request, pk, note_pk):
    workspace, role = get_workspace_or_403(request, pk)
    if workspace is None or role not in ('owner', 'editor'):
        messages.error(request, 'No permission.')
        return redirect('workspace_list')

    wn = get_object_or_404(WorkspaceNote, workspace=workspace, pk=note_pk)
    title = wn.note.title or f'Note #{wn.note.pk}'
    wn.delete()
    log_activity(workspace, request.user, 'note_removed', title)
    messages.success(request, 'Note removed from workspace.')
    return redirect('workspace_detail', pk=pk)
