from django.contrib import admin
from .models import (
    Member,
    Membership,
    Event,
    EventRegistration,
)


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


class EventRegistrationInline(admin.TabularInline):
    model = EventRegistration
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'codice_fiscale', 'email', 'phone', 'unique_id')
    search_fields = ('first_name', 'last_name', 'codice_fiscale', 'email', 'unique_id')
    list_Filter = ('provincia', 'created_at')
    readonly_fields = ('unique_id', 'created_at')
    inlines = [MembershipInline, EventRegistrationInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('member', 'year', 'is_active', 'created_at')
    list_filter = ('year', 'is_active')
    search_fields = ('member__first_name', 'member__last_name', 'member__codice_fiscale', 'member__email')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'year',
        'is_active',
        'requires_membership',
        'membership_price_centesimi',
        'requires_ticket',
        'ticket_price_centesimi',
    )
    list_filter = ('year', 'is_active', 'requires_membership', 'requires_ticket')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        'member',
        'event',
        'status',
        'pagato',
        'metodo_pagamento',
        'total_paid_centesimi',
        'created_at',
    )
    list_filter = ('event', 'status', 'pagato', 'metodo_pagamento')
    search_fields = (
        'member__first_name',
        'member__last_name',
        'member__codice_fiscale',
        'member__unique_id',
    )
