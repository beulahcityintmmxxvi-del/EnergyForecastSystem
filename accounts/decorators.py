# accounts/decorators.py
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def role_required(allowed_roles=None):
    """
    View decorator that restricts access to users who belong to at
    least one of *allowed_roles* (or are superusers).

    Usage::

        @role_required(['Admin', 'Energy Officer'])
        def my_view(request):
            ...
    """
    allowed_roles = set(allowed_roles or [])

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            if allowed_roles and user.groups.filter(name__in=allowed_roles).exists():
                return view_func(request, *args, **kwargs)

            messages.error(request, "You do not have permission to access that page.")
            return redirect("home")

        return _wrapped

    return decorator
