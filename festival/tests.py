# from django.test import TestCase, Client
# from django.urls import reverse
# from django.contrib.auth.models import User
# from django.core import mail
# from festival.models import Participant
# from festival.views import send_approval_email
# from festival.utils import generate_membership_pdf
# from unittest.mock import patch

# class FullRegistrationAndEmailTests(TestCase):

#     def setUp(self):
#         self.client = Client()
#         self.register_url = reverse('register')
#         self.valid_payload = {
#             'first_name': 'Mario',
#             'last_name': 'Rossi',
#             'email': 'mario.rossi@example.com',
#             'confirm_email': 'mario.rossi@example.com',
#             'phone': '3331234567',
#             'data_di_nascita': '1995-05-20',
#             'luogo_di_nascita': 'Modena',
#             'codice_fiscale': 'RSSMRA95E20F257X',
#             'indirizzo': 'Via Roma 10',
#             'citta': 'Fiorano Modenese',
#             'provincia': 'MO',
#             'cap': '41042',
#             'accetta_statuto': True,
#             'accetta_privacy': True,
#             'gateway': 'stripe'
#         }

#     @patch('stripe.checkout.Session.create')
#     def test_single_registration_creation(self, mock_stripe_session):
#         """Verifica che la registrazione crei 1 solo partecipante in 'pending'"""
#         mock_stripe_session.return_value = type('obj', (object,), {'url': 'https://checkout.stripe.com/test'})

#         response = self.client.post(self.register_url, data=self.valid_payload)

#         self.assertIn(response.status_code, [302, 303])
#         self.assertEqual(Participant.objects.count(), 1)

#         participant = Participant.objects.first()
#         self.assertEqual(participant.status, 'pending')
#         self.assertFalse(getattr(participant, 'pagato', False)) # Uso sicuro se il campo è stato rimosso

#     def test_send_approval_email_and_qr_code(self):
#         """Verifica che send_approval_email generi la mail con l'oggetto e l'allegato corretto"""
#         # Svuotiamo l'outbox
#         mail.outbox = []
        
#         participant = Participant.objects.create(
#             first_name='Luigi',
#             last_name='Verdi',
#             email='luigi.verdi@example.com',
#             phone='3339876543',
#             luogo_di_nascita="Sassuolo",
#             indirizzo="Via Mazzini 5",
#             citta="Sassuolo",
#             cap="41049",
#             provincia="MO",
#             codice_fiscale="VRDLGU80A01H501K",
#             status='approved'
#         )
        
#         # Generiamo il QR code e inviamo l'email
#         qr_bytes = participant.get_qr_code_bytes()
#         success = send_approval_email(participant)

#         # Verifichiamo l'invio
#         self.assertTrue(success, "send_approval_email ha restituito False. Controlla i log!")
#         self.assertEqual(len(mail.outbox), 1)
        
#         sent_email = mail.outbox[0]
#         # FIX: L'oggetto deve combaciare con quello reale di views.py
#         self.assertEqual(sent_email.subject, 'Tesseramento e QR code di ingresso - Flanella Fest')
#         self.assertIn('luigi.verdi@example.com', sent_email.to)

#     def test_export_excel_returns_correct_content_type(self):
#         """Verifica che l'export Excel funzioni correttamente per gli organizer"""
#         staff_user = User.objects.create_user(
#             username='staff',
#             email='staff@test.com',
#             password='password',
#             is_staff=True
#         )
#         self.client.login(username='staff', password='password')

#         response = self.client.get(reverse('export_participants_excel'))
        
#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(
#             response['Content-Type'], 
#             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#         )


# class MembershipEmailTest(TestCase):
#     def setUp(self):
#         self.participant = Participant.objects.create(
#             first_name="Mario",
#             last_name="Rossi",
#             email="eliobosdet@gmail.com",
#             luogo_di_nascita="Modena",
#             indirizzo="Via Roma 1",
#             citta="Fiorano Modenese",
#             cap="41042",
#             provincia="MO",
#             codice_fiscale="RSSMRA80A01H501U",
#             status="approved"
#         )

#     def test_pdf_generation_does_not_crash(self):
#         """Verifica che la generazione del PDF con ReportLab avvenga senza crash"""
#         try:
#             pdf_bytes = generate_membership_pdf(self.participant)
#             self.assertIsInstance(pdf_bytes, bytes)
#             self.assertTrue(len(pdf_bytes) > 0)
#         except Exception as e:
#             self.fail(f"La generazione del PDF è andata in crash con l'errore: {str(e)}")

#     def test_send_approval_email_works(self):
#         """Verifica che l'email venga inviata con successo unitamente a PDF e QR code"""
#         mail.outbox = []
        
#         result = send_approval_email(self.participant)
        
#         self.assertTrue(result, "La funzione send_approval_email ha restituito False. C'è stato un errore nell'invio!")
#         self.assertEqual(len(mail.outbox), 1)
        
#         sent_email = mail.outbox[0]
#         self.assertEqual(sent_email.to, ["eliobosdet@gmail.com"])
        
