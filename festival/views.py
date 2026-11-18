import time
import logging
import json
import uuid
import stripe
import openpyxl
import base64
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from email.mime.image import MIMEImage
from django.core.mail import send_mail, EmailMessage
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout as auth_logout
from django.db import transaction
from django.conf import settings

from .utils import generate_membership_pdf
from .models import Member, Event, EventRegistration
from .forms import EventRegistrationForm
from .services import (
    calculate_event_quote,
    create_or_update_registration,
    confirm_registration_payment,
    verify_and_checkin_qr,
)

stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)


def is_admin(user):
    return user.is_staff


def is_organizer(user):
    return user.groups.filter(name="Organizer").exists() or user.is_staff


def get_current_event():
    """
    Recupera l'evento attualmente attivo.
    Se nessun evento è attivo (es. post-festival), restituisce l'ultimo evento creato (es. per consultazione staff).
    """
    active_event = Event.objects.filter(is_active=True).order_by('-year', '-id').first()
    if active_event:
        return active_event
    return Event.objects.order_by('-year', '-id').first()


def get_current_ticket_price(event=None):
    """Calcola il prezzo base da mostrare nella pagina di registrazione."""
    event = event or get_current_event()
    if event:
        total = 0
        if event.requires_membership:
            total += event.membership_price_centesimi
        if event.requires_ticket:
            total += event.ticket_price_centesimi
        return total
    return getattr(settings, 'TICKET_PRICE_CENTESIMI', 1050)

def is_event_full(event=None):
    """Controlla se l'evento ha raggiunto il limite massimo di partecipanti."""
    event = event or get_current_event()
    if not event:
        return False
    time_threshold = timezone.now() - timedelta(minutes=30)
    qs = EventRegistration.objects.filter(event=event)
    firmly_booked = qs.filter(status__in=['approved', 'checked_in']).count()
    recently_pending = qs.filter(status='pending', created_at__gte=time_threshold).count()
    return (firmly_booked + recently_pending) >= settings.MAX_PARTICIPANTS


def event_full(request):
    return render(request, 'festival/event_full.html')


def event_ended(request):
    return render(request, 'festival/event_ended.html')


def recap(request):
    return render(request, 'festival/2026/recap.html')


def privacy_view(request):
    return render(request, 'festival/privacy.html')


def payment_cancel(request):
    return render(request, 'festival/payment/payment_cancel.html')


def register(request):
    """Gestisce la registrazione multi-evento, il calcolo tessera/biglietto e il checkout Stripe."""
    event = get_current_event()

    # Se non c'è alcun evento con is_active=True, mostra la pagina di evento concluso
    if not event or not event.is_active:
        return render(request, 'festival/event_ended.html')

    if is_event_full(event):
        return render(request, 'festival/event_full.html')

    current_price_centesimi = get_current_ticket_price(event)

    if request.method == 'POST':
        form = EventRegistrationForm(request.POST, event=event)

        if form.is_valid():
            try:
                with transaction.atomic():
                    if is_event_full(event):
                        return render(request, 'festival/event_full.html')

                    gateway = request.POST.get('gateway', 'stripe')
                    if gateway == 'paypal':
                        messages.warning(request, "Il pagamento con PayPal sarà disponibile a breve.")
                        return redirect('register')

                    member, registration, quote = create_or_update_registration(
                        event=event,
                        form_data=form.cleaned_data,
                        metodo_pagamento=gateway,
                    )

                    # Caso 1: Utente già Socio nell'anno in corso ed evento senza biglietto a pagamento
                    if not quote['requires_payment']:
                        send_approval_email(registration)
                        qr_bytes = member.get_qr_code_bytes()
                        qr_base64 = base64.b64encode(qr_bytes).decode('utf-8')
                        return render(request, 'festival/payment/payment_success.html', {
                            'participant': registration,
                            'qr_base64': qr_base64,
                        })

                    # Caso 2: Pagamento richiesto tramite Stripe
                    base_url = request.build_absolute_uri('/')[:-1]
                    expiration_time = int(time.time()) + (30 * 60)

                    if quote['needs_membership'] and quote['needs_ticket']:
                        product_name = f"Tesseramento APS + Biglietto - {event.title}"
                    elif quote['needs_membership']:
                        product_name = f"Tesseramento e Ingresso - {event.title}"
                    else:
                        product_name = f"Biglietto Ingresso - {event.title}"

                    checkout_session = stripe.checkout.Session.create(
                        customer_email=member.email,
                        line_items=[{
                            'price_data': {
                                'currency': 'eur',
                                'product_data': {'name': product_name},
                                'unit_amount': quote['total_centesimi'],
                            },
                            'quantity': 1,
                        }],
                        mode='payment',
                        expires_at=expiration_time,
                        metadata={
                            'registration_id': str(registration.id),
                            'participant_id': str(member.unique_id),
                            'event_slug': event.slug,
                            'is_test_payment': 'false',
                        },
                        success_url=base_url + '/register/success/?session_id={CHECKOUT_SESSION_ID}',
                        cancel_url=base_url + '/register/cancel/',
                    )
                    return redirect(checkout_session.url, code=303)

            except Exception as e:
                messages.error(request, f"Errore con il sistema di pagamento: {str(e)}")
                return render(request, 'festival/payment/register.html', {
                    'form': form,
                    'ticket_price': current_price_centesimi / 100,
                    'event': event,
                })
    else:
        form = EventRegistrationForm(event=event)

    return render(request, 'festival/payment/register.html', {
        'form': form,
        'ticket_price': current_price_centesimi / 100,
        'event': event,
    })


