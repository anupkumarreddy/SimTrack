from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "Create a read-only demo user for local demos."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo")
        parser.add_argument("--email", default="demo@simtrack.local")
        parser.add_argument("--password", default="demo")

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username=options["username"],
            defaults={
                "email": options["email"],
                "full_name": "Demo User",
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        user.email = options["email"]
        user.is_staff = False
        user.is_superuser = False
        user.is_active = True
        user.set_password(options["password"])
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} read-only demo user '{user.username}'."))