#         pdf_attachments = [att for att in sent_email.attachments if isinstance(att, tuple) and att[0].endswith('.pdf')]
#         self.assertTrue(len(pdf_attachments) > 0, "Il PDF del verbale non risulta allegato all'email.")



# -------------------------------------------------------------


from datetime import date
from django.test import TestCase
from .models import Member, Membership, Event, EventRegistration
from .services import (
    calculate_event_quote,
    create_or_update_registration,
    confirm_registration_payment,
    verify_and_checkin_qr,
)


class MultiEventArchitectureTests(TestCase):

    def setUp(self):
        # Dati anagrafici di prova
        self.user_data = {
            'first_name': 'mario',
            'last_name': 'rossi',
            'email': 'mario.rossi@example.com',
            'phone': '3331234567',
            'data_di_nascita': date(1998, 5, 20),
            'luogo_di_nascita': 'modena',
            'codice_fiscale': 'rssmra98e20f257x',
            'indirizzo': 'Via Emilia 10',
            'citta': 'modena',
            'provincia': 'mo',
            'cap': '41121',
            'accetta_statuto': True,
            'accetta_privacy': True,
        }

        # Scenario 1: Evento classico APS (Solo Tessera 10.50€, Ingresso gratuito ai soci)
        self.event_membership_only = Event.objects.create(
            title="Flanella Fest IV",
            slug="flanella-fest-4",
            year=2027,
            is_active=True,
            requires_membership=True,
            membership_price_centesimi=1050,
            requires_ticket=False,
            ticket_price_centesimi=0,
        )

        # Scenario 2: Evento solo Biglietto 15.00€ (Nessuna tessera socio richiesta)
        self.event_ticket_only = Event.objects.create(
            title="Concerto Estivo",
            slug="concerto-estivo",
            year=2027,
            is_active=True,
            requires_membership=False,
            membership_price_centesimi=0,
            requires_ticket=True,
            ticket_price_centesimi=1500,
        )

        # Scenario 3: Evento Combinato (Tessera 10.00€ + Biglietto 12.00€)
        self.event_combo = Event.objects.create(
            title="Festival Invernale",
            slug="festival-invernale",
            year=2027,
            is_active=True,
            requires_membership=True,
            membership_price_centesimi=1000,
            requires_ticket=True,
            ticket_price_centesimi=1200,
        )

    def test_scenario_1_new_member_membership_only(self):
        """Un nuovo utente paga la tessera (10.50€), viene iscritto al Libro Soci e può fare check-in."""
        member, reg, quote = create_or_update_registration(self.event_membership_only, self.user_data)

        # Verifica normalizzazione dati e preventivo
        self.assertEqual(member.first_name, "Mario")
        self.assertEqual(member.provincia, "MO")
        self.assertEqual(quote['total_centesimi'], 1050)
        self.assertTrue(quote['requires_payment'])
        self.assertEqual(reg.status, 'pending')
        self.assertFalse(member.has_valid_membership(2027))

        # Simula pagamento confermato da Stripe
        confirm_registration_payment(reg)
        self.assertTrue(member.has_valid_membership(2027))
        self.assertEqual(reg.status, 'approved')

    def test_scenario_2_existing_member_free_second_event(self):
        """Chi è già socio nell'anno in corso non ripaga la tessera per un altro evento gratuito soci."""
        member, reg1, _ = create_or_update_registration(self.event_membership_only, self.user_data)
        confirm_registration_payment(reg1)

        # Creiamo un secondo evento gratuito riservato ai soci nello stesso anno 2027
        second_event = Event.objects.create(
            title="Secret Gig Autunno",
            slug="secret-gig-2027",
            year=2027,
            requires_membership=True,
            membership_price_centesimi=1050,
            requires_ticket=False,
        )

        _, reg2, quote2 = create_or_update_registration(second_event, self.user_data)
        self.assertEqual(quote2['total_centesimi'], 0)
        self.assertFalse(quote2['requires_payment'])
        self.assertEqual(reg2.status, 'approved')
        self.assertEqual(reg2.metodo_pagamento, 'free_member')

    def test_scenario_3_ticket_only_without_membership(self):
        """Evento con solo biglietto: l'utente paga 15€ ma non diventa socio APS."""
        member, reg, quote = create_or_update_registration(self.event_ticket_only, self.user_data)

        self.assertEqual(quote['total_centesimi'], 1500)
        self.assertFalse(quote['needs_membership'])
        self.assertTrue(quote['needs_ticket'])

        confirm_registration_payment(reg)
        self.assertEqual(reg.status, 'approved')
        # Verifica che NON sia stata creata una tessera socio nel Libro Soci
        self.assertFalse(member.has_valid_membership(2027))

    def test_scenario_4_combo_event_new_vs_existing_member(self):
        """Evento Tessera (10€) + Biglietto (12€): nuovo utente paga 22€, già socio paga solo 12€."""
        # 1. Utente non ancora socio: deve pagare 1000 + 1200 = 2200 centesimi
        quote_new = calculate_event_quote(self.event_combo, self.user_data['codice_fiscale'])
        self.assertEqual(quote_new['total_centesimi'], 2200)

        # 2. L'utente diventa socio al primo festival
        member, reg1, _ = create_or_update_registration(self.event_membership_only, self.user_data)
        confirm_registration_payment(reg1)

        # 3. Ora si iscrive all'evento combo: deve pagare solo il biglietto (1200 centesimi)
        quote_existing = calculate_event_quote(self.event_combo, member.codice_fiscale)
        self.assertTrue(quote_existing['already_member'])
        self.assertFalse(quote_existing['needs_membership'])
        self.assertEqual(quote_existing['total_centesimi'], 1200)

    def test_qr_checkin_and_anti_passback(self):
        """Verifica che il QR code permetta il primo ingresso e blocchi il secondo tentativo."""
        member, reg, _ = create_or_update_registration(self.event_membership_only, self.user_data)

        # Prima del pagamento: QR rifiutato
        res_unpaid = verify_and_checkin_qr(str(member.unique_id), self.event_membership_only)
        self.assertFalse(res_unpaid['valid'])
        self.assertEqual(res_unpaid['code'], 'NO_MEMBERSHIP')

        # Dopo il pagamento: Primo check-in valido
        confirm_registration_payment(reg)
        res_ok = verify_and_checkin_qr(str(member.unique_id), self.event_membership_only)
        self.assertTrue(res_ok['valid'])
        self.assertEqual(res_ok['code'], 'CHECKED_IN')

        # Secondo tentativo con lo stesso QR: Bloccato
        res_duplicate = verify_and_checkin_qr(str(member.unique_id), self.event_membership_only)
        self.assertFalse(res_duplicate['valid'])
        self.assertEqual(res_duplicate['code'], 'ALREADY_CHECKED_IN')

    def test_form_blocks_duplicate_on_same_event_but_allows_new_event(self):
        """Il form blocca chi è già iscritto allo stesso evento, ma permette ai vecchi soci di iscriversi a un nuovo evento."""
        from .forms import EventRegistrationForm

        # 1. L'utente si iscrive e paga per il primo evento
        member, reg, _ = create_or_update_registration(self.event_membership_only, self.user_data)
        confirm_registration_payment(reg)

        # 2. Riprova a compilare il form per lo STESSO evento -> Deve essere bloccato
        form_same_event = EventRegistrationForm(data=self.user_data, event=self.event_membership_only)
        self.assertFalse(form_same_event.is_valid())
        self.assertIn('codice_fiscale', form_same_event.errors)

        # 3. Compila il form per un NUOVO evento (es. Concerto Estivo solo biglietto) -> Deve passare
        minimal_ticket_data = {
            'first_name': 'Mario',
            'last_name': 'Rossi',
            'email': 'mario.rossi@example.com',
            'phone': '3331234567',
            'codice_fiscale': 'RSSMRA98E20F257X',
            'accetta_privacy': True,
        }
        form_ticket_event = EventRegistrationForm(data=minimal_ticket_data, event=self.event_ticket_only)
        self.assertTrue(form_ticket_event.is_valid())