def _get_registration_from_stripe_metadata(metadata):
    """Recupera EventRegistration dai metadata di Stripe (supporta sia registration_id sia participant_id)."""
    if not metadata:
        return None
    reg_id = getattr(metadata, 'registration_id', None) or (metadata.get('registration_id') if isinstance(metadata, dict) else None)
    if reg_id:
        return EventRegistration.objects.select_related('member', 'event').filter(id=reg_id).first()

    participant_id = getattr(metadata, 'participant_id', None) or (metadata.get('participant_id') if isinstance(metadata, dict) else None)
    if participant_id:
        event = get_current_event()
        return EventRegistration.objects.select_related('member', 'event').filter(
            member__unique_id=participant_id,
            event=event
        ).first()
    return None


def payment_success(request):
    """Gestisce il ritorno da Stripe, attiva l'iscrizione/tessera e mostra il QR code."""
    session_id = request.GET.get('session_id')
    registration = None
    qr_base64 = None

    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            metadata = getattr(session, 'metadata', None)
            registration = _get_registration_from_stripe_metadata(metadata)

            if registration:
                if registration.status == 'pending':
                    registration.metodo_pagamento = 'stripe'
                    confirm_registration_payment(registration)
                    send_approval_email(registration)

                qr_bytes = registration.get_qr_code_bytes()
                qr_base64 = base64.b64encode(qr_bytes).decode('utf-8')

        except Exception as e:
            logger.error(f"Errore nel recupero sessione Stripe: {str(e)}")

    return render(request, 'festival/payment/payment_success.html', {
        'participant': registration,
        'qr_base64': qr_base64,
    })


# --- VISTE ADMIN / STAFF ---

@login_required
@user_passes_test(is_admin)
def participant_detail(request, pk):
    registration = get_object_or_404(EventRegistration.objects.select_related('member', 'event'), pk=pk)
    return render(request, 'festival/participant_detail.html', {'participant': registration})


def send_approval_email(registration):
    """Invia l'email di conferma con il QR code e (se previsto dall'evento) il Verbale PDF di ammissione socio."""
    try:
        subject = f'Conferma e QR code di ingresso - {registration.event.title}'
        html_message = render_to_string('festival/approval_email.html', {
            'participant': registration,
        })

        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[registration.email],
        )
        email.content_subtype = 'html'

        banner_path = finders.find('img/elmo.webp')
        if banner_path:
            with open(banner_path, 'rb') as f:
                banner_img = MIMEImage(f.read(), _subtype='webp')
                banner_img.add_header('Content-ID', '<banner_header>')
                banner_img.add_header('Content-Disposition', 'inline', filename='banner.webp')
                email.attach(banner_img)

        # Allegato 1: Verbale PDF (solo se l'evento prevede il tesseramento APS)
        if registration.include_membership or registration.event.requires_membership:
            pdf_bytes = generate_membership_pdf(registration)
            filename_pdf = f"Verbale_Ammissione_{registration.last_name}_{registration.first_name}.pdf"
            email.attach(filename_pdf, pdf_bytes, 'application/pdf')

        # Allegato 2: QR Code PNG
        qr_bytes = registration.get_qr_code_bytes()
        email.attach(f'qrcode_{registration.unique_id}.png', qr_bytes, 'image/png')

        email.send(fail_silently=False)
        return True

    except Exception as e:
        logger.error(f"Errore invio mail a {registration.email}: {str(e)}")
        return False


def send_payment_failed_email(registration):
    subject = 'Aggiornamento registrazione - Flanella Fest'
    html_message = render_to_string('festival/rejection_email.html', {'participant': registration})
    email = EmailMessage(
        subject=subject,
        body=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[registration.email],
    )
    email.content_subtype = 'html'
    try:
        email.send()
    except Exception:
        pass


