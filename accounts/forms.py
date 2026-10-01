from django import forms
from django.contrib.auth.models import User
from .models import Profile, Role

class UserAdminCreateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=Role.choices, initial=Role.DEPT_HEAD, widget=forms.Select(attrs={'class': 'form-select'}))
    department = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="-- None / University-wide --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from academics.models import Department
        self.fields['department'].queryset = Department.objects.all().order_by('name')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            profile = getattr(user, 'profile', None)
            if not profile:
                profile = Profile(user=user)
            profile.role = self.cleaned_data['role']
            profile.department = self.cleaned_data['department']
            profile.save()
        return user


class UserAdminUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=Role.choices, widget=forms.Select(attrs={'class': 'form-select'}))
    department = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="-- None / University-wide --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from academics.models import Department
        self.fields['department'].queryset = Department.objects.all().order_by('name')
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['role'].initial = self.instance.profile.role
            self.fields['department'].initial = self.instance.profile.department

    def save(self, commit=True):
        user = super().save(commit=commit)
        if hasattr(user, 'profile'):
            user.profile.role = self.cleaned_data['role']
            user.profile.department = self.cleaned_data['department']
            user.profile.save()
        return user
