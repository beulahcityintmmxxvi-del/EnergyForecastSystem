# accounts/views.py
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import (
    BootstrapUserCreationForm,
    NotificationPreferenceForm,
    UserProfileForm,
)
from .models import NotificationPreference, UserProfile


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = BootstrapUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Account created successfully. You can now log in."
            )
            return redirect("login")
    else:
        form = BootstrapUserCreationForm()

    return render(request, "registration/register.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    # Signals create these on User creation; get_or_create is a safe fallback.
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)

    profile_form = UserProfileForm(instance=profile)
    prefs_form = NotificationPreferenceForm(instance=prefs)

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "profile":
            profile_form = UserProfileForm(request.POST, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("profile")

        elif form_type == "preferences":
            prefs_form = NotificationPreferenceForm(request.POST, instance=prefs)
            if prefs_form.is_valid():
                prefs_form.save()
                messages.success(
                    request, "Notification preferences updated successfully."
                )
                return redirect("profile")

    return render(
        request,
        "accounts/profile.html",
        {
            "profile_form": profile_form,
            "prefs_form": prefs_form,
        },
    )
