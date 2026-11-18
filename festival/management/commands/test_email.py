from django.core.management.base import BaseCommand
from festival.models import EventRegistration
from festival.views import send_approval_email


class Command(BaseCommand):
    help = "Invia un'email di prova usando l'ultima registrazione presente nel database"

    def handle(self, *args, **kwargs):
        registration = EventRegistration.objects.select_related('member', 'event').last()
        if not registration:
            self.stdout.write(self.style.WARNING("Nessuna registrazione trovata nel database per il test."))
            return

        self.stdout.write(f"Invio email di test a {registration.email}...")
        success = send_approval_email(registration)
        if success:
            self.stdout.write(self.style.SUCCESS("Email inviata con successo!"))
        else:
            self.stdout.write(self.style.ERROR("Errore durante l'invio dell'email."))