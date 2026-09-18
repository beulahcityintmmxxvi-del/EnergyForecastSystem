# accounts/utils.py
"""
Centralised role-check helpers.
Every other module (context processors, decorators, views) should
import from here so the logic lives in exactly one place.
"""

MANAGE_ROLES = frozenset({"Admin", "Energy Officer"})
ADMIN_ROLES = frozenset({"Admin"})


def is_admin_or_officer(user) -> bool:
    """Return True for superusers and members of Admin / Energy Officer."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=MANAGE_ROLES).exists()


def is_admin(user) -> bool:
    """Return True for superusers and members of Admin."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=ADMIN_ROLES).exists()
