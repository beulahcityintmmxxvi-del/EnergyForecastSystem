# accounts/templatetags/role_tags.py
from django import template

register = template.Library()


@register.filter
def has_group(user, group_name):
    """Usage in templates: {% if request.user|has_group:"Admin" %}"""
    return user.is_authenticated and user.groups.filter(name=group_name).exists()
