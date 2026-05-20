from django import forms
from .models import Resource, Sport


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['name', 'sport', 'capacity', 'price_per_hour', 'description', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'sport': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'capacity': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'price_per_hour': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sport'].queryset = Sport.objects.filter(is_active=True)
        self.fields['description'].required = False
        self.fields['image'].required = False


class SportForm(forms.ModelForm):
    class Meta:
        model = Sport
        fields = ['name', 'icon', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'icon': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'color': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'type': 'color'}),
        }