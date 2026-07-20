from django import forms
from .models import Participant, Registration
from django.forms import formset_factory


class RegistrationForm(forms.ModelForm):
    confirm_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label="Conferma Email"
    )

    privacy_tick = forms.BooleanField(
        label="Accossento al trattamento dei dati raccolti solamente a scopo funzionale del sito.",
        required=True,
        widget=forms.CheckboxInput(attrs={'class':'form-check-input'})
    )

    class Meta:
        model = Registration
        fields = ['email', 'phone']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        confirm_email = cleaned_data.get("confirm_email")

        if email and confirm_email and email != confirm_email:
            self.add_error('confirm_email', "Le email non corrispondono")

        return cleaned_data


class ParticipantForm(forms.ModelForm):
    confirm_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label="Conferma Email"
    )

    class Meta:
        model = Participant
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        confirm_email = cleaned_data.get("confirm_email")

        if email and confirm_email and email != confirm_email:
            self.add_error('confirm_email', "Le email non corrispondono")

        return cleaned_data



# Creiamo un formset per gestire più partecipanti
ParticipantFormSet = formset_factory(ParticipantForm, extra=1, max_num=5)
