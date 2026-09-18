# alerts/management/commands/run_alert_checks.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from energy.models import EnergyConsumption
from alerts.services import AlertEngine


class Command(BaseCommand):
    help = "Scan recent energy records and generate alerts for spikes or threshold breaches."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help="Number of past days of consumption to evaluate (default: 1)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        cutoff = timezone.now().date() - timezone.timedelta(days=days)
        records = EnergyConsumption.objects.filter(date__gte=cutoff)

        self.stdout.write(f"Evaluating {records.count()} records since {cutoff}...")
        total_created = 0

        for record in records:
            alerts = AlertEngine.evaluate_consumption_record(record)
            total_created += len(alerts)

        self.stdout.write(
            self.style.SUCCESS(f"Done. Generated {total_created} new alert(s).")
        )
