# import re
# from django import forms
# from datetime import date
# from .models import Participant

# class ParticipantForm(forms.ModelForm):
#     confirm_email = forms.EmailField(
#         label='Conferma Email', 
#         required=True,
#         error_messages={
#             'required': "Inserisci la conferma dell'email.",
#             'invalid': "Inserisci un indirizzo email valido."
#         }
#     )

#     accetta_statuto = forms.BooleanField(
#         required=True,
#         error_messages={'required': "Devi accettare lo Statuto per poterti tesserare."}
#     )
#     accetta_privacy = forms.BooleanField(
#         required=True,
#         error_messages={'required': "Devi acconsentire alla Privacy Policy per proseguire."}
#     )


#     class Meta:
#         model = Participant
#         fields = [
#             'first_name', 'last_name', 'email', 'phone',
#             'data_di_nascita', 'luogo_di_nascita', 'codice_fiscale',
#             'indirizzo', 'citta', 'provincia', 'cap',
#             'accetta_statuto', 'accetta_privacy'
#         ]

#         oggi_str = date.today().isoformat()
        
#         # DEFINIZIONE MESSAGGI D'ERRORE PERSONALIZZATI
#         error_messages = {
#             'first_name': {'required': "Il nome è obbligatorio."},
#             'last_name': {'required': "Il cognome è obbligatorio."},
#             'email': {
#                 'required': "L'email è obbligatoria.",
#                 'invalid': "Inserisci un indirizzo email valido."
#             },
#             'phone': {'required': "Il numero di telefono è obbligatorio."},
#             'data_di_nascita': {
#                 'required': "La data di nascita è obbligatoria.",
#                 'invalid': "Inserisci una data valida (AAAA-MM-GG)."
#             },
#             'luogo_di_nascita': {'required': "Il luogo di nascita è obbligatorio."},
#             'codice_fiscale': {'required': "Il codice fiscale è obbligatorio."},
#             'indirizzo': {'required': "L'indirizzo di residenza è obbligatorio."},
#             'citta': {'required': "La città è obbligatoria."},
#             'provincia': {'required': "La provincia è obbligatoria."},
#             'cap': {'required': "Il CAP è obbligatorio."},
#         }

#         widgets = {
#             'data_di_nascita': forms.DateInput(attrs={
#                 'type': 'date',
#                 'max': oggi_str,
#                 'min': '1900-01-01'
#             }),
#             'codice_fiscale': forms.TextInput(attrs={'style': 'text-transform: uppercase;'}),
#             'provincia': forms.TextInput(attrs={'style': 'text-transform: uppercase;', 'maxlength': '2'}),
#         }

#     def clean_data_di_nascita(self):
#         data_nascita = self.cleaned_data.get('data_di_nascita')
        
#         if data_nascita:
#             oggi = date.today()
            
#             # 1. Blocco data nel futuro
#             if data_nascita > oggi:
#                 raise forms.ValidationError("La data di nascita non può essere nel futuro.")
            
#             # 2. Blocco anni non realistici (es. 0003 o prima del 1900)
#             if data_nascita.year < 1900:
#                 raise forms.ValidationError("Inserisci un anno di nascita valido (superiore al 1900).")
                
#             # 3. Controllo età minima (es. almeno 16 anni per tesseramento APS autonomo)
#             eta = oggi.year - data_nascita.year - ((oggi.month, oggi.day) < (data_nascita.month, data_nascita.day))
#             if eta < 16:
#                 raise forms.ValidationError("Devi avere almeno 16 anni per poterti tesserare.")

#         return data_nascita

#     def clean_codice_fiscale(self):
#         cf = self.cleaned_data.get('codice_fiscale', '').upper()
#         if len(cf) != 16:
#             raise forms.ValidationError("Il Codice Fiscale deve essere di esattamente 16 caratteri.")
            
#         pattern = r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$'
#         if not re.match(pattern, cf):
#             raise forms.ValidationError("Il formato del Codice Fiscale non è valido. Controlla di averlo scritto corretto.")
            
#         return cf
    
#     def clean_provincia(self):
#         prov = self.cleaned_data.get('provincia', '').upper().strip()
#         if len(prov) != 2:
#             raise forms.ValidationError("Inserisci la sigla di 2 lettere (es. MO, BO).")
#         return prov

#     def clean(self):
#         cleaned_data = super().clean()
#         email = cleaned_data.get('email')
#         confirm_email = cleaned_data.get('confirm_email')

#         if email and confirm_email and email != confirm_email:
#             self.add_error('confirm_email', "Le due email inserite non corrispondono.")
        
#         return cleaned_data

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         for field_name, field in self.fields.items():
#             if not isinstance(field.widget, forms.CheckboxInput):
#                 field.widget.attrs['class'] = 'form-control'
#             else:
#                 field.widget.attrs['class'] = 'form-check-input'

# --------------------------------------------------------


import re
from datetime import date
from django import forms
from .models import EventRegistration


