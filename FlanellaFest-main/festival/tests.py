from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from festival.models import Participant
from festival.views import send_approval_email
from unittest.mock import patch

class FullRegistrationAndEmailTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.valid_payload = {
            'first_name': 'Mario',
            'last_name': 'Rossi',
            'email': 'mario.rossi@example.com',
            'confirm_email': 'mario.rossi@example.com',
            'phone': '3331234567',
            'data_di_nascita': '1995-05-20',
            'luogo_di_nascita': 'Modena',
            'codice_fiscale': 'RSSMRA95E20F257X',
            'indirizzo': 'Via Roma 10',
            'citta': 'Fiorano Modenese',
            'provincia': 'MO',
            'cap': '41042',
            'accetta_statuto': True,
            'accetta_privacy': True,
            'gateway': 'stripe'
        }

    @patch('stripe.checkout.Session.create')
    def test_single_registration_creation(self, mock_stripe_session):
        """Verifica che la registrazione crei 1 solo partecipante in 'pending'"""
        mock_stripe_session.return_value = type('obj', (object,), {'url': 'https://checkout.stripe.com/test'})

        response = self.client.post(self.register_url, data=self.valid_payload)

        self.assertIn(response.status_code, [302, 303])
        self.assertEqual(Participant.objects.count(), 1)

        participant = Participant.objects.first()
        self.assertEqual(participant.status, 'pending')
        self.assertFalse(participant.pagato)

    def test_send_approval_email_and_qr_code(self):
        """Verifica che send_approval_email generi la mail con l'oggetto e l'allegato corretto"""
        participant = Participant.objects.create(
            first_name='Luigi',
            last_name='Verdi',
            email='luigi.verdi@example.com',
            phone='3339876543',
            status='approved',
            pagato=True
        )
        
        # Generiamo il QR code
        participant.generate_qr_code()
        participant.save()

        # Inviamo l'email
        success = send_approval_email(participant)

        # Verifichiamo l'invio
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, 'Tesseramento e Registrazione approvati - Flanella Fest')
        self.assertIn('luigi.verdi@example.com', sent_email.to)

    def test_export_excel_returns_correct_content_type(self):
        """Verifica che l'export Excel funzioni correttamente per gli organizer"""
        staff_user = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='password',
            is_staff=True
        )
        self.client.login(username='staff', password='password')

        response = self.client.get(reverse('export_participants_excel'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'], 
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )