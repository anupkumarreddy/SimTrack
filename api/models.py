import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel


class ApiToken(TimeStampedModel):
    READ_SCOPE = "read"
    WRITE_SCOPE = "write"
    INGEST_SCOPE = "ingest"
    VALID_SCOPES = {READ_SCOPE, WRITE_SCOPE, INGEST_SCOPE}

    name = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user})"

    @classmethod
    def generate_raw_token(cls):
        return f"st_{secrets.token_urlsafe(32)}"

    @classmethod
    def hash_token(cls, raw_token):
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    def create_token(cls, *, user, name, scopes):
        normalized_scopes = cls.normalize_scopes(scopes)
        raw_token = cls.generate_raw_token()
        token = cls.objects.create(
            user=user,
            name=name,
            scopes=normalized_scopes,
            token_hash=cls.hash_token(raw_token),
        )
        return token, raw_token

    @classmethod
    def normalize_scopes(cls, scopes):
        if isinstance(scopes, str):
            scopes = [scope.strip() for scope in scopes.split(",") if scope.strip()]
        normalized = sorted(set(scopes or []))
        invalid_scopes = sorted(set(normalized) - cls.VALID_SCOPES)
        if invalid_scopes:
            raise ValueError(f"Invalid API token scope(s): {', '.join(invalid_scopes)}")
        return normalized

    def has_scope(self, scope):
        return scope in (self.scopes or [])

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at", "updated_at"])
