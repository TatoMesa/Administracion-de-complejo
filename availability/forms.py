from django import forms
from .models import AvailabilityRule, AvailabilityException


class AvailabilityRuleForm(forms.ModelForm):
    class Meta:
        model = AvailabilityRule
        fields = ['day_of_week', 'open_time', 'close_time']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'open_time': forms.TimeInput(attrs={'class': 'input input-bordered w-full', 'type': 'time'}),
            'close_time': forms.TimeInput(attrs={'class': 'input input-bordered w-full', 'type': 'time'}),
        }


class AvailabilityExceptionForm(forms.ModelForm):
    class Meta:
        model = AvailabilityException
        fields = ['date', 'is_closed', 'open_time', 'close_time', 'reason']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'is_closed': forms.CheckboxInput(attrs={'class': 'checkbox'}),
            'open_time': forms.TimeInput(attrs={'class': 'input input-bordered w-full', 'type': 'time'}),
            'close_time': forms.TimeInput(attrs={'class': 'input input-bordered w-full', 'type': 'time'}),
            'reason': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
        }