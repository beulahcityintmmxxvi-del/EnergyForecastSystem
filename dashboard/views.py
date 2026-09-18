import json

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth
from django.shortcuts import render

from energy.models import Building, EnergyConsumption


@login_required
def home(request):
    total_buildings = Building.objects.count()
    total_records = EnergyConsumption.objects.count()

    total_consumption = EnergyConsumption.objects.aggregate(
        total=Sum('consumption_kwh')
    )['total'] or 0

    latest_records = (
        EnergyConsumption.objects
        .select_related('building')
        .order_by('-reading_date', '-id')[:5]
    )

    monthly_data = (
        EnergyConsumption.objects
        .annotate(month=TruncMonth('reading_date'))
        .values('month')
        .annotate(total=Sum('consumption_kwh'))
        .order_by('month')
    )

    chart_labels = []
    chart_values = []

    for item in monthly_data:
        if item['month']:
            chart_labels.append(item['month'].strftime('%b %Y'))
            chart_values.append(float(item['total'] or 0))

    context = {
        'total_buildings': total_buildings,
        'total_records': total_records,
        'total_consumption': total_consumption,
        'latest_records': latest_records,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_values_json': json.dumps(chart_values),
        'has_chart_data': len(chart_labels) > 0,
    }

    return render(request, 'dashboard/home.html', context)

@login_required
def comparison_dashboard(request):
    try:
        limit = int(request.GET.get('limit', 5))
    except (TypeError, ValueError):
        limit = 5

    limit = max(3, min(limit, 10))

    buildings_qs = (
        Building.objects
        .annotate(
            total_consumption=Sum('energy_records__consumption_kwh'),
            records_count=Count('energy_records'),
            avg_consumption=Avg('energy_records__consumption_kwh'),
        )
        .filter(records_count__gt=0)
        .order_by('-total_consumption', 'name')[:limit]
    )

    chart_labels = []
    chart_values = []
    comparison_rows = []

    institution_total = EnergyConsumption.objects.aggregate(
        total=Sum('consumption_kwh')
    )['total'] or 0

    institution_records = EnergyConsumption.objects.count()
    compare_total = 0.0

    for index, building in enumerate(buildings_qs, start=1):
        total = float(building.total_consumption or 0)
        avg = float(building.avg_consumption or 0)
        compare_total += total

        chart_labels.append(building.name)
        chart_values.append(round(total, 2))

        share = (total / float(institution_total) * 100) if float(institution_total) > 0 else 0

        comparison_rows.append({
            'rank': index,
            'name': building.name,
            'code': building.code,
            'records_count': building.records_count,
            'total_consumption': round(total, 2),
            'avg_consumption': round(avg, 2),
            'share': round(share, 2),
        })

    highest_building = comparison_rows[0]['name'] if comparison_rows else None
    highest_value = comparison_rows[0]['total_consumption'] if comparison_rows else 0
    remaining_total = max(float(institution_total) - compare_total, 0)

    context = {
        'selected_limit': limit,
        'comparison_rows': comparison_rows,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_values_json': json.dumps(chart_values),
        'has_chart_data': len(chart_labels) > 0,
        'institution_total': institution_total,
        'institution_records': institution_records,
        'compare_total': compare_total,
        'remaining_total': remaining_total,
        'highest_building': highest_building,
        'highest_value': highest_value,
    }

    return render(request, 'dashboard/comparison.html', context)