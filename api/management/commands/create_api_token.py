from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from api.models import ApiToken


class Command(BaseCommand):
    help = "Create a bearer token for SimTrack API access."

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="Username or email address for the token owner.")
        parser.add_argument("--name", required=True, help="Human-readable token name.")
        parser.add_argument(
            "--scopes",
            default=ApiToken.READ_SCOPE,
            help="Comma-separated scopes. Valid scopes: read, write, ingest.",
        )

    def handle(self, *args, **options):
        user_identifier = options["user"]
        user = (
            User.objects.filter(username=user_identifier).first() or User.objects.filter(email=user_identifier).first()
        )
        if not user:
            raise CommandError(f"User '{user_identifier}' was not found.")

        try:
            token, raw_token = ApiToken.create_token(user=user, name=options["name"], scopes=options["scopes"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"Created API token '{token.name}' for '{user.username}'."))
        self.stdout.write("Copy this token now. It will not be shown again:")
        self.stdout.write(raw_token)
