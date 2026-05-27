from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.conf import settings


def login_required_all(get_response):
    """Middleware que requiere login en todas las vistas excepto login."""
    def middleware(request):
        exempt_urls = [settings.LOGIN_URL]
        if not request.user.is_authenticated and request.path not in exempt_urls:
            from django.shortcuts import redirect
            return redirect(f'{settings.LOGIN_URL}?next={request.path}')
        return get_response(request)
    return middleware