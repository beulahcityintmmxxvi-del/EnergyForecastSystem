# accounts/signals.py
from django.contrib.auth.models import Group, User
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import NotificationPreference, UserProfile


@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    if sender.name != "accounts":
        return

    for group_name in ("Admin", "Energy Officer", "Viewer"):
        Group.objects.get_or_create(name=group_name)


@receiver(post_save, sender=User)
def create_user_related_records(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        NotificationPreference.objects.get_or_create(user=instance)

        if not instance.is_superuser:
            viewer_group, _ = Group.objects.get_or_create(name="Viewer")
            instance.groups.add(viewer_group)
