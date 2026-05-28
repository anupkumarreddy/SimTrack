from rest_framework.permissions import BasePermission

from .models import ApiToken


class HasTokenScope(BasePermission):
    required_scope = None

    def has_permission(self, request, view):
        token = request.auth
        return isinstance(token, ApiToken) and token.has_scope(self.required_scope)


class HasReadScope(HasTokenScope):
    required_scope = ApiToken.READ_SCOPE


class HasWriteScope(HasTokenScope):
    required_scope = ApiToken.WRITE_SCOPE


class HasIngestScope(HasTokenScope):
    required_scope = ApiToken.INGEST_SCOPE
