from rest_framework import authentication, exceptions

from .models import ApiToken


class BearerTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        authorization = authentication.get_authorization_header(request).decode("utf-8")
        if not authorization:
            return None

        parts = authorization.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            raise exceptions.AuthenticationFailed("Invalid bearer token header.")

        raw_token = parts[1]
        token_hash = ApiToken.hash_token(raw_token)
        try:
            token = ApiToken.objects.select_related("user").get(token_hash=token_hash)
        except ApiToken.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("Invalid bearer token.") from exc

        if not token.is_active or not token.user.is_active:
            raise exceptions.AuthenticationFailed("Inactive bearer token.")

        token.mark_used()
        return token.user, token

    def authenticate_header(self, request):
        return self.keyword
