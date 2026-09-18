# alerts/context_processors.py
from django.core.cache import cache

from .models import EnergyAlert

CACHE_KEY = "alert_stats"
CACHE_TTL = 60  # seconds — adjust to taste


def alert_stats(request):
    """Inject open-alert counts into every template context."""
    if not request.user.is_authenticated:
        return {
            "open_alert_count": 0,
            "critical_alert_count": 0,
            "warning_alert_count": 0,
            "recent_open_alerts": [],
        }

    stats = cache.get(CACHE_KEY)
    if stats is None:
        open_qs = EnergyAlert.objects.filter(status="open").select_related("building")
        stats = {
            "open_alert_count": open_qs.count(),
            "critical_alert_count": open_qs.filter(severity="critical").count(),
            "warning_alert_count": open_qs.filter(severity="warning").count(),
            "recent_open_alerts": list(open_qs.order_by("-created_at")[:5]),
        }
        cache.set(CACHE_KEY, stats, CACHE_TTL)

    return stats
