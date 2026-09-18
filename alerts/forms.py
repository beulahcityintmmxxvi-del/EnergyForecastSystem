# alerts/forms.py
from django import forms

from energy.models import Building

from .models import BuildingThreshold, ThresholdDefaults


class BuildingThresholdForm(forms.ModelForm):
    class Meta:
        model = BuildingThreshold
        fields = [
            "building",
            "monthly_threshold_kwh",
            "spike_threshold_percent",
            "active",
            "notes",
        ]
        widgets = {
            "building": forms.Select(attrs={"class": "form-select"}),
            "monthly_threshold_kwh": forms.NumberInput(attrs={"class": "form-control"}),
            "spike_threshold_percent": forms.NumberInput(attrs={"class": "form-control"}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["building"].queryset = Building.objects.order_by("name")


class AlertFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search title, message, or building...",
            }
        ),
    )
    building = forms.ModelChoiceField(
        queryset=Building.objects.none(),
        required=False,
        empty_label="All Buildings",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All Statuses"), ("open", "Open"), ("resolved", "Resolved")],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    severity = forms.ChoiceField(
        required=False,
        choices=[
            ("", "All Severities"),
            ("info", "Info"),
            ("warning", "Warning"),
            ("critical", "Critical"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    ordering = forms.ChoiceField(
        required=False,
        choices=[
            ("-created_at", "Newest First"),
            ("created_at", "Oldest First"),
            ("-alert_date", "Latest Alert Date"),
            ("alert_date", "Earliest Alert Date"),
        ],
        initial="-created_at",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["building"].queryset = Building.objects.order_by("name")


class ThresholdDefaultsForm(forms.ModelForm):
    class Meta:
        model = ThresholdDefaults
        fields = ["monthly_threshold_kwh", "spike_threshold_percent", "active"]
        widgets = {
            "monthly_threshold_kwh": forms.NumberInput(attrs={"class": "form-control"}),
            "spike_threshold_percent": forms.NumberInput(attrs={"class": "form-control"}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
