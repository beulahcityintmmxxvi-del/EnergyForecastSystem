import csv
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import render

from accounts.decorators import role_required
from energy.models import Building, EnergyConsumption

# Optional PDF support
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def _pdf_not_available():
    return HttpResponse(
        "PDF export is unavailable because 'reportlab' is not installed. "
        "Please install it using: pip install reportlab",
        content_type='text/plain',
        status=501
    )


@login_required
@role_required(['Admin', 'Energy Officer'])
def reports_dashboard(request):
    total_buildings = Building.objects.count()
    total_records = EnergyConsumption.objects.count()

    total_consumption = EnergyConsumption.objects.aggregate(
        total=Sum('consumption_kwh')
    )['total'] or 0

    avg_consumption = EnergyConsumption.objects.aggregate(
        avg=Avg('consumption_kwh')
    )['avg'] or 0

    monthly_summary_qs = (
        EnergyConsumption.objects
        .annotate(month=TruncMonth('reading_date'))
        .values('month')
        .annotate(
            total_consumption=Sum('consumption_kwh'),
            records_count=Count('id')
        )
        .order_by('month')
    )

    monthly_summary = []
    chart_labels = []
    chart_values = []

    for item in monthly_summary_qs:
        month_label = item['month'].strftime('%b %Y') if item['month'] else 'N/A'
        total_val = round(float(item['total_consumption'] or 0), 2)

        monthly_summary.append({
            'month': month_label,
            'total_consumption': total_val,
            'records_count': item['records_count']
        })

        chart_labels.append(month_label)
        chart_values.append(total_val)

    top_buildings_qs = (
        Building.objects
        .annotate(
            total_consumption=Sum('energy_records__consumption_kwh'),
            records_count=Count('energy_records')
        )
        .order_by('-total_consumption')[:5]
    )

    top_buildings = [
        {
            'name': building.name,
            'total_consumption': round(float(building.total_consumption or 0), 2),
            'records_count': building.records_count
        }
        for building in top_buildings_qs
    ]

    latest_records = (
        EnergyConsumption.objects
        .select_related('building')
        .order_by('-reading_date', '-id')[:10]
    )

    context = {
        'total_buildings': total_buildings,
        'total_records': total_records,
        'total_consumption': total_consumption,
        'avg_consumption': avg_consumption,
        'monthly_summary': monthly_summary,
        'top_buildings': top_buildings,
        'latest_records': latest_records,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_values_json': json.dumps(chart_values),
        'has_chart_data': len(chart_labels) > 0,
        'pdf_available': REPORTLAB_AVAILABLE,
    }

    return render(request, 'reports/reports_dashboard.html', context)


@login_required
@role_required(['Admin', 'Energy Officer'])
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="energy_consumption_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Building', 'Reading Date', 'Meter ID', 'Consumption (kWh)',
        'Cost', 'Peak Demand (kW)', 'Remarks'
    ])

    records = EnergyConsumption.objects.select_related('building').order_by('-reading_date', '-id')

    for record in records:
        writer.writerow([
            record.building.name,
            record.reading_date,
            record.meter_id or '',
            record.consumption_kwh,
            record.cost or '',
            record.peak_demand_kw or '',
            record.remarks or '',
        ])

    return response


@login_required
@role_required(['Admin', 'Energy Officer'])
def export_pdf(request):
    if not REPORTLAB_AVAILABLE:
        return _pdf_not_available()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="energy_consumption_report.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=18,
        leftMargin=18,
        topMargin=20,
        bottomMargin=18
    )

    styles = getSampleStyleSheet()
    elements = []

    total_buildings = Building.objects.count()
    total_records = EnergyConsumption.objects.count()
    total_consumption = EnergyConsumption.objects.aggregate(total=Sum('consumption_kwh'))['total'] or 0
    avg_consumption = EnergyConsumption.objects.aggregate(avg=Avg('consumption_kwh'))['avg'] or 0

    elements.append(Paragraph("Energy Consumption Report", styles['Title']))
    elements.append(Spacer(1, 12))

    summary_data = [
        ['Metric', 'Value'],
        ['Total Buildings', str(total_buildings)],
        ['Total Records', str(total_records)],
        ['Total Consumption (kWh)', f"{float(total_consumption):,.2f}"],
        ['Average Consumption (kWh)', f"{float(avg_consumption):,.2f}"],
    ]

    summary_table = Table(summary_data, colWidths=[220, 180])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#14532d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#eef6ef')]),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 14))

    monthly_summary_qs = (
        EnergyConsumption.objects
        .annotate(month=TruncMonth('reading_date'))
        .values('month')
        .annotate(
            total_consumption=Sum('consumption_kwh'),
            records_count=Count('id')
        )
        .order_by('month')
    )

    monthly_rows = [['Month', 'Records', 'Total Consumption (kWh)']]
    for item in monthly_summary_qs:
        month_label = item['month'].strftime('%b %Y') if item['month'] else 'N/A'
        monthly_rows.append([
            month_label,
            str(item['records_count']),
            f"{float(item['total_consumption'] or 0):,.2f}"
        ])

    if len(monthly_rows) > 1:
        elements.append(Paragraph("Monthly Summary", styles['Heading2']))
        elements.append(Spacer(1, 6))

        monthly_table = Table(monthly_rows, colWidths=[180, 100, 180], repeatRows=1)
        monthly_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f8ff')]),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(monthly_table)
        elements.append(Spacer(1, 14))

    latest_records = (
        EnergyConsumption.objects
        .select_related('building')
        .order_by('-reading_date', '-id')[:25]
    )

    if latest_records:
        elements.append(Paragraph("Latest Energy Records", styles['Heading2']))
        elements.append(Spacer(1, 6))

        record_rows = [[
            'Building', 'Date', 'Meter ID', 'Consumption',
            'Cost', 'Peak Demand'
        ]]

        for record in latest_records:
            record_rows.append([
                record.building.name,
                record.reading_date.strftime('%Y-%m-%d'),
                record.meter_id or '-',
                f"{float(record.consumption_kwh):,.2f}",
                f"{float(record.cost):,.2f}" if record.cost else '-',
                f"{float(record.peak_demand_kw):,.2f}" if record.peak_demand_kw else '-',
            ])

        record_table = Table(record_rows, repeatRows=1)
        record_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f766e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#eefaf5')]),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(record_table)

    doc.build(elements)
    return response


