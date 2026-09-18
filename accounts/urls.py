# accounts/urls.py
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import BootstrapLoginForm, BootstrapPasswordChangeForm

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=BootstrapLoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path(
        "password/change/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html",
            success_url=reverse_lazy("password_change_done"),
            form_class=BootstrapPasswordChangeForm,  # Enforces PasswordToggleInput on password change
        ),
        name="password_change",
    ),
    path(
        "password/change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),
]
