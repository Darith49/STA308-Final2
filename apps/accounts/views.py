from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from apps.accounts.forms import UserRegisterForm, UserLoginForm, UserProfileForm
from apps.accounts.models import log_audit_event


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()

            # Profile is auto-created via signal; update profile fields
            profile = user.profile
            profile.role = form.cleaned_data.get("role")
            profile.department = form.cleaned_data.get("department") or "Department of Statistics & Data Science"
            profile.save()

            log_audit_event(
                user,
                "USER_CREATE",
                target_model="User",
                target_id=str(user.id),
                details=f"Self-registration as {profile.role} in {profile.department}",
                request=request,
            )

            login(request, user)
            messages.success(request, f"Welcome to the University Data Portal, {user.username}!")
            return redirect("home")
    else:
        form = UserRegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            log_audit_event(
                user,
                "LOGIN",
                target_model="User",
                target_id=str(user.id),
                details=f"User '{user.username}' successfully authenticated",
                request=request,
            )
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = UserLoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    if request.user.is_authenticated:
        log_audit_event(
            request.user,
            "LOGOUT",
            target_model="User",
            target_id=str(request.user.id),
            details=f"User '{request.user.username}' signed out",
            request=request,
        )
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


@login_required
def change_password_view(request):
    """Allow user to change their own password securely."""
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            log_audit_event(
                user,
                "PASSWORD_RESET",
                target_model="User",
                target_id=str(user.id),
                details=f"User '{user.username}' changed their own password",
                request=request,
            )
            messages.success(request, "Your password was successfully updated!")
            return redirect("accounts:profile")
        else:
            for errs in form.errors.values():
                for err in errs:
                    messages.error(request, err)
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "accounts/change_password.html", {"form": form})
