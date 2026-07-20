from django.contrib import admin
from .models import Participant

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('first_name', 'last_name', 'email', 'phone')
