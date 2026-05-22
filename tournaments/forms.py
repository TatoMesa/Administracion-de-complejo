from django import forms
from .models import Tournament, Team, Player, Match


class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'sport', 'format', 'gender', 'category', 'status',
                  'min_players', 'max_players', 'start_date', 'resource', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'sport': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'format': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'gender': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'category': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'min_players': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'max_players': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'start_date': forms.DateInput(attrs={'class': 'input input-bordered w-full', 'type': 'date'}),
            'resource': forms.Select(attrs={'class': 'select select-bordered w-full'}),
            'notes': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_date'].required = False
        self.fields['resource'].required = False
        self.fields['notes'].required = False


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'contact_name', 'contact_phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'contact_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'contact_phone': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
        }


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['name', 'dni', 'injury_replacement']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'dni': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'injury_replacement': forms.CheckboxInput(attrs={'class': 'checkbox'}),
        }


class MatchResultForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['home_score', 'away_score', 'status']
        widgets = {
            'home_score': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'away_score': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'status': forms.Select(attrs={'class': 'select select-bordered w-full'}),
        }