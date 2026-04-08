from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import Note


class RegisterForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        min_length=3,
        widget=forms.TextInput(attrs={
            'placeholder': 'pick a username',
            'autocomplete': 'username',
            'id': 'register-username',
        })
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'create a password',
            'autocomplete': 'new-password',
            'id': 'register-password',
        })
    )
    password_confirm = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'confirm password',
            'autocomplete': 'new-password',
            'id': 'register-password-confirm',
        })
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('That username is already taken.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        pw2 = cleaned_data.get('password_confirm')
        if pw and pw2 and pw != pw2:
            self.add_error('password_confirm', 'Passwords do not match.')
        return cleaned_data


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'username',
            'autocomplete': 'username',
            'id': 'login-username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'password',
            'autocomplete': 'current-password',
            'id': 'login-password',
        })
    )


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'content', 'note_type', 'color', 'pinned']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Title',
                'id': 'note-title',
                'autocomplete': 'off',
            }),
            'content': forms.Textarea(attrs={
                'placeholder': 'Write something...',
                'id': 'note-content',
                'rows': 10,
            }),
            'note_type': forms.HiddenInput(),
            'color': forms.HiddenInput(),
            'pinned': forms.CheckboxInput(attrs={
                'id': 'note-pinned',
            }),
        }


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'current password',
            'id': 'current-password',
        })
    )
    new_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'new password',
            'id': 'new-password',
        })
    )
    new_password_confirm = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'confirm new password',
            'id': 'new-password-confirm',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('new_password')
        pw2 = cleaned_data.get('new_password_confirm')
        if pw and pw2 and pw != pw2:
            self.add_error('new_password_confirm', 'Passwords do not match.')
        return cleaned_data


class DeleteAccountForm(forms.Form):
    confirm_username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'type your username to confirm',
            'id': 'confirm-delete-username',
        })
    )