from django.urls import reverse
from django.contrib.auth.models import User
import json


class ViewsIntegrationTests(TestCase):

    def setUp(self):
        self.event_2026, _ = Event.objects.update_or_create(
            slug="flanella-fest-3",
            defaults={
                'title': "Flanella Fest III",
                'year': 2026,
                'is_active': False,  # Evento concluso
                'requires_membership': True,
                'membership_price_centesimi': 1050,
            }
        )
        self.member = Member.objects.create(
            first_name="Luca",
            last_name="Bianchi",
            email="luca@example.com",
            phone="3339876543",
            codice_fiscale="BNCLCU95A01F257Z",
        )
        Membership.objects.create(member=self.member, year=2026, is_active=True)
        self.reg = EventRegistration.objects.create(
            event=self.event_2026,
            member=self.member,
            pagato=True,
            status='approved',
            include_membership=True,
            total_paid_centesimi=1050,
        )
        
    def test_register_view_shows_event_ended_when_inactive(self):
        """Se l'evento ha is_active=False, la pagina /register/ mostra event_ended.html."""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'festival/event_ended.html')

    def test_check_qr_result_endpoint_json(self):
        """Lo scanner QR via POST JSON valida il socio e blocca il secondo passaggio."""
        url = reverse('check_qr_result')
        payload = json.dumps({'qr_data': str(self.member.unique_id)})

        # 1. Primo passaggio allo scanner -> Valido
        res1 = self.client.post(url, data=payload, content_type='application/json')
        data1 = res1.json()
        self.assertTrue(data1['valid'])
        self.assertEqual(data1['name'], "Luca Bianchi")

        # 2. Secondo passaggio allo scanner -> Già entrato (Falso)
        res2 = self.client.post(url, data=payload, content_type='application/json')
        data2 = res2.json()
        self.assertFalse(data2['valid'])