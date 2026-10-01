from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from apps.accounts.models import UserProfile, UserRole


class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password"}))
    role = forms.ChoiceField(choices=UserRole.choices, widget=forms.Select(attrs={"class": "form-select"}))
    department = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Department of Statistics"}))

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email address"}),
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Last name"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("password_confirm")
        if p1 and p2 and p1 != p2:
            self.add_error("password_confirm", "Passwords do not match.")
        return cleaned_data


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}))

    def clean_username(self):
        username = self.cleaned_data.get("username", "")
        # Resolve username case-insensitively (e.g. 'darith' -> 'Darith')
        user = User.objects.filter(username__iexact=username).first()
        if user:
            return user.username
        return username


class UserProfileForm(forms.ModelForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    first_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))

    class Meta:
        model = UserProfile
        fields = ["role", "department"]
        widgets = {
            "role": forms.Select(attrs={"class": "form-select"}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
        }