# --- CONTROLLO QR ---

@login_required
@user_passes_test(is_organizer)
def check_qr(request):
    event = get_current_event()
    qs = EventRegistration.objects.filter(event=event) if event else EventRegistration.objects.none()
    n_approved = qs.filter(status='approved').count()
    n_checked_in = qs.filter(status='checked_in').count()
    result = None

    if request.method == 'POST':
        qr_uuid = request.POST.get('qr_uuid')
        if qr_uuid:
            class DummyRequest:
                method = 'POST'
                body = json.dumps({'qr_data': qr_uuid}).encode()
            response = check_qr_result(DummyRequest())
            result = json.loads(response.content)
            request.session['manual_qr_result'] = result
            return HttpResponseRedirect(reverse('check_qr'))

    if 'manual_qr_result' in request.session:
        result = request.session['manual_qr_result']
        del request.session['manual_qr_result']

    return render(request, 'festival/check_qr.html', {
        'n_checked_in': n_checked_in,
        'total': n_checked_in + n_approved,
        'free_spots': settings.MAX_PARTICIPANTS - (n_approved + n_checked_in + settings.TOTAL_VOLUNTEERS),
        'result': result,
        'event': event,
    })


@csrf_exempt
def check_qr_result(request):
    """Verifica il QR code appoggiandosi a services.verify_and_checkin_qr."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            qr_data = (data.get('qr_data') or '').strip()
            if not qr_data:
                return JsonResponse({'valid': False, 'status': 'Dati QR Code mancanti o non validi.'})

            event = get_current_event()
            if not event:
                return JsonResponse({'valid': False, 'status': 'Nessun evento configurato nel sistema.'})

            check_res = verify_and_checkin_qr(qr_data, event)
            member = check_res.get('member')
            response_payload = {
                'valid': check_res['valid'],
                'status': check_res['message'],
            }
            if member:
                response_payload['name'] = f"{member.first_name} {member.last_name}"

            return JsonResponse(response_payload)

        except json.JSONDecodeError:
            return JsonResponse({'valid': False, 'status': 'Errore nella decodifica dei dati JSON.'})
        except Exception as e:
            return JsonResponse({'valid': False, 'status': f'Errore interno: {str(e)}'})

    return JsonResponse({'valid': False, 'status': 'Metodo non valido. Usa POST.'})


def approved_partecipants(request):
    event = get_current_event()
    approved_qs = EventRegistration.objects.select_related('member', 'event').filter(
        event=event, status='approved'
    )
    return render(request, 'festival/approved_partecipants.html', {'participants': approved_qs})


@login_required
@user_passes_test(is_organizer)
def checked_in_partecipants(request):
    event = get_current_event()
    checked_in_qs = EventRegistration.objects.select_related('member', 'event').filter(
        event=event, status='checked_in'
    )
    return render(request, 'festival/checked_in_participants.html', {
        'participants': checked_in_qs,
        'n_checked_in': checked_in_qs.count(),
    })


@login_required
@user_passes_test(is_organizer)
def all_participants(request):
    event = get_current_event()
    participants = EventRegistration.objects.select_related('member', 'event').filter(
        event=event,
        status__in=['approved', 'checked_in']
    ).order_by('-created_at')
    n_checked_in = participants.filter(status='checked_in').count()

    return render(request, 'festival/all_participants.html', {
        'participants': participants,
        'n_checked_in': n_checked_in,
        'event': event,
    })


@login_required
@user_passes_test(is_organizer)
def export_participants_excel(request):
    event = get_current_event()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Libro Soci & Partecipanti"

    headers = [
        "ID Unico", "Nome", "Cognome", "Data di Nascita", "Luogo di Nascita",
        "Codice Fiscale", "Indirizzo", "Città", "CAP", "Provincia",
        "Telefono", "Email", "Metodo Pagamento", "Stato Check-in", "Data Iscrizione"
    ]
    sheet.append(headers)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1A1A1A", end_color="1A1A1A", fill_type="solid")

    for cell in sheet[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    participants = EventRegistration.objects.select_related('member', 'event').filter(
        event=event,
        status__in=['approved', 'checked_in']
    ).order_by('-created_at')

    for p in participants:
        sheet.append([
            str(p.unique_id),
            p.first_name,
            p.last_name,
            p.data_di_nascita.strftime("%d/%m/%Y") if p.data_di_nascita else "",
            p.luogo_di_nascita or "",
            p.codice_fiscale or "",
            p.indirizzo or "",
            p.citta or "",
            p.cap or "",
            p.provincia or "",
            p.phone or "",
            p.email or "",
            p.get_metodo_pagamento_display(),
            "Arrivato" if p.status == 'checked_in' else "In attesa",
            p.created_at.strftime("%d/%m/%Y %H:%M"),
        ])

    for col in sheet.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        sheet.column_dimensions[column].width = max(max_length + 3, 12)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="libro_soci_flanellafest.xlsx"'
    workbook.save(response)
    return response


@login_required
@user_passes_test(is_organizer)
def logout(request):
    auth_logout(request)
    return redirect('home')


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = getattr(session, 'metadata', None)
        is_test_payment = getattr(metadata, 'is_test_payment', 'false') if metadata else 'false'

        if is_test_payment == 'true':
            send_mail(
                'Stripe Prod Test OK - Flanella Fest',
                'Il test da 50 centesimi è andato a buon fine.',
                settings.DEFAULT_FROM_EMAIL,
                [settings.EMAIL_HOST_USER],
                fail_silently=True,
            )
            return HttpResponse(status=200)

        registration = _get_registration_from_stripe_metadata(metadata)
        if registration:
            if registration.status == 'pending':
                registration.metodo_pagamento = 'stripe'
                confirm_registration_payment(registration)
                send_approval_email(registration)
        else:
            return HttpResponse(status=404)

    elif event['type'] == 'checkout.session.expired':
        session = event['data']['object']
        metadata = getattr(session, 'metadata', None)
        is_test_payment = getattr(metadata, 'is_test_payment', 'false') if metadata else 'false'

        if is_test_payment == 'true':
            return HttpResponse(status=200)

        registration = _get_registration_from_stripe_metadata(metadata)
        if registration and registration.status == 'pending':
            registration.status = 'rejected'
            registration.save()

    return HttpResponse(status=200)


@login_required
@user_passes_test(is_admin)
def admin_management(request):
    event = get_current_event()

    if request.method == 'POST':
        new_price_euro = request.POST.get('ticket_price')
        if new_price_euro and event:
            try:
                centesimi = int(float(new_price_euro.replace(',', '.')) * 100)
                if event.requires_membership:
                    event.membership_price_centesimi = centesimi
                else:
                    event.ticket_price_centesimi = centesimi
                event.save()
                messages.success(request, f"Prezzo per '{event.title}' aggiornato a {new_price_euro} €!")
            except ValueError:
                messages.error(request, "Inserisci un valore numerico valido.")
            return redirect('admin_management')

    current_price_centesimi = get_current_ticket_price(event)
    return render(request, 'festival/admin_management.html', {
        'current_price_euro': current_price_centesimi / 100,
        'event': event,
    })


@login_required
@user_passes_test(is_admin)
def stripe_test_checkout(request):
    base_url = request.build_absolute_uri('/')[:-1]
    admin_email = request.user.email if request.user.email else settings.EMAIL_HOST_USER

    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=admin_email,
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'TEST SISTEMA DI PAGAMENTO LIVE',
                        'description': 'Transazione di test per verifica API e Webhook.'
                    },
                    'unit_amount': 50,
                },
                'quantity': 1,
            }],
            mode='payment',
            metadata={'is_test_payment': 'true'},
            success_url=base_url + '/register/success/?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=base_url + '/register/cancel/',
        )
        return redirect(checkout_session.url, code=303)

    except Exception as e:
        messages.error(request, f"Errore test Stripe: {str(e)}")
        return redirect('admin_management')


@login_required
def toggle_checkin(request, pk):
    if request.method == 'POST':
        registration = get_object_or_404(EventRegistration.objects.select_related('member'), pk=pk)

        if registration.status == 'checked_in':
            registration.status = 'approved'
            messages.warning(request, f"Arrivo annullato per {registration.first_name} {registration.last_name}.")
        else:
            registration.status = 'checked_in'
            messages.success(request, f"{registration.first_name} {registration.last_name} segnato come arrivato!")

        registration.save()

    return redirect('participant_detail', pk=pk)

def check_quote_api(request):
    """Restituisce in JSON il preventivo aggiornato in base al Codice Fiscale inserito nel form."""
    event = get_current_event()
    if not event:
        return JsonResponse({'error': 'Nessun evento attivo'}, status=404)

    cf = request.GET.get('cf', '').strip().upper()
    quote = calculate_event_quote(event, cf)
    return JsonResponse({
        'already_member': quote['already_member'],
        'needs_membership': quote['needs_membership'],
        'membership_euro': f"{quote['membership_cost_centesimi'] / 100:.2f}",
        'needs_ticket': quote['needs_ticket'],
        'ticket_euro': f"{quote['ticket_cost_centesimi'] / 100:.2f}",
        'total_euro': f"{quote['total_centesimi'] / 100:.2f}",
        'requires_payment': quote['requires_payment'],
    })