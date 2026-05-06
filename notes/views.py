import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string

from django.http import JsonResponse
from django.urls import reverse

from .models import Note, ChecklistItem, Tag
from .forms import RegisterForm, LoginForm, NoteForm, ChangePasswordForm, DeleteAccountForm


# ── Auth Views ──────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    return render(request, 'notes/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            login(request, user)
            messages.success(request, 'Welcome to Notsy!')
            return redirect('dashboard')
    return render(request, 'notes/register.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# ── Dashboard ───────────────────────────────────────────────

@login_required
def dashboard(request):
    # Auto-delete trash older than 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    request.user.notes.filter(is_trashed=True, trashed_at__lte=thirty_days_ago).delete()

    notes = request.user.notes.all()

    # Filter by section
    section_filter = request.GET.get('filter', 'active')
    if section_filter == 'trash':
        notes = notes.filter(is_trashed=True)
    elif section_filter == 'archive':
        notes = notes.filter(is_archived=True, is_trashed=False)
    else:
        notes = notes.filter(is_trashed=False, is_archived=False)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        notes = notes.filter(
            Q(title__icontains=q) |
            Q(content__icontains=q) |
            Q(tags__name__icontains=q)
        ).distinct()

    # Tag filter
    tag_filter = request.GET.get('tag', '').strip()
    if tag_filter:
        notes = notes.filter(tags__name=tag_filter).distinct()

    pinned = notes.filter(pinned=True)
    others = notes.filter(pinned=False)

    # All user tags for the filter bar
    user_tags = request.user.tags.all()

    return render(request, 'notes/dashboard.html', {
        'pinned_notes': pinned,
        'notes': others,
        'search_query': q,
        'tag_filter': tag_filter,
        'user_tags': user_tags,
    })


# ── Note CRUD ───────────────────────────────────────────────

@login_required
def note_create(request):
    form = NoteForm(initial={'note_type': 'text'})
    user_tags = request.user.tags.all()

    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()

            # Handle tags
            tag_ids = request.POST.getlist('note_tags')
            if tag_ids:
                note.tags.set(tag_ids)

            # Handle checklist items if converted to list
            if note.note_type == 'checklist':
                items_json = request.POST.get('checklist_items', '[]')
                try:
                    items = json.loads(items_json)
                    for i, item in enumerate(items):
                        if item.get('text', '').strip():
                            ChecklistItem.objects.create(
                                note=note,
                                text=item['text'].strip(),
                                is_checked=item.get('is_checked', False),
                                order=i,
                            )
                except (json.JSONDecodeError, TypeError):
                    pass

            note.preview = render_to_string('notes/partials/note_preview.html', {'note': note})
            note.save(update_fields=['preview'])

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'ok', 'id': note.id, 'edit_url': reverse('note_edit', args=[note.id])})

            messages.success(request, 'Note created.')
            return redirect('dashboard')

    return render(request, 'notes/note_form.html', {
        'form': form,
        'is_edit': False,
        'user_tags': user_tags,
    })


@login_required
def note_edit(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    form = NoteForm(instance=note)
    user_tags = request.user.tags.all()

    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            note = form.save()

            # Handle tags
            tag_ids = request.POST.getlist('note_tags')
            note.tags.set(tag_ids)

            # Handle checklist items
            if note.note_type == 'checklist':
                note.checklist_items.all().delete()
                items_json = request.POST.get('checklist_items', '[]')
                try:
                    items = json.loads(items_json)
                    for i, item in enumerate(items):
                        if item.get('text', '').strip():
                            ChecklistItem.objects.create(
                                note=note,
                                text=item['text'].strip(),
                                is_checked=item.get('is_checked', False),
                                order=i,
                            )
                except (json.JSONDecodeError, TypeError):
                    pass
            else:
                # If converted back to text, remove checklist items
                note.checklist_items.all().delete()

            note.preview = render_to_string('notes/partials/note_preview.html', {'note': note})
            note.save(update_fields=['preview'])

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'ok'})

            messages.success(request, 'Note updated.')
            return redirect('dashboard')

    checklist_items = []
    if note.note_type == 'checklist':
        checklist_items = list(note.checklist_items.values('text', 'is_checked', 'order'))

    note_tag_ids = list(note.tags.values_list('id', flat=True))

    return render(request, 'notes/note_form.html', {
        'form': form,
        'note': note,
        'is_edit': True,
        'checklist_items_json': json.dumps(checklist_items),
        'user_tags': user_tags,
        'note_tag_ids': json.dumps(note_tag_ids),
    })


