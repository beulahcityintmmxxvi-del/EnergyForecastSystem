# accounts/context_processors.py
from .utils import is_admin, is_admin_or_officer


def role_flags(request):
    """Inject ``can_manage`` and ``can_admin`` booleans into every template."""
    return {
        "can_manage": is_admin_or_officer(request.user),
        "can_admin": is_admin(request.user),
    }
