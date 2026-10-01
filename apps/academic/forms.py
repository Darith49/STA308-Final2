from django import forms
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile, UserRole
from apps.academic.models import Department, Program, Course, Student


class AdminUserCreateForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "user@university.edu"}))
    first_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "First Name"}))
    last_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Last Name"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Temporary Password"}))
    role = forms.ChoiceField(choices=UserRole.choices, initial=UserRole.DEPT_HEAD, widget=forms.Select(attrs={"class": "form-select"}))
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=False, empty_label="-- Select Department (Optional for Admin/Registrar) --", widget=forms.Select(attrs={"class": "form-select"}))

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username


class DepartmentForm(forms.ModelForm):
    head = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="-- Select Faculty / Head (Optional) --",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Department
        fields = ["code", "name", "description", "head"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. STAT, CS, MATH"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Department of Statistics & Data Science"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Department overview and mission"}),
        }


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ["department", "code", "name", "degree_level"]
        widgets = {
            "department": forms.Select(attrs={"class": "form-select"}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. BS-STAT, MS-DS"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Bachelor of Science in Statistics"}),
            "degree_level": forms.Select(attrs={"class": "form-select"}),
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["department", "program", "code", "title", "credits", "semester"]
        widgets = {
            "department": forms.Select(attrs={"class": "form-select"}),
            "program": forms.Select(attrs={"class": "form-select"}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. STA308"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Statistical Data Cleaning & Live Dashboards"}),
            "credits": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 12}),
            "semester": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Fall 2026"}),
        }


class StudentProfileEditForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control"}))
    phone = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+1 (555) 000-0000"}))
    new_password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Leave blank to keep current password"}))
