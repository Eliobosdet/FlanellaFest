from django.db import models
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
class Registration(models.Model):
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Registrazione {self.id} - {self.email}"



class Participant(models.Model):
    STATUS_CHOICES = [
        ('approved', 'Approvato'),
        ('rejected', 'Rifiutato'),
        ('checked_in', 'Partecipante arrivato'),
    ]

    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='participants', null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    # NOTA: il phone è relativo a chi ha fatto la registrazione, non al partecipante stesso.
    phone = models.CharField(max_length=20, blank=True, null=True)
    payment_proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    created_at = models.DateTimeField(auto_now_add=True)
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

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
