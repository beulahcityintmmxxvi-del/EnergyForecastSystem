from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils.dateparse import parse_date

from energy.models import Building, EnergyConsumption


def _serialize_building(building):
    return {
        "id": building.id,
        "name": building.name,
        "code": building.code,
        "description": building.description,
        "records_count": int(getattr(building, "records_count", 0) or 0),
        "total_consumption": round(float(getattr(building, "total_consumption", 0) or 0), 2),
    }


def _serialize_record(record):
    return {
        "id": record.id,
        "building": {
            "id": record.building.id,
            "name": record.building.name,
            "code": record.building.code,
        },
        "reading_date": record.reading_date.isoformat(),
        "meter_id": record.meter_id,
        "consumption_kwh": round(float(record.consumption_kwh or 0), 2),
        "cost": round(float(record.cost), 2) if record.cost is not None else None,
        "peak_demand_kw": round(float(record.peak_demand_kw), 2) if record.peak_demand_kw is not None else None,
        "remarks": record.remarks,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


@login_required
@require_GET
def api_summary(request):
    total_buildings = Building.objects.count()
    total_records = EnergyConsumption.objects.count()

    total_consumption = EnergyConsumption.objects.aggregate(
        total=Sum("consumption_kwh")
    )["total"] or 0

    avg_consumption = EnergyConsumption.objects.aggregate(
        avg=Avg("consumption_kwh")
    )["avg"] or 0

    latest_record = (
        EnergyConsumption.objects
        .select_related("building")
        .order_by("-reading_date", "-id")
        .first()
    )

    return JsonResponse({
        "success": True,
        "data": {
            "total_buildings": total_buildings,
            "total_records": total_records,
            "total_consumption": round(float(total_consumption), 2),
            "avg_consumption": round(float(avg_consumption), 2),
            "latest_record": _serialize_record(latest_record) if latest_record else None,
        }
    })


@login_required
@require_GET
def api_buildings(request):
    buildings = (
        Building.objects
        .annotate(
            records_count=Count("energy_records"),
            total_consumption=Sum("energy_records__consumption_kwh")
        )
        .order_by("name")
    )

    return JsonResponse({
        "success": True,
        "count": buildings.count(),
        "data": [_serialize_building(b) for b in buildings]
    })


@login_required
@require_GET
def api_records(request):
    records = EnergyConsumption.objects.select_related("building").order_by("-reading_date", "-id")

    building_id = request.GET.get("building_id")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if building_id:
        try:
            building_id_int = int(building_id)
            records = records.filter(building_id=building_id_int)
        except ValueError:
            return JsonResponse({
                "success": False,
                "message": "Invalid building_id. It must be a number."
            }, status=400)

    if start_date:
        parsed_start = parse_date(start_date)
        if not parsed_start:
            return JsonResponse({
                "success": False,
                "message": "Invalid start_date. Use YYYY-MM-DD."
            }, status=400)
        records = records.filter(reading_date__gte=parsed_start)

    if end_date:
        parsed_end = parse_date(end_date)
        if not parsed_end:
            return JsonResponse({
                "success": False,
                "message": "Invalid end_date. Use YYYY-MM-DD."
            }, status=400)
        records = records.filter(reading_date__lte=parsed_end)

    try:
        limit = int(request.GET.get("limit", 100))
        limit = max(1, min(limit, 1000))
    except ValueError:
        return JsonResponse({
            "success": False,
            "message": "Invalid limit. It must be a number."
        }, status=400)

    records = records[:limit]

    return JsonResponse({
        "success": True,
        "count": records.count(),
        "filters": {
            "building_id": building_id,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
        },
        "data": [_serialize_record(r) for r in records]
    })