class EventRegistrationForm(forms.Form):
    first_name = forms.CharField(
        label="Nome",
        max_length=100,
        error_messages={'required': "Il nome è obbligatorio."},
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mario'})
    )
    last_name = forms.CharField(
        label="Cognome",
        max_length=100,
        error_messages={'required': "Il cognome è obbligatorio."},
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rossi'})
    )
    email = forms.EmailField(
        label="Email",
        error_messages={
            'required': "L'email è obbligatoria.",
            'invalid': "Inserisci un indirizzo email valido."
        },
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'mario.rossi@email.it'})
    )
    confirm_email = forms.EmailField(
        label="Conferma Email",
        required=False,
        error_messages={'invalid': "Inserisci un indirizzo email valido."},
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Conferma la tua email',
            'required': 'required'
        })
    )
    phone = forms.CharField(
        label="Telefono",
        max_length=20,
        error_messages={'required': "Il numero di telefono è obbligatorio."},
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '333 1234567'})
    )
    codice_fiscale = forms.CharField(
        label="Codice Fiscale",
        max_length=16,
        min_length=16,
        error_messages={'required': "Il codice fiscale è obbligatorio."},
        widget=forms.TextInput(attrs={
            'class': 'form-control text-uppercase',
            'placeholder': 'RSSMRA98E20F257X',
            'maxlength': '16',
            'style': 'text-transform: uppercase;',
        })
    )

    # Campi Libro Soci APS (obbligatori se requires_membership=True, opzionali se solo biglietto)
    data_di_nascita = forms.DateField(
        label="Data di nascita",
        required=True,
        error_messages={
            'required': "La data di nascita è obbligatoria.",
            'invalid': "Inserisci una data valida (AAAA-MM-GG)."
        },
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': '1900-01-01',
        })
    )
    luogo_di_nascita = forms.CharField(
        label="Luogo di nascita",
        max_length=100,
        required=True,
        error_messages={'required': "Il luogo di nascita è obbligatorio."},
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Modena'})
    )
    indirizzo = forms.CharField(
        label="Indirizzo di residenza",
        max_length=200,
        required=True,
        error_messages={'required': "L'indirizzo di residenza è obbligatorio."},
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Via Emilia 10'})
    )
    citta = forms.CharField(
        label="Città",
        max_length=100,
        required=True,
        error_messages={'required': "La città è obbligatoria."},
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Modena'})
    )
    provincia = forms.CharField(
        label="Provincia (Sigla)",
        max_length=2,
        required=True,
        error_messages={'required': "La provincia è obbligatoria."},
        widget=forms.TextInput(attrs={
            'class': 'form-control text-uppercase',
            'placeholder': 'MO',
            'maxlength': '2',
            'style': 'text-transform: uppercase;',
        })
    )
    cap = forms.CharField(
        label="CAP",
        max_length=5,
        required=True,
        error_messages={'required': "Il CAP è obbligatorio."},
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '41121', 'maxlength': '5'})
    )

    accetta_statuto = forms.BooleanField(
        label="Dichiaro di aver letto e accettato lo Statuto dell'Associazione",
        required=True,
        error_messages={'required': "Devi accettare lo Statuto per poterti tesserare."},
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    accetta_privacy = forms.BooleanField(
        label="Acconsento al trattamento dei dati personali (Privacy Policy)",
        required=True,
        error_messages={'required': "Devi acconsentire alla Privacy Policy per proseguire."},
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event
        self.fields['data_di_nascita'].widget.attrs['max'] = date.today().isoformat()

        if self.event and not self.event.requires_membership:
            aps_only_fields = [
                'data_di_nascita',
                'luogo_di_nascita',
                'indirizzo',
                'citta',
                'provincia',
                'cap',
                'accetta_statuto',
            ]
            for field_name in aps_only_fields:
                self.fields[field_name].required = False

    def clean_data_di_nascita(self):
        data_nascita = self.cleaned_data.get('data_di_nascita')
        if data_nascita:
            oggi = date.today()
            if data_nascita > oggi:
                raise forms.ValidationError("La data di nascita non può essere nel futuro.")
            if data_nascita.year < 1900:
                raise forms.ValidationError("Inserisci un anno di nascita valido (superiore al 1900).")
            eta = oggi.year - data_nascita.year - ((oggi.month, oggi.day) < (data_nascita.month, data_nascita.day))
            if eta < 16:
                raise forms.ValidationError("Devi avere almeno 16 anni per poterti tesserare.")
        return data_nascita

    def clean_provincia(self):
        prov = (self.cleaned_data.get('provincia') or '').upper().strip()
        if prov and len(prov) != 2:
            raise forms.ValidationError("Inserisci la sigla di 2 lettere (es. MO, BO).")
        return prov

    def clean_codice_fiscale(self):
        cf = (self.cleaned_data.get('codice_fiscale') or '').strip().upper()
        if not re.match(r'^[A-Z0-9]{16}$', cf):
            raise forms.ValidationError("Il Codice Fiscale deve contenere esattamente 16 caratteri alfanumerici.")

        if self.event:
            already_registered = EventRegistration.objects.filter(
                event=self.event,
                member__codice_fiscale=cf,
                status__in=['approved', 'checked_in']
            ).exists()
            if already_registered:
                raise forms.ValidationError("Questo Codice Fiscale risulta già iscritto e confermato per questo evento.")

        return cf

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        confirm_email = cleaned_data.get('confirm_email')

        if email and confirm_email and email != confirm_email:
            self.add_error('confirm_email', "Le due email inserite non corrispondono.")
        return cleaned_data


# Alias per retrocompatibilità
ParticipantForm = EventRegistrationForm