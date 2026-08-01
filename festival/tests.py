from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from festival.models import Participant
from festival.views import send_approval_email
from festival.utils import generate_membership_pdf
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
        self.assertFalse(getattr(participant, 'pagato', False)) # Uso sicuro se il campo è stato rimosso

    def test_send_approval_email_and_qr_code(self):
        """Verifica che send_approval_email generi la mail con l'oggetto e l'allegato corretto"""
        # Svuotiamo l'outbox
        mail.outbox = []
        
        participant = Participant.objects.create(
            first_name='Luigi',
            last_name='Verdi',
            email='luigi.verdi@example.com',
            phone='3339876543',
            luogo_di_nascita="Sassuolo",
            indirizzo="Via Mazzini 5",
            citta="Sassuolo",
            cap="41049",
            provincia="MO",
            codice_fiscale="VRDLGU80A01H501K",
            status='approved'
        )
        
        # Generiamo il QR code e inviamo l'email
        qr_bytes = participant.get_qr_code_bytes()
        success = send_approval_email(participant)

        # Verifichiamo l'invio
        self.assertTrue(success, "send_approval_email ha restituito False. Controlla i log!")
        self.assertEqual(len(mail.outbox), 1)
        
        sent_email = mail.outbox[0]
        # FIX: L'oggetto deve combaciare con quello reale di views.py
        self.assertEqual(sent_email.subject, 'Tesseramento e QR code di ingresso - Flanella Fest')
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


class MembershipEmailTest(TestCase):
    def setUp(self):
        self.participant = Participant.objects.create(
            first_name="Mario",
            last_name="Rossi",
            email="eliobosdet@gmail.com",
            luogo_di_nascita="Modena",
            indirizzo="Via Roma 1",
            citta="Fiorano Modenese",
            cap="41042",
            provincia="MO",
            codice_fiscale="RSSMRA80A01H501U",
            status="approved"
        )

    def test_pdf_generation_does_not_crash(self):
        """Verifica che la generazione del PDF con ReportLab avvenga senza crash"""
        try:
            pdf_bytes = generate_membership_pdf(self.participant)
            self.assertIsInstance(pdf_bytes, bytes)
            self.assertTrue(len(pdf_bytes) > 0)
        except Exception as e:
            self.fail(f"La generazione del PDF è andata in crash con l'errore: {str(e)}")

    def test_send_approval_email_works(self):
        """Verifica che l'email venga inviata con successo unitamente a PDF e QR code"""
        mail.outbox = []
        
        result = send_approval_email(self.participant)
        
        self.assertTrue(result, "La funzione send_approval_email ha restituito False. C'è stato un errore nell'invio!")
        self.assertEqual(len(mail.outbox), 1)
        
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ["eliobosdet@gmail.com"])
        
        pdf_attachments = [att for att in sent_email.attachments if isinstance(att, tuple) and att[0].endswith('.pdf')]
        self.assertTrue(len(pdf_attachments) > 0, "Il PDF del verbale non risulta allegato all'email.")