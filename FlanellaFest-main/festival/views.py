import time
import json
import uuid
import stripe
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.contrib.auth import logout as auth_logout
from .models import Participant, Registration, FestivalConfig
from .forms import RegistrationForm, ParticipantFormSet

stripe.api_key = settings.STRIPE_SECRET_KEY

def is_admin(user):
    return user.is_staff


def is_organizer(user):
    return user.groups.filter(name="Organizer").exists() or user.is_staff



def is_event_full():
    """Verifica se l'evento ha raggiunto il limite (300) tenendo conto dei carrelli attivi"""
    
    # Biglietti effettivamente venduti o già scansionati all'ingresso
    firmly_booked = Participant.objects.filter(status__in=['approved', 'checked_in']).count()
    
    # Biglietti bloccati nel carrello (creati da meno di 30 minuti)
    time_threshold = timezone.now() - timedelta(minutes=30)
    recently_approved = Participant.objects.filter(status='approved', created_at__gte=time_threshold).count()

    total_count = firmly_booked + recently_approved
    print(f"Disponibilità: {total_count}/300 (Confermati: {firmly_booked}, Nel carrello: {recently_approved})")
    
    return total_count >= 300


def event_full(request):
    return render(request, 'festival/event_full.html')


def home(request):
    if is_event_full():
        return render(request, 'festival/event_full.html')
    else:
        return render(request, 'festival/home.html')

def about(request):
    return render(request, 'festival/about.html')

def register(request):
    if is_event_full():
        return render(request, 'festival/event_full.html')

    current_price_centesimi = get_current_ticket_price()

    if request.method == 'POST':
        registration_form = RegistrationForm(request.POST)
        participant_formset = ParticipantFormSet(request.POST, prefix='participants')

        if registration_form.is_valid() and participant_formset.is_valid():
            registration = registration_form.save()
            phone = registration.phone
            participants_to_create = []
            total_tickets = 0

            for form in participant_formset:
                if form.cleaned_data:
                    participant = form.save(commit=False)
                    participant.registration = registration
                    participant.phone = phone
                    participants_to_create.append(participant)
                    total_tickets += 1
            
            for p in participants_to_create:
                p.save()

            base_url = request.build_absolute_uri('/')[:-1]
            expiration_time = int(time.time()) + (30 * 60)
            
            try:
                checkout_session = stripe.checkout.Session.create(
                    customer_email=registration.email,
                    line_items=[{
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': 'Biglietto Flanella Fest',
                            },
                            'unit_amount': current_price_centesimi, # <-- ORA È DINAMICO!
                        },
                        'quantity': total_tickets,
                    }],
                    mode='payment',
                    expires_at=expiration_time,
                    metadata={
                        'registration_id': registration.id,
                        'is_test_payment': 'false' # Segnaliamo che è un acquisto vero
                    },
                    success_url=base_url + '/register/success/',
                    cancel_url=base_url + '/register/cancel/',
                )
                return redirect(checkout_session.url, code=303)
                
            except Exception as e:
                messages.error(request, f"Errore con Stripe: {str(e)}")
                return render(request, 'festival/payment/register.html', {
                    'registration_form': registration_form,
                    'participant_formset': participant_formset
                })
    else:
        registration_form = RegistrationForm()
        participant_formset = ParticipantFormSet(prefix='participants')
    
    return render(request, 'festival/payment/register.html', {
        'registration_form': registration_form,
        'participant_formset': participant_formset,
        'ticket_price': current_price_centesimi / 100 # Mostra il prezzo in Euro corretto
    })

def payment_success(request):
    return render(request, 'festival/payment/payment_success.html')

def payment_cancel(request):
    return render(request, 'festival/payment/payment_cancel.html')


@login_required
@user_passes_test(is_organizer)
def approved_requests(request):
    # Raggruppa i partecipanti per registrazione
    approved_registrations = Registration.objects.filter(
        participants__status='approved'
    ).distinct().order_by('-created_at')

    users_approved = Registration.objects.filter(participants__status='approved').count()
    users_checked_in = Registration.objects.filter(participants__status='checked_in').count()

    return render(request, 'festival/approved_requests.html', {
        'registrations': approved_registrations,
        'users_checked_in': users_checked_in,
        'users_approved': users_approved
    })


