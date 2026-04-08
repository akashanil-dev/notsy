import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Note, ChecklistItem
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
    notes = request.user.notes.all()

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        notes = notes.filter(title__icontains=q) | notes.filter(content__icontains=q)
        notes = notes.distinct()

    pinned = notes.filter(pinned=True)
    others = notes.filter(pinned=False)

    return render(request, 'notes/dashboard.html', {
        'pinned_notes': pinned,
        'notes': others,
        'search_query': q,
    })


# ── Note CRUD ───────────────────────────────────────────────

@login_required
def note_create(request):
    form = NoteForm(initial={'note_type': 'text'})
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()

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

            messages.success(request, 'Note created.')
            return redirect('dashboard')

    return render(request, 'notes/note_form.html', {
        'form': form,
        'is_edit': False,
    })


@login_required
def note_edit(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    form = NoteForm(instance=note)

    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            note = form.save()

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

            messages.success(request, 'Note updated.')
            return redirect('dashboard')

    checklist_items = []
    if note.note_type == 'checklist':
        checklist_items = list(note.checklist_items.values('text', 'is_checked', 'order'))

    return render(request, 'notes/note_form.html', {
        'form': form,
        'note': note,
        'is_edit': True,
        'checklist_items_json': json.dumps(checklist_items),
    })


@login_required
@require_POST
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    note.delete()
    messages.success(request, 'Note deleted.')
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
        'member_since': request.user.date_joined,
    }

    return render(request, 'notes/settings.html', {
        'pw_form': pw_form,
        'del_form': del_form,
        'stats': stats,
    })
