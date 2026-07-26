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
        ('stripe', 'Stripe / Carta di Credito'),
        ('paypal', 'PayPal'),
        ('contanti', 'Contanti (Pagamento in loco)'),
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
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)

    def __str__(self):
        stato = "PAGATO" if self.pagato else "DA PAGARE"
        return f"{self.first_name} {self.last_name} - CF: {self.codice_fiscale} [{stato}]"

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