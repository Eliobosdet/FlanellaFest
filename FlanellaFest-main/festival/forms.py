import re
from django import forms
from datetime import date
from .models import Participant

class ParticipantForm(forms.ModelForm):
    confirm_email = forms.EmailField(
        label='Conferma Email', 
        required=True,
        error_messages={
            'required': "Inserisci la conferma dell'email.",
            'invalid': "Inserisci un indirizzo email valido."
        }
    )

    accetta_statuto = forms.BooleanField(
        required=True,
        error_messages={'required': "Devi accettare lo Statuto per poterti tesserare."}
    )
    accetta_privacy = forms.BooleanField(
        required=True,
        error_messages={'required': "Devi acconsentire alla Privacy Policy per proseguire."}
    )


    class Meta:
        model = Participant
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'data_di_nascita', 'luogo_di_nascita', 'codice_fiscale',
            'indirizzo', 'citta', 'provincia', 'cap',
            'accetta_statuto', 'accetta_privacy'
        ]

        oggi_str = date.today().isoformat()
        
        # DEFINIZIONE MESSAGGI D'ERRORE PERSONALIZZATI
        error_messages = {
            'first_name': {'required': "Il nome è obbligatorio."},
            'last_name': {'required': "Il cognome è obbligatorio."},
            'email': {
                'required': "L'email è obbligatoria.",
                'invalid': "Inserisci un indirizzo email valido."
            },
            'phone': {'required': "Il numero di telefono è obbligatorio."},
            'data_di_nascita': {
                'required': "La data di nascita è obbligatoria.",
                'invalid': "Inserisci una data valida (AAAA-MM-GG)."
            },
            'luogo_di_nascita': {'required': "Il luogo di nascita è obbligatorio."},
            'codice_fiscale': {'required': "Il codice fiscale è obbligatorio."},
            'indirizzo': {'required': "L'indirizzo di residenza è obbligatorio."},
            'citta': {'required': "La città è obbligatoria."},
            'provincia': {'required': "La provincia è obbligatoria."},
            'cap': {'required': "Il CAP è obbligatorio."},
        }

        widgets = {
            'data_di_nascita': forms.DateInput(attrs={
                'type': 'date',
                'max': oggi_str,
                'min': '1900-01-01'
            }),
            'codice_fiscale': forms.TextInput(attrs={'style': 'text-transform: uppercase;'}),
            'provincia': forms.TextInput(attrs={'style': 'text-transform: uppercase;', 'maxlength': '2'}),
        }

    def clean_data_di_nascita(self):
        data_nascita = self.cleaned_data.get('data_di_nascita')
        
        if data_nascita:
            oggi = date.today()
            
            # 1. Blocco data nel futuro
            if data_nascita > oggi:
                raise forms.ValidationError("La data di nascita non può essere nel futuro.")
            
            # 2. Blocco anni non realistici (es. 0003 o prima del 1900)
            if data_nascita.year < 1900:
                raise forms.ValidationError("Inserisci un anno di nascita valido (superiore al 1900).")
                
            # 3. Controllo età minima (es. almeno 16 anni per tesseramento APS autonomo)
            eta = oggi.year - data_nascita.year - ((oggi.month, oggi.day) < (data_nascita.month, data_nascita.day))
            if eta < 16:
                raise forms.ValidationError("Devi avere almeno 16 anni per poterti tesserare.")

        return data_nascita

    def clean_codice_fiscale(self):
        cf = self.cleaned_data.get('codice_fiscale', '').upper()
        if len(cf) != 16:
            raise forms.ValidationError("Il Codice Fiscale deve essere di esattamente 16 caratteri.")
            
        pattern = r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$'
        if not re.match(pattern, cf):
            raise forms.ValidationError("Il formato del Codice Fiscale non è valido. Controlla di averlo scritto corretto.")
            
        return cf
    
    def clean_provincia(self):
        prov = self.cleaned_data.get('provincia', '').upper().strip()
        if len(prov) != 2:
            raise forms.ValidationError("Inserisci la sigla di 2 lettere (es. MO, BO).")
        return prov

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        confirm_email = cleaned_data.get('confirm_email')

        if email and confirm_email and email != confirm_email:
            self.add_error('confirm_email', "Le due email inserite non corrispondono.")
        
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'
            else:
                field.widget.attrs['class'] = 'form-check-input'