@login_required
@role_required(['Admin', 'Energy Officer'])
def export_reports_dashboard_pdf(request):
    if not REPORTLAB_AVAILABLE:
        return _pdf_not_available()

    total_buildings = Building.objects.count()
    total_records = EnergyConsumption.objects.count()

    total_consumption = EnergyConsumption.objects.aggregate(
        total=Sum('consumption_kwh')
    )['total'] or 0

    avg_consumption = EnergyConsumption.objects.aggregate(
        avg=Avg('consumption_kwh')
    )['avg'] or 0

    monthly_summary_qs = (
        EnergyConsumption.objects
        .annotate(month=TruncMonth('reading_date'))
        .values('month')
        .annotate(
            total_consumption=Sum('consumption_kwh'),
            records_count=Count('id')
        )
        .order_by('month')
    )

    top_buildings_qs = (
        Building.objects
        .annotate(
            total_consumption=Sum('energy_records__consumption_kwh'),
            records_count=Count('energy_records')
        )
        .order_by('-total_consumption')[:5]
    )

    latest_records = (
        EnergyConsumption.objects
        .select_related('building')
        .order_by('-reading_date', '-id')[:10]
    )

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reports_dashboard.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=18,
        leftMargin=18,
        topMargin=20,
        bottomMargin=18
    )

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Energy Reports Dashboard", styles['Title']))
    elements.append(Spacer(1, 12))

    summary_data = [
        ['Metric', 'Value'],
        ['Total Buildings', str(total_buildings)],
        ['Total Records', str(total_records)],
        ['Total Consumption (kWh)', f"{float(total_consumption):,.2f}"],
        ['Average Consumption (kWh)', f"{float(avg_consumption):,.2f}"],
    ]

    summary_table = Table(summary_data, colWidths=[220, 180])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#14532d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#eef6ef')]),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 14))

    monthly_rows = [['Month', 'Records', 'Total Consumption (kWh)']]
    for item in monthly_summary_qs:
        month_label = item['month'].strftime('%b %Y') if item['month'] else 'N/A'
        monthly_rows.append([
            month_label,
            str(item['records_count']),
            f"{float(item['total_consumption'] or 0):,.2f}"
        ])

    if len(monthly_rows) > 1:
        elements.append(Paragraph("Monthly Summary", styles['Heading2']))
        elements.append(Spacer(1, 6))

        monthly_table = Table(monthly_rows, colWidths=[180, 100, 180], repeatRows=1)
        monthly_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f8ff')]),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(monthly_table)
        elements.append(Spacer(1, 14))

    top_rows = [['Rank', 'Building', 'Records', 'Total Consumption (kWh)']]
    for idx, building in enumerate(top_buildings_qs, start=1):
        top_rows.append([
            str(idx),
            building.name,
            str(building.records_count),
            f"{float(building.total_consumption or 0):,.2f}"
        ])

    if len(top_rows) > 1:
        elements.append(Paragraph("Top Buildings", styles['Heading2']))
        elements.append(Spacer(1, 6))

        top_table = Table(top_rows, colWidths=[50, 220, 90, 160], repeatRows=1)
        top_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f766e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#eefaf5')]),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(top_table)
        elements.append(Spacer(1, 14))

    if latest_records:
        elements.append(Paragraph("Latest Records", styles['Heading2']))
        elements.append(Spacer(1, 6))

        latest_rows = [['Building', 'Date', 'Meter ID', 'Consumption', 'Cost']]
        for record in latest_records:
            latest_rows.append([
                record.building.name,
                record.reading_date.strftime('%Y-%m-%d'),
                record.meter_id or '-',
                f"{float(record.consumption_kwh):,.2f}",
                f"{float(record.cost):,.2f}" if record.cost else '-',
            ])

        latest_table = Table(latest_rows, repeatRows=1)
        latest_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#14532d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#eef6ef')]),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(latest_table)

    doc.build(elements)
    return response