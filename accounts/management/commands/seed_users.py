# accounts/management/commands/seed_users.py
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand


SEED_USERS = [
    {
        "username": "admin",
        "email": "admin@energysystem.com",
        "password": "Admin@Energy2024!",
        "is_superuser": True,
        "is_staff": True,
        "groups": ["Admin"],
    },
    {
        "username": "userEvrons123",
        "email": "staff256@energysystem.com",
        "password": "enerygy@emilly123",
        "is_superuser": False,
        "is_staff": True,
        "groups": ["Admin", "Energy Officer"],
    },
    {
        "username": "officerSarah",
        "email": "officer@energysystem.com",
        "password": "Officer@Sarah2024!",
        "is_superuser": False,
        "is_staff": True,
        "groups": ["Energy Officer"],
    },
    {
        "username": "viewerJohn",
        "email": "viewer@energysystem.com",
        "password": "Viewer@John2024!",
        "is_superuser": False,
        "is_staff": False,
        "groups": ["Viewer"],
    },
]


class Command(BaseCommand):
    help = "Seed the database with default users (admin, officers, viewer)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing seed users before re-creating them.",
        )

    def handle(self, *args, **options):
        reset = options["reset"]

        for data in SEED_USERS:
            username = data["username"]

            if reset:
                User.objects.filter(username=username).delete()

            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f"  ⏭  User '{username}' already exists — skipped.")
                )
                continue

            user = User.objects.create_user(
                username=username,
                email=data["email"],
                password=data["password"],
                is_superuser=data["is_superuser"],
                is_staff=data["is_staff"],
            )

            for group_name in data["groups"]:
                group, _ = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)

            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✔  Created '{username}' "
                    f"({', '.join(data['groups'])})"
                )
            )

        self.stdout.write(self.style.SUCCESS("\nSeeding complete."))