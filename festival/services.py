from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Member, Membership, Event, EventRegistration


def calculate_event_quote(event: Event, codice_fiscale: str = None) -> dict:
    """
    Calcola in automatico cosa deve pagare un utente per un dato Evento:
    - Solo Tessera
    - Solo Biglietto
    - Tessera + Biglietto
    - Gratuito (se è già socio per l'anno dell'evento e il biglietto non è richiesto o costa 0)
    """
    member = None
    already_member = False

    if codice_fiscale:
        cf_clean = codice_fiscale.strip().upper()
        member = Member.objects.filter(codice_fiscale=cf_clean).first()
        if member:
            already_member = member.has_valid_membership(event.year)

    needs_membership = event.requires_membership and not already_member
    membership_cost = event.membership_price_centesimi if needs_membership else 0

    needs_ticket = event.requires_ticket
    ticket_cost = event.ticket_price_centesimi if needs_ticket else 0

    total_centesimi = membership_cost + ticket_cost

    return {
        'member': member,
        'already_member': already_member,
        'needs_membership': needs_membership,
        'membership_cost_centesimi': membership_cost,
        'needs_ticket': needs_ticket,
        'ticket_cost_centesimi': ticket_cost,
        'total_centesimi': total_centesimi,
        'requires_payment': total_centesimi > 0,
    }


@transaction.atomic
def create_or_update_registration(event: Event, form_data: dict, metodo_pagamento: str = 'stripe') -> tuple[Member, EventRegistration, dict]:
    """
    Crea o aggiorna l'anagrafica del socio e prepara l'iscrizione all'evento.
    Se l'utente è già socio e l'evento è gratuito per i soci, conferma subito l'iscrizione senza Stripe.
    """
    cf_clean = form_data['codice_fiscale'].strip().upper()
    quote = calculate_event_quote(event, cf_clean)

    member, _ = Member.objects.update_or_create(
        codice_fiscale=cf_clean,
        defaults={
            'first_name': form_data.get('first_name', ''),
            'last_name': form_data.get('last_name', ''),
            'email': form_data.get('email', ''),
            'phone': form_data.get('phone', ''),
            'data_di_nascita': form_data.get('data_di_nascita'),
            'luogo_di_nascita': form_data.get('luogo_di_nascita'),
            'indirizzo': form_data.get('indirizzo'),
            'citta': form_data.get('citta'),
            'provincia': form_data.get('provincia'),
            'cap': form_data.get('cap'),
            'accetta_statuto': form_data.get('accetta_statuto', False),
            'accetta_privacy': form_data.get('accetta_privacy', False),
        }
    )

    # Se non deve pagare nulla (es. già socio per quell'anno ed evento senza biglietto a pagamento)
    if not quote['requires_payment']:
        registration, _ = EventRegistration.objects.update_or_create(
            event=event,
            member=member,
            defaults={
                'metodo_pagamento': 'free_member',
                'pagato': True,
                'status': 'approved',
                'include_membership': False,
                'include_ticket': quote['needs_ticket'],
                'total_paid_centesimi': 0,
            }
        )
    else:
        registration, _ = EventRegistration.objects.update_or_create(
            event=event,
            member=member,
            defaults={
                'metodo_pagamento': metodo_pagamento,
                'pagato': False,
                'status': 'pending',
                'include_membership': quote['needs_membership'],
                'include_ticket': quote['needs_ticket'],
                'total_paid_centesimi': quote['total_centesimi'],
            }
        )

    return member, registration, quote


@transaction.atomic
def confirm_registration_payment(registration: EventRegistration) -> EventRegistration:
    """
    Richiamata dal webhook di Stripe o dallo staff (pagamento in contanti).
    Conferma l'ingresso e, se previsto, attiva la Tessera Socio per l'anno dell'evento.
    """
    registration.pagato = True
    registration.status = 'approved'
    registration.save()

    if registration.include_membership or registration.event.requires_membership:
        Membership.objects.update_or_create(
            member=registration.member,
            year=registration.event.year,
            defaults={'is_active': True}
        )

    return registration


@transaction.atomic
def verify_and_checkin_qr(unique_id: str, event: Event) -> dict:
    """
    Verifica il QR code allo scanner dell'ingresso in base alle regole dell'evento attivo.
    Funziona anche con i QR code storici inviati nel 2026!
    """
    try:
        member = Member.objects.get(unique_id=unique_id)
    except (Member.DoesNotExist, ValidationError, ValueError):
        return {'valid': False, 'code': 'NOT_FOUND', 'message': 'QR Code non riconosciuto.'}

    # 1. Controllo requisito Tessera Socio APS
    if event.requires_membership and not member.has_valid_membership(event.year):
        return {
            'valid': False,
            'code': 'NO_MEMBERSHIP',
            'member': member,
            'message': f'{member.first_name} {member.last_name} non ha una tessera socio attiva per il {event.year}.',
        }

    registration = EventRegistration.objects.filter(event=event, member=member).first()

    # 2. Se l'evento richiede un biglietto, deve esistere una registrazione pagata/approvata
    if event.requires_ticket:
        if not registration or (not registration.pagato and registration.status not in ['approved', 'checked_in']):
            return {
                'valid': False,
                'code': 'NO_TICKET',
                'member': member,
                'message': f'Biglietto non presente o non pagato per {event.title}.',
            }

    # 3. Se l'evento è riservato ai soci senza biglietto e un socio già attivo per l'anno
    # si presenta direttamente alla porta con il suo vecchio QR code, registriamo l'ingresso al volo
    if not registration and event.requires_membership and not event.requires_ticket:
        registration = EventRegistration.objects.create(
            event=event,
            member=member,
            metodo_pagamento='free_member',
            pagato=True,
            status='checked_in',
            include_membership=False,
            include_ticket=False,
            total_paid_centesimi=0,
        )
        return {
            'valid': True,
            'code': 'CHECKED_IN',
            'member': member,
            'registration': registration,
            'message': f'Ingresso confermato per il socio {member.first_name} {member.last_name}!',
        }

    if not registration or registration.status not in ['approved', 'checked_in']:
        return {
            'valid': False,
            'code': 'NOT_APPROVED',
            'member': member,
            'message': f'Iscrizione in attesa di pagamento ({registration.status if registration else "assente"}).',
        }

    # 4. Controllo doppio ingresso
    if registration.status == 'checked_in':
        return {
            'valid': False,
            'code': 'ALREADY_CHECKED_IN',
            'member': member,
            'registration': registration,
            'message': f'ATTENZIONE: {member.first_name} {member.last_name} ha già effettuato il check-in!',
        }

    # 5. Segna il check-in
    registration.status = 'checked_in'
    registration.save()

    return {
        'valid': True,
        'code': 'CHECKED_IN',
        'member': member,
        'registration': registration,
        'message': f'Ingresso confermato per {member.first_name} {member.last_name}!',
    }