@login_required
@user_passes_test(is_organizer)
def registration_detail(request, pk):
    registration = get_object_or_404(Registration, pk=pk)
    participants = registration.participants.all()

    return render(request, 'festival/registration_detail.html', {
        'registration': registration,
        'participants': participants
    })

def send_approval_email(participant):
    """Invia un'email di approvazione con il QR code al partecipante"""
    subject = 'Registrazione approvata - Flanella Fest'

    # Usa il template HTML per il corpo dell'email
    html_message = render_to_string('festival/approval_email.html', {'participant': participant})

    # Crea un oggetto EmailMessage invece di usare send_mail
    email = EmailMessage(
        subject=subject,
        body=html_message,
        from_email='noreply@flanellafest.it',
        to=[participant.email]
    )

    # Imposta il tipo di contenuto come HTML
    email.content_subtype = 'html'

    # Allega il QR code se esiste
    if participant.qr_code:
        try:
            email.attach_file(participant.qr_code.path)
        except Exception as e:
            print(f"Errore nell'allegare il QR code: {str(e)}")

    # Invia l'email
    email.send()


def send_payment_failed_email(participant):
    """Invia un'email quando la sessione di Stripe scade o il pagamento fallisce"""
    subject = 'Aggiornamento registrazione - Flanella Fest'

    # Usa un nuovo template HTML per l'email
    html_message = render_to_string('festival/rejection_email.html', {'participant': participant})

    email = EmailMessage(
        subject=subject,
        body=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL, # Usa l'email configurata in settings
        to=[participant.email]
    )
    email.content_subtype = 'html'
    
    try:
        email.send()
    except Exception as e:
        print(f"Errore nell'invio dell'email di fallimento: {str(e)}")


@login_required
@user_passes_test(is_admin)
def participant_detail(request, pk):
    participant = get_object_or_404(Participant, pk=pk)
    return render(request, 'festival/participant_detail.html', {'participant': participant})


@login_required
@user_passes_test(is_organizer)
def check_qr(request):
    n_approved = Registration.objects.filter(participants__status='approved').count()
    n_checked_in = Registration.objects.filter(participants__status='checked_in').count()
    # Gestione verifica manuale
    result = None
    if request.method == 'POST':
        qr_uuid = request.POST.get('qr_uuid')
        if qr_uuid:
            # Simuliamo una richiesta al metodo check_qr_result
            # Inviamo manualmente l'UUID alla stessa funzione che gestisce il QR code

            # Creiamo un oggetto request fittizio con i dati necessari
            class DummyRequest:
                method = 'POST'
                body = json.dumps({'qr_data': qr_uuid}).encode()

            # Chiamiamo la funzione check_qr_result
            response = check_qr_result(DummyRequest())

            # Convertiamo la risposta JSON in un dizionario
            result = json.loads(response.content)

            # Memorizziamo temporaneamente il risultato nella sessione
            request.session['manual_qr_result'] = result

            # Redirect to the same page to avoid form resubmission on refresh
            return HttpResponseRedirect(reverse('check_qr'))

    # Recuperiamo il risultato dalla sessione se esiste
    if 'manual_qr_result' in request.session:
        result = request.session['manual_qr_result']
        # Eliminiamo il risultato dalla sessione dopo averlo usato
        del request.session['manual_qr_result']

    return render(request, 'festival/check_qr.html', {
        'n_checked_in': n_checked_in,
        'total_approved': n_approved + n_checked_in,
        'result': result
    })



