import csv
import io
import json
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Avg
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from alerts.services.alert_service import evaluate_record_alerts
from .forms import (
    BuildingFilterForm,
    BuildingForm,
    EnergyConsumptionForm,
    EnergyImportForm,
    EnergyRecordFilterForm,
)
from .models import Building, EnergyConsumption


@login_required
def building_list(request):
    filter_form = BuildingFilterForm(request.GET or None)

    buildings = Building.objects.annotate(
        records_count=Count('energy_records'),
        total_consumption=Sum('energy_records__consumption_kwh')
    )

    if request.GET and filter_form.is_valid():
        q = filter_form.cleaned_data.get('q')
        ordering = filter_form.cleaned_data.get('ordering') or 'name'

        if q:
            buildings = buildings.filter(
                Q(name__icontains=q) |
                Q(code__icontains=q) |
                Q(description__icontains=q)
            )

        buildings = buildings.order_by(ordering, 'name')
    else:
        buildings = buildings.order_by('name')

    summary = buildings.aggregate(
        total_buildings=Count('id'),
        total_records=Count('energy_records'),
        total_consumption=Sum('energy_records__consumption_kwh'),
        avg_consumption=Avg('energy_records__consumption_kwh'),
    )

    paginator = Paginator(buildings, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()

    return render(request, 'energy/building_list.html', {
        'buildings': page_obj,
        'filter_form': filter_form,
        'total_buildings': summary['total_buildings'] or 0,
        'total_records': summary['total_records'] or 0,
        'total_consumption': summary['total_consumption'] or 0,
        'avg_consumption': summary['avg_consumption'] or 0,
        'query_string': query_string,
    })


@login_required
@role_required(['Admin', 'Energy Officer'])
def building_create(request):
    if request.method == 'POST':
        form = BuildingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Building added successfully.')
            return redirect('building_list')
    else:
        form = BuildingForm()

    return render(request, 'energy/building_form.html', {
        'form': form,
        'title': 'Add Building'
    })


@login_required
@role_required(['Admin', 'Energy Officer'])
def building_update(request, pk):
    building = get_object_or_404(Building, pk=pk)

    if request.method == 'POST':
        form = BuildingForm(request.POST, instance=building)
        if form.is_valid():
            form.save()
            messages.success(request, 'Building updated successfully.')
            return redirect('building_list')
    else:
        form = BuildingForm(instance=building)

    return render(request, 'energy/building_form.html', {
        'form': form,
        'building': building,
        'title': 'Edit Building'
    })


@login_required
@role_required(['Admin'])
def building_delete(request, pk):
    building = get_object_or_404(Building, pk=pk)

    if request.method == 'POST':
        building.delete()
        messages.success(request, 'Building deleted successfully.')
        return redirect('building_list')

    return render(request, 'energy/building_confirm_delete.html', {
        'building': building
    })


@login_required
def building_detail(request, pk):
    building = get_object_or_404(Building, pk=pk)

    records_qs = building.energy_records.select_related('building').order_by('-reading_date', '-id')

    total_records = records_qs.count()
    total_consumption = records_qs.aggregate(total=Sum('consumption_kwh'))['total'] or 0
    avg_consumption = records_qs.aggregate(avg=Avg('consumption_kwh'))['avg'] or 0
    latest_reading = records_qs.first()
    latest_records = records_qs[:10]

    monthly_summary = (
        records_qs
        .annotate(month=TruncMonth('reading_date'))
        .values('month')
        .annotate(total=Sum('consumption_kwh'))
        .order_by('month')
    )

    chart_labels = []
    chart_values = []

    for item in monthly_summary:
        if item['month']:
            chart_labels.append(item['month'].strftime('%b %Y'))
            chart_values.append(float(item['total'] or 0))

    context = {
        'building': building,
        'total_records': total_records,
        'total_consumption': total_consumption,
        'avg_consumption': avg_consumption,
        'latest_reading': latest_reading,
        'latest_records': latest_records,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_values_json': json.dumps(chart_values),
        'has_chart_data': len(chart_labels) > 0,
    }

    return render(request, 'energy/building_detail.html', context)


@login_required
def energy_list(request):
    filter_form = EnergyRecordFilterForm(request.GET or None)

    records = EnergyConsumption.objects.select_related('building').all()

    if request.GET and filter_form.is_valid():
        q = filter_form.cleaned_data.get('q')
        building = filter_form.cleaned_data.get('building')
        start_date = filter_form.cleaned_data.get('start_date')
        end_date = filter_form.cleaned_data.get('end_date')
        min_consumption = filter_form.cleaned_data.get('min_consumption')
        max_consumption = filter_form.cleaned_data.get('max_consumption')
        ordering = filter_form.cleaned_data.get('ordering') or '-reading_date'

        if q:
            records = records.filter(
                Q(building__name__icontains=q) |
                Q(building__code__icontains=q) |
                Q(meter_id__icontains=q) |
                Q(remarks__icontains=q)
            )

        if building:
            records = records.filter(building=building)

        if start_date:
            records = records.filter(reading_date__gte=start_date)

        if end_date:
            records = records.filter(reading_date__lte=end_date)

        if min_consumption is not None:
            records = records.filter(consumption_kwh__gte=min_consumption)

        if max_consumption is not None:
            records = records.filter(consumption_kwh__lte=max_consumption)

        records = records.order_by(ordering, '-id')

    elif request.GET and not filter_form.is_valid():
        messages.error(request, 'Please correct the filter errors and try again.')

    summary = records.aggregate(
        total_records=Count('id'),
        total_consumption=Sum('consumption_kwh'),
        avg_consumption=Avg('consumption_kwh'),
    )

    paginator = Paginator(records, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()

    return render(request, 'energy/energy_list.html', {
        'records': page_obj,
        'filter_form': filter_form,
        'total_records': summary['total_records'] or 0,
        'total_consumption': summary['total_consumption'] or 0,
        'avg_consumption': summary['avg_consumption'] or 0,
        'query_string': query_string,
    })


@login_required
@role_required(['Admin', 'Energy Officer'])
def energy_create(request):
    if request.method == 'POST':
        form = EnergyConsumptionForm(request.POST)
        if form.is_valid():
            record = form.save()
            evaluate_record_alerts(record)
            messages.success(request, 'Energy record added successfully.')
            return redirect('energy_list')
    else:
        form = EnergyConsumptionForm()

    return render(request, 'energy/energy_form.html', {
        'form': form,
        'title': 'Add Energy Record'
    })


@login_required
@role_required(['Admin', 'Energy Officer'])
def energy_update(request, pk):
    record = get_object_or_404(EnergyConsumption, pk=pk)

    if request.method == 'POST':
        form = EnergyConsumptionForm(request.POST, instance=record)
        if form.is_valid():
            record = form.save()
            evaluate_record_alerts(record)
            messages.success(request, 'Energy record updated successfully.')
            return redirect('energy_list')
    else:
        form = EnergyConsumptionForm(instance=record)

    return render(request, 'energy/energy_form.html', {
        'form': form,
        'record': record,
        'title': 'Edit Energy Record'
    })


@login_required
@role_required(['Admin'])
def energy_delete(request, pk):
    record = get_object_or_404(EnergyConsumption, pk=pk)

    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Energy record deleted successfully.')
        return redirect('energy_list')

    return render(request, 'energy/energy_confirm_delete.html', {
        'record': record
    })


@login_required
@role_required(['Admin', 'Energy Officer'])
def energy_import(request):
    summary = None
    errors = []

    if request.method == 'POST':
        form = EnergyImportForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = request.FILES['csv_file']

            if not uploaded_file.name.lower().endswith('.csv'):
                messages.error(request, 'Please upload a valid CSV file.')
            else:
                try:
                    decoded_file = uploaded_file.read().decode('utf-8-sig')
                    reader = csv.DictReader(io.StringIO(decoded_file))

                    required_fields = {'building_name', 'reading_date', 'consumption_kwh'}
                    file_fields = {field.strip().lower() for field in (reader.fieldnames or [])}

                    missing = required_fields - file_fields
                    if missing:
                        messages.error(
                            request,
                            f'Missing required columns: {", ".join(sorted(missing))}'
                        )
                    else:
                        created_count = 0
                        skipped_count = 0
                        row_count = 0

                        for row in reader:
                            row_count += 1

                            normalized = {
                                (k or '').strip().lower(): (v.strip() if v is not None else '')
                                for k, v in row.items()
                            }

                            try:
                                building_name = normalized.get('building_name') or normalized.get('building') or ''
                                building_code = normalized.get('building_code') or ''

                                if not building_name:
                                    errors.append(f'Row {row_count}: building_name is required.')
                                    skipped_count += 1
                                    continue

                                building, created = Building.objects.get_or_create(
                                    name=building_name,
                                    defaults={'code': building_code}
                                )

                                if not created and building_code and not building.code:
                                    building.code = building_code
                                    building.save(update_fields=['code'])

                                reading_date_str = normalized.get('reading_date')
                                try:
                                    reading_date = datetime.strptime(reading_date_str, '%Y-%m-%d').date()
                                except (ValueError, TypeError):
                                    errors.append(
                                        f'Row {row_count}: invalid reading_date "{reading_date_str}". Use YYYY-MM-DD.'
                                    )
                                    skipped_count += 1
                                    continue

                                meter_id = normalized.get('meter_id') or ''

                                consumption_raw = normalized.get('consumption_kwh')
                                try:
                                    consumption_kwh = Decimal(consumption_raw)
                                except (InvalidOperation, TypeError):
                                    errors.append(f'Row {row_count}: invalid consumption_kwh "{consumption_raw}".')
                                    skipped_count += 1
                                    continue

                                cost_raw = normalized.get('cost')
                                peak_raw = normalized.get('peak_demand_kw')
                                cost = None
                                peak_demand_kw = None

                                if cost_raw:
                                    try:
                                        cost = Decimal(cost_raw)
                                    except (InvalidOperation, TypeError):
                                        errors.append(f'Row {row_count}: invalid cost "{cost_raw}".')
                                        skipped_count += 1
                                        continue

                                if peak_raw:
                                    try:
                                        peak_demand_kw = Decimal(peak_raw)
                                    except (InvalidOperation, TypeError):
                                        errors.append(f'Row {row_count}: invalid peak_demand_kw "{peak_raw}".')
                                        skipped_count += 1
                                        continue

                                remarks = normalized.get('remarks') or ''

                                duplicate_exists = EnergyConsumption.objects.filter(
                                    building=building,
                                    reading_date=reading_date,
                                    meter_id=meter_id
                                ).exists()

                                if duplicate_exists:
                                    skipped_count += 1
                                    continue

                                record = EnergyConsumption.objects.create(
                                    building=building,
                                    reading_date=reading_date,
                                    meter_id=meter_id,
                                    consumption_kwh=consumption_kwh,
                                    cost=cost,
                                    peak_demand_kw=peak_demand_kw,
                                    remarks=remarks
                                )
                                evaluate_record_alerts(record)
                                created_count += 1

                            except Exception as exc:
                                errors.append(f'Row {row_count}: {exc}')
                                skipped_count += 1

                        summary = {
                            'rows': row_count,
                            'created': created_count,
                            'skipped': skipped_count,
                        }

                        messages.success(
                            request,
                            f'Import completed. {created_count} records added, {skipped_count} skipped.'
                        )
                except Exception as exc:
                    messages.error(request, f'Unable to process the CSV file: {exc}')
        else:
            messages.error(request, 'Please choose a CSV file before uploading.')
    else:
        form = EnergyImportForm()

    return render(request, 'energy/energy_import.html', {
        'form': form,
        'summary': summary,
        'errors': errors[:10],
    })