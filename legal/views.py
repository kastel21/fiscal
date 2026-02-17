"""Public legal pages. No authentication required."""

from django.shortcuts import render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def eula_view(request):
    """
    Public End-User License Agreement page.
    URL: /legal/eula/
    No authentication required. Production-ready for QuickBooks Developer portal and enterprise audit.
    """
    context = {
        "last_updated": "February 2026",
    }
    return render(request, "legal/eula.html", context)


@require_http_methods(["GET"])
def privacy_view(request):
    """
    Public Privacy Policy page.
    URL: /legal/privacy/
    No authentication required. Production-ready for QuickBooks Developer Portal and SaaS compliance.
    """
    context = {
        "last_updated": "February 2026",
    }
    return render(request, "legal/privacy.html", context)