@csrf_exempt
def check_qr_result(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            qr_data = data.get('qr_data')

            # Se non c'è il qr_data, restituisci un errore
            if not qr_data:
                return JsonResponse({
                    'valid': False,
                    'status': 'Dati QR Code mancanti o non validi.'
                })

            # Pulisci il qr_data
            qr_data = qr_data.strip()

            try:
                # Prova a convertire in UUID, in caso di errore usa il valore originale
                try:
                    uuid_obj = uuid.UUID(qr_data)
                    participant = Participant.objects.get(unique_id=uuid_obj)
                except (ValueError, TypeError):
                    # Se la conversione a UUID fallisce, cerca con il valore originale
                    participant = Participant.objects.get(unique_id=qr_data)

                name = f"{participant.first_name} {participant.last_name}"
                # Verifica se il partecipante è approvato
                if participant.status == 'approved':
                    # Aggiorna lo stato in "checked_in"
                    participant.status = 'checked_in'
                    participant.save()

                    return JsonResponse({
                        'valid': True,
                        'name': name,
                        'status': 'Benvenuto! Partecipante verificato.'
                    })
                elif participant.status == 'checked_in':
                    return JsonResponse({
                        'valid': False,
                        'name': name,
                        'status': 'Questo QR code è già stato usato.'
                    })
                else:
                    return JsonResponse({
                        'valid': False,
                        'name': name,
                        'status': f'Stato: {participant.get_status_display()}'
                    })
            except Participant.DoesNotExist:
                return JsonResponse({
                    'valid': False,
                    'status': f'QR code non valido o non trovato: {qr_data}'
                })
            except Exception as e:
                return JsonResponse({
                    'valid': False,
                    'status': f'Errore durante la verifica: {str(e)}'
                })

        except json.JSONDecodeError:
            return JsonResponse({
                'valid': False,
                'status': 'Errore nella decodifica dei dati JSON.'
            })
        except Exception as e:
            return JsonResponse({
                'valid': False,
                'status': f'Errore interno: {str(e)}'
            })

    # Se non è una richiesta POST, mostra la pagina normale
    return JsonResponse({
        'valid': False,
        'status': 'Metodo non valido. Usa POST.'
    })


def approved_partecipants(request):
    approved_partecipants = Participant.objects.filter(status='approved')
    return render(request, 'festival/approved_partecipants.html', {'participants': approved_partecipants})


@login_required
@user_passes_test(is_organizer)
def checked_in_partecipants(request):
    checked_in_partecipants = Participant.objects.filter(status='checked_in')
    n_checked_in = checked_in_partecipants.count()
    return render(request, 'festival/checked_in_participants.html', {
                  'participants': checked_in_partecipants,
                  'n_checked_in': n_checked_in
    })



@login_required
@user_passes_test(is_organizer)
def all_participants(request):
    participants = Participant.objects.filter(status='approved') | Participant.objects.filter(status='checked_in')
    n_checked_in = Participant.objects.filter(status='checked_in').count()
    return render(request, 'festival/all_participants.html', { 'participants' : participants, 'n_checked_in': n_checked_in })


@login_required
@user_passes_test(is_organizer)
def all_participants_pdf(request):
    from weasyprint import HTML
    
    participants = Participant.objects.filter(status='approved') | Participant.objects.filter(status='checked_in')
    n_checked_in = Participant.objects.filter(status='checked_in').count()

    template = get_template('festival/all_participants_pdf.html')
    html_string = template.render({'participants' : participants, 'n_checked_in': n_checked_in })

    base_url = request.build_absolute_uri('/')
    pdf_file = HTML(string=html_string, base_url=base_url).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment;filename="partecipanti.pdf"'

    return response

@login_required
@user_passes_test(is_organizer)
def logout(request):
    auth_logout(request)
    return redirect('home')


# Helper per recuperare il prezzo dinamico dal database
def get_current_ticket_price():
    """ Calcola automaticamente il prezzo fisso in base ai biglietti venduti:
        - Primi 50 biglietti (Early Bird): 5.50€
        - Successivi (Regular): 10.50€
    """
    
    # 1. Contiamo i biglietti venduti e quelli "bloccati" in carrelli attivi (ultimi 30 min)
    time_threshold = timezone.now() - timedelta(minutes=30)
    
    sold_or_locked_tickets = Participant.objects.filter(
        status__in=['approved', 'checked_in']
    ).count() + Participant.objects.filter(
        status='pending', 
        created_at__gte=time_threshold
    ).count()

    # 2. Applichiamo la tariffa fissa in base alla soglia
    if sold_or_locked_tickets < 50:
        price_centesimi = 550   # 5.50 € per i primi 50
    else:
        price_centesimi = 1050  # 10.50 € dal 51esimo in poi
    
    return price_centesimi
# --- NUOVE VISTE PER LA GESTIONE ADMIN E TEST DA 1 CENTESIMO ---

@login_required
@user_passes_test(is_admin)
def admin_management(request):
    config = FestivalConfig.objects.first()
    if not config:
        config = FestivalConfig.objects.create(ticket_price_centesimi=settings.TICKET_PRICE_CENTESIMI)

    if request.method == 'POST':
        new_price_euro = request.POST.get('ticket_price')
        if new_price_euro:
            try:
                # Convertiamo l'input in Euro (es: 15.50 o 15) in centesimi interi
                centesimi = int(float(new_price_euro.replace(',', '.')) * 100)
                config.ticket_price_centesimi = centesimi
                config.save()
                messages.success(request, f"Prezzo del biglietto aggiornato con successo a {new_price_euro} €!")
            except ValueError:
                messages.error(request, "Inserisci un valore numerico valido per il prezzo.")
            return redirect('admin_management')

    return render(request, 'festival/admin_management.html', {
        'current_price_euro': config.ticket_price_centesimi / 100
    })

@login_required
@user_passes_test(is_admin)
def stripe_test_checkout(request):
    """Crea una sessione di checkout da 50 centesimi per i test in produzione"""
    base_url = request.build_absolute_uri('/')[:-1]
    
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=request.user.email,
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'TEST SISTEMA DI PAGAMENTO (50 CENTESIMI)',
                    },
                    'unit_amount': 50, # 50 Centesimi di Euro
                },
                'quantity': 1,
            }],
            mode='payment',
            metadata={
                'is_test_payment': 'true' # <-- FONDAMENTALE: Dice al Webhook di ignorare i contatori posti
            },
            success_url=base_url + '/register/success/',
            cancel_url=base_url + '/register/cancel/',
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        messages.error(request, f"Errore nella creazione del test Stripe: {str(e)}")
        return redirect('admin_management')


