from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    """Require authentication for application pages outside public auth/static paths."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not self._is_public_path(request.path):
            login_url = reverse("login")
            return redirect(f"{login_url}?next={request.get_full_path()}")
        return self.get_response(request)

    def _is_public_path(self, path):
        public_prefixes = [
            settings.STATIC_URL,
            reverse("login"),
            reverse("logout"),
            reverse("signup"),
            reverse("password_reset"),
            reverse("password_reset_done"),
            "/accounts/reset/",
            "/admin/",
        ]
        return any(path.startswith(prefix) for prefix in public_prefixes)
