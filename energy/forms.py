from django import forms
from .models import Building, EnergyConsumption


class BuildingForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Main Library'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. BLD-01'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Optional description'
            }),
        }


class EnergyConsumptionForm(forms.ModelForm):
    class Meta:
        model = EnergyConsumption
        fields = [
            'building',
            'reading_date',
            'meter_id',
            'consumption_kwh',
            'cost',
            'peak_demand_kw',
            'remarks'
        ]
        widgets = {
            'building': forms.Select(attrs={'class': 'form-select'}),
            'reading_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'meter_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. MTR-001'
            }),
            'consumption_kwh': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2450.50'
            }),
            'cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 98000.00'
            }),
            'peak_demand_kw': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 120.75'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Optional notes'
            }),
        }


class EnergyRecordFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search building, meter ID, or remarks...'
        })
    )

    building = forms.ModelChoiceField(
        queryset=Building.objects.none(),
        required=False,
        empty_label="All Buildings",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    start_date = forms.DateField(
        required=False,
        label="Start Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    end_date = forms.DateField(
        required=False,
        label="End Date",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    min_consumption = forms.DecimalField(
        required=False,
        label="Min Consumption",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min kWh'
        })
    )

    max_consumption = forms.DecimalField(
        required=False,
        label="Max Consumption",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max kWh'
        })
    )

    ordering = forms.ChoiceField(
        required=False,
        label="Sort By",
        choices=[
            ('-reading_date', 'Newest Date'),
            ('reading_date', 'Oldest Date'),
            ('-consumption_kwh', 'Highest Consumption'),
            ('consumption_kwh', 'Lowest Consumption'),
        ],
        initial='-reading_date',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['building'].queryset = Building.objects.all().order_by('name')


class BuildingFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search building name, code, or description...'
        })
    )

    ordering = forms.ChoiceField(
        required=False,
        label="Sort By",
        choices=[
            ('name', 'Name A-Z'),
            ('-name', 'Name Z-A'),
            ('-records_count', 'Most Records'),
            ('records_count', 'Least Records'),
            ('-total_consumption', 'Highest Consumption'),
            ('total_consumption', 'Lowest Consumption'),
        ],
        initial='name',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class EnergyImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        })
    )