from django.db import migrations
from django.db.models import Case, When, Value, IntegerField


def forwards_func(apps, schema_editor):
    Participant = apps.get_model('festival', 'Participant')
    FestivalConfig = apps.get_model('festival', 'FestivalConfig')
    Member = apps.get_model('festival', 'Member')
    Membership = apps.get_model('festival', 'Membership')
    Event = apps.get_model('festival', 'Event')
    EventRegistration = apps.get_model('festival', 'EventRegistration')

    # 1. Recupera il prezzo configurato nel 2026
    config = FestivalConfig.objects.first()
    price_2026 = config.ticket_price_centesimi if config else 1050

    # 2. Crea l'evento storico Flanella Fest III (2026)
    event_2026, _ = Event.objects.get_or_create(
        slug='flanella-fest-3',
        defaults={
            'title': 'Flanella Fest III Edizione',
            'year': 2026,
            'is_active': False,
            'requires_membership': True,
            'membership_price_centesimi': price_2026,
            'requires_ticket': False,
            'ticket_price_centesimi': 0,
        }
    )

    # 3. Ordina i partecipanti dando priorità a chi è entrato o ha pagato,
    # così in caso di CF duplicati vince sempre il QR code valido!
    participants = Participant.objects.annotate(
        priority=Case(
            When(status='checked_in', then=Value(1)),
            When(status='approved', then=Value(2)),
            When(pagato=True, then=Value(3)),
            When(status='pending', then=Value(4)),
            default=Value(5),
            output_field=IntegerField(),
        )
    ).order_by('priority', '-created_at')

    for p in participants:
        # Normalizza il CF; se per caso un record vecchio avesse CF vuoto, usa un fallback univoco
        cf = (p.codice_fiscale or "").strip().upper()
        if not cf:
            cf = f"MISSING-{str(p.unique_id)[:8].upper()}"

        # Se il socio non esiste ancora, lo creiamo mantenendo il suo unique_id originale!
        member, created = Member.objects.get_or_create(
            codice_fiscale=cf,
            defaults={
                'first_name': (p.first_name or "").strip().title(),
                'last_name': (p.last_name or "").strip().title(),
                'email': p.email,
                'phone': p.phone,
                'data_di_nascita': p.data_di_nascita,
                'luogo_di_nascita': (p.luogo_di_nascita or "").strip().title() if p.luogo_di_nascita else None,
                'indirizzo': p.indirizzo,
                'citta': (p.citta or "").strip().title() if p.citta else None,
                'provincia': (p.provincia or "").strip().upper() if p.provincia else None,
                'cap': p.cap,
                'accetta_statuto': p.accetta_statuto,
                'accetta_privacy': p.accetta_privacy,
                'unique_id': p.unique_id,
                'created_at': p.created_at,
            }
        )

        is_valid_member = p.pagato or p.status in ['approved', 'checked_in']

        # 4. Se ha pagato o è approvato, registra la sua Tessera Socio 2026 nel Libro Soci
        if is_valid_member:
            Membership.objects.get_or_create(
                member=member,
                year=2026,
                defaults={'is_active': True}
            )

        # 5. Registra la sua partecipazione a Flanella Fest III (se non già creata da un tentativo precedente)
        EventRegistration.objects.get_or_create(
            event=event_2026,
            member=member,
            defaults={
                'metodo_pagamento': p.metodo_pagamento,
                'pagato': p.pagato,
                'status': p.status,
                'include_membership': True,
                'include_ticket': False,
                'total_paid_centesimi': price_2026 if p.pagato else 0,
            }
        )


def reverse_func(apps, schema_editor):
    # Permette di annullare la migrazione senza danni (ripristina lo stato precedente)
    Member = apps.get_model('festival', 'Member')
    Event = apps.get_model('festival', 'Event')
    Event.objects.filter(slug='flanella-fest-3').delete()
    Member.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('festival', '0010_create_multi_event_models'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]