# accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User

from .models import NotificationPreference, UserProfile
from .widgets import PasswordToggleInput


class BootstrapLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Username",
                "autofocus": True,
            }
        )
    )
    password = forms.CharField(
        widget=PasswordToggleInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Password",
            }
        )
    )


class BootstrapUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Email address",
            }
        ),
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=PasswordToggleInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Create a password",
            }
        ),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=PasswordToggleInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Confirm password",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "placeholder": "Choose a username",
                }
            ),
        }


class BootstrapPasswordChangeForm(PasswordChangeForm):
    """Overrides default fields to map our custom toggle widget into Password Change."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ["old_password", "new_password1", "new_password2"]:
            if field_name in self.fields:
                self.fields[field_name].widget = PasswordToggleInput(
                    attrs={
                        "class": "form-control",
                        "placeholder": self.fields[field_name].label,
                    }
                )


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["full_name", "department", "job_title", "phone", "bio"]
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Full name"}
            ),
            "department": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Department"}
            ),
            "job_title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Job title"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Phone number"}
            ),
            "bio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Short bio",
                }
            ),
        }


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = [
            "email_alerts",
            "in_app_alerts",
            "critical_only",
            "daily_summary",
            "weekly_summary",
            "preferred_email",
        ]
        widgets = {
            "email_alerts": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "in_app_alerts": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "critical_only": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "daily_summary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "weekly_summary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "preferred_email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional email override",
                }
            ),
        }
