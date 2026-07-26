from django.core.management.base import BaseCommand
from django.conf import settings
from festival.models import Participant
from festival.views import send_approval_email

class Command(BaseCommand):
    help = 'Invia una mail reale di test con QR Code in memoria (Solo se DEBUG=True)'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email del destinatario di test')

    def handle(self, *args, **options):
        # 1. Blocco di sicurezza per la Produzione
        if not settings.DEBUG:
            self.stdout.write(
                self.style.ERROR("ERRORE: Questo comando è disabilitato in ambiente di produzione (DEBUG=False).")
            )
            return

        target_email = options['email']
        self.stdout.write(f"Inizializzazione partecipante temporaneo per: {target_email}...")

        # 2. Istanziazione IN MEMORIA (Nessuna query al DB, nessun .save() o get_or_create)
        participant = Participant(
            first_name='Test',
            last_name='Utente',
            email=target_email,
            phone='3330000000',
            citta='Modena',
            status='approved',
            pagato=True
        )

        # Generiamo il QR Code (necessario per l'allegato)
        participant.generate_qr_code()

        self.stdout.write("Invio email in corso tramite SMTP...")
        success = send_approval_email(participant)

        if success:
            self.stdout.write(
                self.style.SUCCESS(f"Email inviata con successo a {target_email}! Nessun dato è stato salvato nel DB.")
            )
        else:
            self.stdout.write(
                self.style.ERROR("Invio fallito. Controlla le credenziali SMTP in settings.py.")
            )