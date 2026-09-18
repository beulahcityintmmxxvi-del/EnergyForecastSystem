from django import forms
from energy.models import Building


class ForecastForm(forms.Form):
    building = forms.ModelChoiceField(
        queryset=Building.objects.none(),
        required=False,
        empty_label="All Buildings",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    periods = forms.IntegerField(
        label="Forecast Period (Days)",
        min_value=7,
        max_value=365,
        initial=30,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 30'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['building'].queryset = Building.objects.all().order_by('name')


class ForecastEvaluationForm(forms.Form):
    building = forms.ModelChoiceField(
        queryset=Building.objects.none(),
        required=False,
        empty_label="All Buildings",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    test_days = forms.IntegerField(
        label="Test Period (Days)",
        min_value=3,
        max_value=365,
        initial=30,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 30'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['building'].queryset = Building.objects.all().order_by('name')