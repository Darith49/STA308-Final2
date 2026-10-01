from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.accounts.forms import UserRegisterForm, UserLoginForm, UserProfileForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("uploads:list")

    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()

            # Profile is auto-created via signal; update profile fields
            profile = user.profile
            profile.role = form.cleaned_data.get("role")
            profile.department = form.cleaned_data.get("department") or "Department of Statistics"
            profile.save()

            login(request, user)
            messages.success(request, f"Welcome to the University Data Portal, {user.username}!")
            return redirect("uploads:list")
    else:
        form = UserRegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("uploads:list")

    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get("next") or "uploads:list"
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = UserLoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("accounts:login")


@login_required
def profile_view(request):
    user = request.user
    profile = user.profile

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            user.first_name = form.cleaned_data.get("first_name", "")
            user.last_name = form.cleaned_data.get("last_name", "")
            user.email = form.cleaned_data.get("email", "")
            user.save()
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile")
    else:
        initial_data = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        }
        form = UserProfileForm(instance=profile, initial=initial_data)

    return render(request, "accounts/profile.html", {"form": form, "user": user})
