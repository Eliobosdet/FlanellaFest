from django.db import models
import uuid
import qrcode
from io import BytesIO
from django.core.files import File

class Participant(models.Model):
    STATUS_CHOICES = [
        ('pending', 'In attesa di pagamento'), # Aggiunto lo stato pending
        ('approved', 'Approvato'),
        ('rejected', 'Rifiutato'),
        ('checked_in', 'Partecipante arrivato'),
    ]

    PAYMENT_CHOICES = [
        ('stripe', 'Carta di Credito'),
        ('contanti', 'Contanti'),
    ]

    # --- Anagrafica Base ---
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # --- Campi Obbligatori APS (Libro Soci) ---
    data_di_nascita = models.DateField(null=True, blank=False)
    luogo_di_nascita = models.CharField(max_length=100, null=True, blank=False)
    codice_fiscale = models.CharField(max_length=16, null=True, blank=False)
    indirizzo = models.CharField(max_length=200, null=True, blank=False)
    citta = models.CharField(max_length=100, null=True, blank=False)
    provincia = models.CharField(max_length=2, null=True, blank=False) # Es. 'MO', 'BO'
    cap = models.CharField(max_length=5, null=True, blank=False)
    
    accetta_statuto = models.BooleanField(default=False)
    accetta_privacy = models.BooleanField(default=False)
    
    # --- Gestione Pagamenti e Stato ---
    metodo_pagamento = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='stripe')
    pagato = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending') # Default in attesa
    created_at = models.DateTimeField(auto_now_add=True)
    
    # --- Dati di Sistema e Biglietteria ---
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def save(self, *args, **kwargs):
        # Normalizza Nome e Cognome in Title Case
        if self.first_name:
            self.first_name = self.first_name.strip().title()
        if self.last_name:
            self.last_name = self.last_name.strip().title()
            
        # Normalizza Luogo di Nascita e Città in Title Case
        if self.luogo_di_nascita:
            self.luogo_di_nascita = self.luogo_di_nascita.strip().title()
        if self.citta:
            self.citta = self.citta.strip().title()

        # Assicura che la provincia sia sempre in maiuscolo (es. 'mo' -> 'MO')
        if self.provincia:
            self.provincia = self.provincia.strip().upper()

        super().save(*args, **kwargs)

    def __str__(self):
        if self.status in ['approved', 'checked_in']:
            stato = "PAGATO"
        elif self.status == 'rejected':
            stato = "ANNULLATO"
        else:
            stato = "DA PAGARE"
            
        return f"{self.first_name} {self.last_name} - CF: {self.codice_fiscale} [{stato}]"

    def get_qr_code_bytes(self):
        """Genera il PNG del QR Code al volo in memoria e ne restituisce i byte."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(str(self.unique_id))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    def generate_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(str(self.unique_id))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer)
        filename = f'qr_{self.unique_id}.png'
        self.qr_code.save(filename, File(buffer), save=False)


class FestivalConfig(models.Model):
    ticket_price_centesimi = models.PositiveIntegerField(default=1050) # Default 10.50€ (1050 centesimi)

    class Meta:
        verbose_name = "Configurazione Festival"
        verbose_name_plural = "Configurazioni Festival"

    def __str__(self):
        return f"Prezzo Corrente: {self.ticket_price_centesimi / 100} €"


# ... (Lascia intatti Participant e FestivalConfig sopra) ...


class Member(models.Model):
    """
    1. ANAGRAFICA UNICA SOCIO / UTENTE
    Contiene i dati della persona fisica e il codice QR permanente.
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    # Campi Libro Soci APS
    data_di_nascita = models.DateField(null=True, blank=True)
    luogo_di_nascita = models.CharField(max_length=100, null=True, blank=True)
    codice_fiscale = models.CharField(max_length=16, unique=True, db_index=True)
    indirizzo = models.CharField(max_length=200, null=True, blank=True)
    citta = models.CharField(max_length=100, null=True, blank=True)
    provincia = models.CharField(max_length=2, null=True, blank=True)
    cap = models.CharField(max_length=5, null=True, blank=True)

    accetta_statuto = models.BooleanField(default=False)
    accetta_privacy = models.BooleanField(default=False)

    # Identificativo univoco per il QR Code (conserva quello del 2026!)
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.first_name:
            self.first_name = self.first_name.strip().title()
        if self.last_name:
            self.last_name = self.last_name.strip().title()
        if self.luogo_di_nascita:
            self.luogo_di_nascita = self.luogo_di_nascita.strip().title()
        if self.citta:
            self.citta = self.citta.strip().title()
        if self.provincia:
            self.provincia = self.provincia.strip().upper()
        if self.codice_fiscale:
            self.codice_fiscale = self.codice_fiscale.strip().upper()
        super().save(*args, **kwargs)

    def has_valid_membership(self, year: int) -> bool:
        return self.memberships.filter(year=year, is_active=True).exists()

    def get_qr_code_bytes(self):
        """Genera il PNG del QR Code al volo in memoria usando unique_id."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(str(self.unique_id))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.codice_fiscale})"


class Membership(models.Model):
    """
    2. STORICO TESSERAMENTO ANNUALE APS (Libro Soci per anno)
    """
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='memberships')
    year = models.PositiveIntegerField(db_index=True)  # Es. 2026, 2027
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('member', 'year')
        verbose_name = "Tessera Socio Annuale"
        verbose_name_plural = "Tessere Soci Annuali"

    def __str__(self):
        stato = "ATTIVA" if self.is_active else "NON ATTIVA"
        return f"Tessera {self.year} - {self.member} [{stato}]"


class Event(models.Model):
    """
    3. CONFIGURATORE EVENTO (Permette solo tessera, solo biglietto o entrambi)
    """
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    year = models.PositiveIntegerField(default=2027)
    date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    # Regole di accesso flessibili (in centesimi come nel tuo FestivalConfig per Stripe)
    requires_membership = models.BooleanField(default=True)
    membership_price_centesimi = models.PositiveIntegerField(default=1050)

    requires_ticket = models.BooleanField(default=False)
    ticket_price_centesimi = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventi"

    def __str__(self):
        return f"{self.title} ({self.year})"


class EventRegistration(models.Model):
    """
    4. PARTECIPAZIONE / INGRESSO AL SINGOLO EVENTO
    """
    STATUS_CHOICES = [
        ('pending', 'In attesa di pagamento'),
        ('approved', 'Approvato'),
        ('rejected', 'Rifiutato'),
        ('checked_in', 'Partecipante arrivato'),
    ]

    PAYMENT_CHOICES = [
        ('stripe', 'Carta di Credito'),
        ('contanti', 'Contanti'),
        ('free_member', 'Gratuito (Già Socio)'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='registrations')
    
    metodo_pagamento = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='stripe')
    pagato = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    include_membership = models.BooleanField(default=False)
    include_ticket = models.BooleanField(default=False)
    total_paid_centesimi = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'member')
        verbose_name = "Iscrizione Evento"
        verbose_name_plural = "Iscrizioni Eventi"

    def __str__(self):
        return f"{self.member} @ {self.event.title} [{self.status}]"