@login_required
@require_POST
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if note.is_trashed:
        note.delete()
        messages.success(request, 'Note permanently deleted.')
    else:
        note.is_trashed = True
        note.trashed_at = timezone.now()
        note.pinned = False
        note.save(update_fields=['is_trashed', 'trashed_at', 'pinned'])
        messages.success(request, 'Note moved to trash.')
    return redirect('dashboard')

@login_required
@require_POST
def note_archive(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    note.is_archived = not note.is_archived
    note.save(update_fields=['is_archived'])
    status = 'archived' if note.is_archived else 'unarchived'
    messages.success(request, f'Note {status}.')
    return redirect('dashboard')

@login_required
@require_POST
def note_restore(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if note.is_trashed:
        note.is_trashed = False
        note.trashed_at = None
        note.save(update_fields=['is_trashed', 'trashed_at'])
        messages.success(request, 'Note restored.')
    return redirect('dashboard')


@login_required
@require_POST
def note_toggle_pin(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    note.pinned = not note.pinned
    note.save()
    return JsonResponse({'pinned': note.pinned})


@login_required
@require_POST
def note_update_color(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    color = request.POST.get('color', 'default')
    valid_colors = [c[0] for c in Note.COLOR_CHOICES]
    if color in valid_colors:
        note.color = color
        note.save()
    return JsonResponse({'color': note.color})


# ── Tag management ──────────────────────────────────────────

@login_required
@require_POST
def tag_create(request):
    name = request.POST.get('name', '').strip()
    color = request.POST.get('color', 'fog').strip()

    if not name:
        return JsonResponse({'error': 'Tag name is required.'}, status=400)
    if len(name) > 50:
        return JsonResponse({'error': 'Tag name too long.'}, status=400)

    valid_colors = [c[0] for c in Tag.TAG_COLOR_CHOICES]
    if color not in valid_colors:
        color = 'fog'

    tag, created = Tag.objects.get_or_create(
        user=request.user,
        name__iexact=name,
        defaults={'name': name, 'color': color},
    )
    if not created:
        return JsonResponse({'error': 'Tag already exists.'}, status=400)

    return JsonResponse({
        'id': tag.id,
        'name': tag.name,
        'color': tag.color,
    })


@login_required
@require_POST
def tag_delete(request, pk):
    tag = get_object_or_404(Tag, pk=pk, user=request.user)
    tag.delete()
    return JsonResponse({'ok': True})


# ── Account Settings ────────────────────────────────────────

@login_required
def account_settings(request):
    pw_form = ChangePasswordForm()
    del_form = DeleteAccountForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'change_password':
            pw_form = ChangePasswordForm(request.POST)
            if pw_form.is_valid():
                if not request.user.check_password(pw_form.cleaned_data['current_password']):
                    messages.error(request, 'Current password is incorrect.')
                else:
                    request.user.set_password(pw_form.cleaned_data['new_password'])
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, 'Password changed successfully.')
                    pw_form = ChangePasswordForm()

        elif action == 'delete_account':
            del_form = DeleteAccountForm(request.POST)
            if del_form.is_valid():
                if del_form.cleaned_data['confirm_username'] != request.user.username:
                    messages.error(request, 'Username does not match.')
                else:
                    request.user.delete()
                    logout(request)
                    messages.success(request, 'Account deleted.')
                    return redirect('login')

    stats = {
        'total_notes': request.user.notes.count(),
        'text_notes': request.user.notes.filter(note_type='text').count(),
        'checklists': request.user.notes.filter(note_type='checklist').count(),
        'tags_count': request.user.tags.count(),
        'member_since': request.user.date_joined,
    }

    return render(request, 'notes/settings.html', {
        'pw_form': pw_form,
        'del_form': del_form,
        'stats': stats,
    })
