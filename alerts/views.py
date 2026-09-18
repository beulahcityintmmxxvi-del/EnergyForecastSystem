from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import role_required
from energy.models import EnergyConsumption

from .forms import AlertFilterForm, BuildingThresholdForm, ThresholdDefaultsForm
from .models import BuildingThreshold, EnergyAlert, ThresholdDefaults
from .services.alert_service import evaluate_record_alerts


@login_required
def alerts_dashboard(request):
    open_alerts_qs = EnergyAlert.objects.filter(status='open').select_related('building').order_by('-created_at')

    total_open = open_alerts_qs.count()
    critical_open = open_alerts_qs.filter(severity='critical').count()
    warning_open = open_alerts_qs.filter(severity='warning').count()
    thresholds_count = BuildingThreshold.objects.count()

    resolved_this_month = EnergyAlert.objects.filter(
        status='resolved',
        resolved_at__year=timezone.now().year,
        resolved_at__month=timezone.now().month
    ).count()

    recent_alerts = open_alerts_qs[:10]

    context = {
        'total_open': total_open,
        'critical_open': critical_open,
        'warning_open': warning_open,
        'thresholds_count': thresholds_count,
        'resolved_this_month': resolved_this_month,
        'recent_alerts': recent_alerts,
    }

    return render(request, 'alerts/dashboard.html', context)


@login_required
def alert_list(request):
    filter_form = AlertFilterForm(request.GET or None)
    alerts = EnergyAlert.objects.select_related('building', 'energy_record').all()

    if request.GET and filter_form.is_valid():
        q = filter_form.cleaned_data.get('q')
        building = filter_form.cleaned_data.get('building')
        status = filter_form.cleaned_data.get('status')
        severity = filter_form.cleaned_data.get('severity')
        ordering = filter_form.cleaned_data.get('ordering') or '-created_at'

        if q:
            alerts = alerts.filter(
                Q(title__icontains=q) |
                Q(message__icontains=q) |
                Q(building__name__icontains=q) |
                Q(building__code__icontains=q)
            )

        if building:
            alerts = alerts.filter(building=building)

        if status:
            alerts = alerts.filter(status=status)

        if severity:
            alerts = alerts.filter(severity=severity)

        alerts = alerts.order_by(ordering, '-id')
    else:
        alerts = alerts.order_by('-created_at', '-id')

    total_matching = alerts.count()
    open_matching = alerts.filter(status='open').count()
    critical_matching = alerts.filter(severity='critical').count()

    paginator = Paginator(alerts, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()

    context = {
        'alerts': page_obj,
        'filter_form': filter_form,
        'total_matching': total_matching,
        'open_matching': open_matching,
        'critical_matching': critical_matching,
        'query_string': query_string,
    }

    return render(request, 'alerts/list.html', context)


@login_required
@role_required(['Admin', 'Energy Officer'])
def scan_alerts(request):
    """
    Scan existing records and generate alerts. Useful for backfilling.
    """
    if request.method != 'POST':
        return redirect('alerts_dashboard')

    records = EnergyConsumption.objects.select_related('building').order_by('reading_date', 'id')

    created_total = 0
    for record in records:
        created_total += len(evaluate_record_alerts(record))

    messages.success(
        request,
        f'Alert scan completed. {created_total} new alert(s) created.'
    )
    return redirect('alerts_dashboard')


@login_required
@role_required(['Admin', 'Energy Officer'])
def resolve_alert(request, pk):
    alert = get_object_or_404(EnergyAlert, pk=pk)

    if request.method == 'POST' and alert.status == 'open':
        alert.status = 'resolved'
        alert.resolved_at = timezone.now()
        alert.save(update_fields=['status', 'resolved_at'])
        messages.success(request, 'Alert resolved successfully.')
    else:
        messages.info(request, 'Alert was already resolved or request is invalid.')

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)

    return redirect('alert_list')


@login_required
def threshold_list(request):
    thresholds = BuildingThreshold.objects.select_related('building').order_by('building__name')
    return render(request, 'alerts/threshold_list.html', {'thresholds': thresholds})


@login_required
@role_required(['Admin'])
def threshold_create(request):
    if request.method == 'POST':
        form = BuildingThresholdForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            BuildingThreshold.objects.update_or_create(
                building=data['building'],
                defaults={
                    'monthly_threshold_kwh': data['monthly_threshold_kwh'],
                    'spike_threshold_percent': data['spike_threshold_percent'],
                    'active': data['active'],
                    'notes': data['notes'],
                }
            )

            messages.success(request, 'Threshold saved successfully.')
            return redirect('threshold_list')
    else:
        form = BuildingThresholdForm()

    return render(request, 'alerts/threshold_form.html', {
        'form': form,
        'title': 'Add Threshold'
    })


@login_required
@role_required(['Admin'])
def threshold_update(request, pk):
    threshold = get_object_or_404(BuildingThreshold, pk=pk)

    if request.method == 'POST':
        form = BuildingThresholdForm(request.POST, instance=threshold)
        if form.is_valid():
            form.save()
            messages.success(request, 'Threshold updated successfully.')
            return redirect('threshold_list')
    else:
        form = BuildingThresholdForm(instance=threshold)

    return render(request, 'alerts/threshold_form.html', {
        'form': form,
        'threshold': threshold,
        'title': 'Edit Threshold'
    })
@login_required
@role_required(['Admin'])
def threshold_defaults(request):
    defaults = ThresholdDefaults.load()

    if request.method == 'POST':
        form = ThresholdDefaultsForm(request.POST, instance=defaults)
        if form.is_valid():
            form.save()
            messages.success(request, 'Threshold defaults updated successfully.')
            return redirect('threshold_defaults')
    else:
        form = ThresholdDefaultsForm(instance=defaults)

    return render(request, 'alerts/threshold_defaults.html', {
        'form': form,
        'defaults': defaults,
    })