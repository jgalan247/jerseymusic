"""Diagnostic views for troubleshooting OAuth configuration."""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse


@login_required
def check_sumup_env(request):
    """Check if SumUp environment variables are configured.

    IMPORTANT: Only use this for debugging. Remove or restrict access in production.
    """
    # Only allow superusers to access this diagnostic
    if not request.user.is_superuser:
        return JsonResponse(
            {"error": "Access denied. Only superusers can access diagnostics."},
            status=403
        )

    config_check = {
        "SUMUP_CLIENT_ID": {
            "set": bool(settings.SUMUP_CLIENT_ID),
            "preview": settings.SUMUP_CLIENT_ID[:20] + "..." if settings.SUMUP_CLIENT_ID else None
        },
        "SUMUP_CLIENT_SECRET": {
            "set": bool(settings.SUMUP_CLIENT_SECRET),
            "length": len(settings.SUMUP_CLIENT_SECRET) if settings.SUMUP_CLIENT_SECRET else 0
        },
        "SUMUP_REDIRECT_URI": {
            "set": bool(settings.SUMUP_REDIRECT_URI),
            "value": settings.SUMUP_REDIRECT_URI
        },
        "SUMUP_MERCHANT_CODE": {
            "set": bool(settings.SUMUP_MERCHANT_CODE),
            "value": settings.SUMUP_MERCHANT_CODE if settings.SUMUP_MERCHANT_CODE else None
        },
        "SUMUP_API_URL": {
            "value": settings.SUMUP_API_URL
        },
        "SUMUP_BASE_URL": {
            "value": settings.SUMUP_BASE_URL
        }
    }

    # Check if critical values are missing
    critical_missing = []
    if not settings.SUMUP_CLIENT_ID:
        critical_missing.append("SUMUP_CLIENT_ID")
    if not settings.SUMUP_CLIENT_SECRET:
        critical_missing.append("SUMUP_CLIENT_SECRET")
    if not settings.SUMUP_REDIRECT_URI:
        critical_missing.append("SUMUP_REDIRECT_URI")

    return JsonResponse({
        "status": "ok" if not critical_missing else "error",
        "critical_missing": critical_missing,
        "configuration": config_check,
        "oauth_flow_url": f"{settings.SUMUP_BASE_URL}/authorize?response_type=code&client_id={settings.SUMUP_CLIENT_ID or 'NOT_SET'}&redirect_uri={settings.SUMUP_REDIRECT_URI or 'NOT_SET'}&scope=payments%20checkouts&state=test"
    }, json_dumps_params={'indent': 2})
