# forecasting/views.py
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from energy.models import Building
from .forms import ForecastForm
from .models import ForecastRun
from .services import EnergyForecastingService


@login_required
@role_required(["Admin", "Energy Officer"])
def forecast_dashboard(request):
    runs = ForecastRun.objects.select_related("building").order_by("-generated_at")
    form = ForecastForm()

    latest = runs.first()
    chart_html = None
    if latest and latest.results.exists():
        chart_html = EnergyForecastingService.build_plot_html(latest)

    return render(request, "forecasting/dashboard.html", {
        "runs": runs[:15],
        "form": form,
        "total_runs": runs.count(),
        "latest": latest,
        "chart_html": chart_html,
    })


@login_required
@role_required(["Admin", "Energy Officer"])
def run_forecast_view(request):
    if request.method == "POST":
        form = ForecastForm(request.POST)
        if form.is_valid():
            building = form.cleaned_data["building"]
            periods = form.cleaned_data["periods"]

            if not building:
                messages.error(request, "Please select a building.")
                return redirect("forecast_dashboard")

            try:
                run = EnergyForecastingService.run_forecast(
                    building=building,
                    periods=periods,
                    user_label=request.user.username,
                )
                messages.success(
                    request,
                    f"Forecast generated for {building.name} "
                    f"(MAPE: {run.mape:.1f}%, Accuracy: {run.accuracy:.1f}%).",
                )
                return redirect("forecast_detail", pk=run.pk)
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Forecasting failed: {e}")
        else:
            messages.error(request, "Please correct the form errors.")
    return redirect("forecast_dashboard")


@login_required
@role_required(["Admin", "Energy Officer"])
def forecast_detail_view(request, pk):
    run = get_object_or_404(
        ForecastRun.objects.select_related("building").prefetch_related("results"),
        pk=pk,
    )
    chart_html = None
    if run.results.exists():
        chart_html = EnergyForecastingService.build_plot_html(run)

    return render(request, "forecasting/forecast_detail.html", {
        "run": run,
        "values": run.results.all().order_by("forecast_date"),
        "chart_html": chart_html,
    })


@login_required
def building_forecast_view(request, building_id=None, pk=None):
    """View or trigger energy forecasts for a specific building."""
    b_id = building_id or pk
    building = get_object_or_404(Building, pk=b_id)

    if request.method == "POST":
        periods = int(request.POST.get("periods", 30))
        try:
            run = EnergyForecastingService.run_forecast(
                building=building,
                periods=periods,
                user_label=request.user.username,
            )
            messages.success(
                request,
                f"Forecast generated for {building.name} "
                f"(MAPE: {run.mape:.1f}%, Accuracy: {run.accuracy:.1f}%).",
            )
            return redirect("forecast_detail", pk=run.pk)
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Forecasting failed: {e}")
        return redirect("building_forecast", building_id=building.pk)

    runs = ForecastRun.objects.filter(building=building).order_by("-generated_at")
    latest_run = runs.first()
    chart_html = None
    if latest_run and latest_run.results.exists():
        chart_html = EnergyForecastingService.build_plot_html(latest_run)

    return render(request, "forecasting/building_forecast.html", {
        "building": building,
        "latest_run": latest_run,
        "runs": runs[:10],
        "chart_html": chart_html,
    })


@login_required
@role_required(["Admin", "Energy Officer"])
def export_forecast_csv(request, pk):
    run = get_object_or_404(ForecastRun, pk=pk)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="forecast_{run.building.name}_'
        f'{run.generated_at.strftime("%Y%m%d")}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(["Date", "Predicted kWh", "Lower Bound", "Upper Bound"])
    for v in run.results.all().order_by("forecast_date"):
        writer.writerow([v.forecast_date, v.predicted_consumption, v.lower_bound, v.upper_bound])
    return response
