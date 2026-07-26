from django.contrib import admin
from .models import Participant, FestivalConfig

# Amministrazione singola del Partecipante (Socio e Pagamento)
@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    # Colonne visibili nella lista generale
    list_display = (
        'first_name', 'last_name', 'email', 'codice_fiscale', 
        'status', 'metodo_pagamento', 'pagato', 'created_at'
    )
    
    # Filtri laterali per trovare facilmente i non pagati o chi deve fare il check-in
    list_filter = ('status', 'pagato', 'metodo_pagamento', 'accetta_statuto', 'created_at')
    
    # Campi di ricerca testuale
    search_fields = ('first_name', 'last_name', 'codice_fiscale', 'email', 'phone')
    
    # Campi che non possono essere modificati a mano
    readonly_fields = ('unique_id', 'created_at')
    
    # Azione rapida per il pannello
    actions = ['segna_come_pagato']

    @admin.action(description='Segna i partecipanti selezionati come Pagati')
    def segna_come_pagato(self, request, queryset):
        queryset.update(pagato=True)


# Amministrazione Configurazione (Prezzo biglietto)
@admin.register(FestivalConfig)
class FestivalConfigAdmin(admin.ModelAdmin):
    list_display = ('__str__',)