# --- AGGIORNA IL TUO WEBHOOK PER INTERCETTARE IL TEST ---
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Controlliamo prima se si tratta del pagamento di test da 50 centesimi
        is_test_payment = 'false'
        if 'metadata' in session and 'is_test_payment' in session['metadata']:
            is_test_payment = session['metadata']['is_test_payment']

        if is_test_payment == 'true':
            # È un test! Non tocchiamo il database, non registriamo partecipanti.
            # Inviamo solo una mail all'admin per confermare che il webhook risponde
            send_mail(
                'Stripe Prod Test OK - Flanella Fest',
                'Il test da 50 centesimi è andato a buon fine. Il circuito dei Webhook risponde correttamente!',
                settings.DEFAULT_FROM_EMAIL,
                [settings.EMAIL_HOST_USER],
                fail_silently=True
            )
            return HttpResponse(status=200) # Chiudiamo dicendo a Stripe che è tutto OK

        # --- SE NON È UN TEST, PROCEDI CON LA LOGICA REALE COMPRATORI ---
        registration_id = None
        if 'metadata' in session and 'registration_id' in session['metadata']:
            registration_id = session['metadata']['registration_id']
        
        if registration_id:
            try:
                registration = Registration.objects.get(id=registration_id)
                participants = registration.participants.filter(status='pending')
                
                for participant in participants:
                    participant.status = 'approved'
                    participant.generate_qr_code()
                    participant.save()
                    send_approval_email(participant)
            except Registration.DoesNotExist:
                return HttpResponse(status=404)

    elif event['type'] == 'checkout.session.expired':
        session = event['data']['object']
        
        # Ignoriamo la scadenza se era una sessione di test
        if 'metadata' in session and session['metadata'].get('is_test_payment') == 'true':
            return HttpResponse(status=200)

        registration_id = None
        if 'metadata' in session and 'registration_id' in session['metadata']:
            registration_id = session['metadata']['registration_id']
        
        if registration_id:
            try:
                registration = Registration.objects.get(id=registration_id)
                participants = registration.participants.filter(status='pending')
                for participant in participants:
                    participant.status = 'rejected'
                    participant.save()
                    send_payment_failed_email(participant)
            except Registration.DoesNotExist:
                pass 

    return HttpResponse(status=200)
